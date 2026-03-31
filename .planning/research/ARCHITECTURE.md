# Architecture Patterns

**Domain:** Mac employee monitoring agent + VPS dashboard
**Researched:** 2026-03-31
**Overall Confidence:** HIGH (Apple official docs + verified patterns)

---

## System Overview

Five components form the complete system. The Mac Agent is the critical path — everything else depends on it working.

```
┌─────────────────────────────────────────────────────┐
│  Mac Agent (Swift)                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Capture  │→ │ Compress │→ │  Local Store     │  │
│  │ Engine   │  │ Pipeline │  │  ~/Library/...   │  │
│  └──────────┘  └──────────┘  └────────┬─────────┘  │
│                                        │             │
│  ┌──────────────────────────────────────↓──────────┐ │
│  │ Upload Queue (async, retry-capable)             │ │
│  └───────────────────────────┬─────────────────────┘ │
└──────────────────────────────┼──────────────────────┘
                               │ HTTPS POST (multipart)
                               ↓
┌──────────────────────────────────────────────────────┐
│  VPS Backend (FastAPI + Python)                      │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Ingest  │→ │  Store   │→ │  AI Analysis Queue │ │
│  │   API    │  │ (files + │  │  (Gemini Flash)    │ │
│  └──────────┘  │   DB)    │  └────────────────────┘ │
│                └──────────┘                          │
└───────────────────────┬──────────────────────────────┘
                        │ SQL queries
                        ↓
┌─────────────────────────────────────────────────────┐
│  PostgreSQL DB                                      │
│  employees | screenshots | analyses | alerts        │
└─────────────────────────────────────────────────────┘
                        │ JSON API
                        ↓
┌─────────────────────────────────────────────────────┐
│  Web Dashboard (Next.js)                            │
│  Timeline view | Thumbnails | Red flag alerts       │
└─────────────────────────────────────────────────────┘
```

---

## Component 1: Mac Agent

### Process Architecture

**Decision: LaunchAgent + KeepAlive, NOT LaunchDaemon**

LaunchDaemon runs as root before user login — it cannot access screen content because it has no user session. Screen capture (ScreenCaptureKit) requires a user session with screen recording permission. A LaunchAgent runs in the user session and supports the menu bar UI.

The agent uses two cooperating processes:

```
LaunchAgent A (Watchdog helper — minimal, no UI)
└── spawns and monitors →
    LaunchAgent B (Main agent — menu bar, capture, upload)
        if B exits for any reason → A restarts it via launchctl
```

This is the standard watchdog pattern. The main agent registers itself as a LaunchAgent with `KeepAlive = true` so launchd restarts it on kill. The companion watchdog ensures it re-registers if launchd state is corrupted.

**Persistence mechanism:**

```xml
<!-- ~/Library/LaunchAgents/com.jsr.systemhelper.plist -->
<dict>
    <key>Label</key>
    <string>com.jsr.systemhelper</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/SystemHelper.app/Contents/MacOS/SystemHelper</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
```

With `KeepAlive = true`, launchd restarts the process every time it exits — including when killed from Activity Monitor. ThrottleInterval prevents rapid crash-restart loops from hammering the CPU.

**Disguise:**
- App bundle name: "SystemHelper" or "UpdateService" (innocuous system-sounding name)
- Custom icon matching macOS system utilities
- No Dock icon (`LSUIElement = YES` in Info.plist, or `NSApp.setActivationPolicy(.accessory)`)

**Tamper resistance levels:**

| Threat | Defense |
|--------|---------|
| Kill from Activity Monitor | launchd KeepAlive restarts within 10s |
| `launchctl unload` by user | Requires admin password, plist re-installs on next app launch |
| Quit from menu bar | Menu requires 6-digit PIN to quit (stored in Keychain) |
| Delete the app | Watchdog helper plist remains in LaunchAgents, fails gracefully |
| System reboot | Both LaunchAgent plists have RunAtLoad = true |

Note: Without a kernel extension (kext), true unkillable protection is not possible on modern macOS (SIP prevents kext signing for third parties). launchd restart is the practical maximum.

### Screenshot Capture Pipeline

**Decision: ScreenCaptureKit (SCScreenshotManager), NOT CGWindowListCreateImage**

CGWindowListCreateImage was deprecated in macOS 14 and marked unavailable (compile error) in macOS 15 (Sequoia). All company Macs running Sequoia cannot use it. ScreenCaptureKit is the only supported path.

Pipeline:

```
Timer (300s interval)
    │
    ↓
SCShareableContent.getExcludingDesktopWindows(false, onScreenWindowsOnly: true)
    │
    ↓
SCContentFilter(display: primaryDisplay, excludingWindows: [])
    │
    ↓
SCStreamConfiguration (resolution: 1920x1080, scaleFactor: 1.0, format: .bgra8888)
    │
    ↓
SCScreenshotManager.captureImage(contentFilter:, configuration:)  // async/await
    │
    ↓
CGImage → compress to JPEG (quality: 0.7) → Data (~200-500KB)
    │
    ↓
Write to local store with metadata JSON sidecar
```

**Screen recording permission:** Must be granted by user (or MDM PPPC profile) before first capture. Apple blocks MDM from auto-granting screen recording — it requires user action exactly once. On first launch, the agent should prompt the user and open System Settings > Privacy > Screen Recording if not yet granted.

macOS Sequoia (15+) shows a monthly re-confirmation prompt for screen recording. This cannot be disabled without MDM configuration profile (`com.apple.screencapture` key `disable-user-preference-approval`). Document this for the setup guide.

### Local Storage

```
~/Library/Application Support/SystemHelper/
├── screenshots/
│   ├── 2026-03-31/
│   │   ├── 2026-03-31T09-00-00.jpg
│   │   ├── 2026-03-31T09-00-00.meta.json
│   │   └── ...
│   └── ...
├── queue/           ← uploaded=false files pending VPS sync
└── db.sqlite        ← local index: filename, timestamp, uploaded, hash
```

30-day cleanup: a background timer runs daily, deletes directories older than 30 days. SQLite is the index for the upload queue — cheaper than filesystem scanning, survives app restarts.

**Upload queue state machine:**

```
PENDING → UPLOADING → UPLOADED
                ↓
           FAILED (retry_count < 5)
                ↓
           DEAD (retry_count >= 5, skip)
```

Retry with exponential backoff: 30s, 2m, 10m, 1h, 6h.

### Credential Obfuscation

**Decision: ObfuscateMacro (Swift macro, compile-time XOR scramble)**

Library: `github.com/p-x9/ObfuscateMacro` — transforms string literals at compile time using a random seed, only decodes at runtime. Binary contains scrambled bytes, not plain strings. Decompilation via `strings` command reveals nothing readable.

```swift
import ObfuscateMacro

// These are scrambled at compile time
let vpsBaseURL = #obfuscate("https://monitor.jsrdental.com")
let vpsAPIKey  = #obfuscate("sk-...")
let geminiKey  = #obfuscate("AIza...")
```

Honest limitation: a determined reverse engineer with a debugger can extract values at runtime. This provides protection against casual inspection (strings tool, Hopper quick scan), not against targeted analysis. Acceptable for the threat model (casual employee tampering).

---

## Component 2: VPS Backend

### Stack

**FastAPI (Python) + PostgreSQL + local filesystem**

FastAPI chosen for: async-native (image uploads don't block), auto-generated OpenAPI docs, fast development, excellent multipart upload support.

Local filesystem (not S3) chosen because: 7.2GB/month total for 5 machines is trivially small. S3 adds complexity and cost. At this scale, VPS disk (even 50GB SSD) handles 6+ months. Upgrade path to S3/Backblaze B2 exists if needed.

### API Surface

```
POST /api/v1/upload
    Headers: Authorization: Bearer {api_key}
    Body: multipart/form-data
        - file: screenshot JPEG
        - employee_id: string
        - captured_at: ISO8601 timestamp
        - machine_id: string
        - app_name: string (active app at capture time)
        - window_title: string

GET  /api/v1/employees
GET  /api/v1/employees/{id}/screenshots?date=2026-03-31
GET  /api/v1/screenshots/{id}          ← metadata JSON
GET  /api/v1/screenshots/{id}/image    ← raw JPEG
GET  /api/v1/screenshots/{id}/thumb    ← 320px thumbnail
GET  /api/v1/alerts?date=&employee_id=
```

### Database Schema

```sql
-- Employees
CREATE TABLE employees (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    machine_id  TEXT UNIQUE NOT NULL,   -- MAC address or hostname
    location    TEXT,                   -- clinic name
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Screenshots
CREATE TABLE screenshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID REFERENCES employees(id),
    captured_at     TIMESTAMPTZ NOT NULL,
    received_at     TIMESTAMPTZ DEFAULT NOW(),
    file_path       TEXT NOT NULL,       -- relative path on VPS filesystem
    file_size_bytes INTEGER,
    app_name        TEXT,
    window_title    TEXT,
    analysis_status TEXT DEFAULT 'pending'  -- pending|processing|done|error
);

CREATE INDEX idx_screenshots_employee_captured ON screenshots(employee_id, captured_at DESC);
CREATE INDEX idx_screenshots_status ON screenshots(analysis_status);

-- AI Analyses
CREATE TABLE analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screenshot_id   UUID REFERENCES screenshots(id) UNIQUE,
    analyzed_at     TIMESTAMPTZ DEFAULT NOW(),
    activity_desc   TEXT,               -- "User editing Excel spreadsheet"
    app_detected    TEXT,               -- "Microsoft Excel"
    risk_score      SMALLINT DEFAULT 0, -- 0-10
    flags           JSONB DEFAULT '[]', -- ["usb_activity", "cloud_upload"]
    raw_response    JSONB               -- full model response for audit
);

-- Alerts
CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screenshot_id   UUID REFERENCES screenshots(id),
    employee_id     UUID REFERENCES employees(id),
    alert_type      TEXT NOT NULL,       -- "usb_transfer"|"cloud_upload"|"suspicious_app"
    severity        TEXT DEFAULT 'medium', -- low|medium|high|critical
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ          -- NULL = unread
);

CREATE INDEX idx_alerts_employee_created ON alerts(employee_id, created_at DESC);
CREATE INDEX idx_alerts_unack ON alerts(acknowledged_at) WHERE acknowledged_at IS NULL;
```

### Image Storage Layout

```
/var/app/tgmonitor/screenshots/
├── {employee_id}/
│   ├── 2026/03/31/
│   │   ├── {uuid}.jpg
│   │   └── {uuid}.thumb.jpg   ← generated on upload (320px wide)
│   └── ...
└── ...
```

Thumbnails generated server-side using Pillow on upload. Avoids repeated resizing on every dashboard load.

### AI Analysis Pipeline

**Decision: Server-side analysis, NOT on-device**

On-device analysis would require: running a local model (too heavy for background agent) or the Gemini API key exposed on every Mac. Server-side concentrates the API key to one trusted location (VPS) and can batch/queue analysis without impacting capture timing.

```
Upload received → screenshot written to disk → DB record inserted → 
task queued in analysis_queue (in-memory queue or Redis) →
background worker pulls task → calls Gemini Flash API →
inserts into analyses table → if risk_score >= 7 → inserts alert
```

Worker is a FastAPI background task or a separate Python process with asyncio. At 480 screenshots/day, even synchronous processing catches up easily.

**AI prompt structure (Gemini Flash):**

```
Analyze this workplace screenshot. Return JSON:
{
  "activity_description": "brief description of what user is doing",
  "active_app": "application name",
  "risk_score": 0-10,
  "flags": ["usb_activity"|"cloud_upload"|"file_transfer"|"personal_use"|"suspicious_app"],
  "reasoning": "why this risk score"
}
Risk indicators: USB file transfers, cloud storage uploads (Dropbox/Drive/OneDrive visible),
sending files externally, personal browsing during work hours, screenshots of sensitive data.
```

---

## Component 3: Web Dashboard

### Stack

**Next.js 14 (App Router) + Tailwind CSS + SWR for data fetching**

Minimal complexity. No real-time requirement — screenshots arrive every 5 minutes. Polling every 60 seconds is sufficient. WebSockets add unnecessary complexity for this use case.

### Page Structure

```
/                      → redirect to /dashboard
/dashboard             → all employees, today's alert count, last seen
/employees/{id}        → timeline view for one employee
/employees/{id}?date=  → filter by date
/alerts                → all unacknowledged alerts across all employees
/settings              → employee management
```

### Timeline View Architecture

```
EmployeeTimelinePage
├── DatePicker
├── AlertBanner (count of flags for selected day)
└── ScreenshotGrid
    ├── HourBlock (09:00 - 10:00)
    │   ├── ScreenshotCard (thumbnail + time + app name)
    │   │   ├── <img src="/api/screenshots/{id}/thumb" />
    │   │   └── RiskBadge (color-coded by risk_score)
    │   └── ...
    └── ...
```

Each ScreenshotCard links to a detail modal showing:
- Full-size image (lazy loaded via `/api/screenshots/{id}/image`)
- AI activity description
- App name / window title
- Any alerts triggered

### Data Fetching

SWR with 60-second revalidation:

```typescript
// Polling — sufficient for 5-min screenshot interval
const { data } = useSWR(`/api/v1/employees/${id}/screenshots?date=${date}`, fetcher, {
    refreshInterval: 60_000
})
```

No WebSocket needed. Dashboard is read-only and screenshots arrive infrequently.

### Authentication

Single-password protection via JWT stored in httpOnly cookie. No user management needed — Thuan is the only viewer. Dashboard login page → cookie set → all API routes check Bearer token.

---

## Component 4: Security Architecture

### Transport Security

All uploads use HTTPS. Mac agent validates server certificate (no cert pinning needed — standard TLS is sufficient). API key in Authorization header.

### Credential Storage on Mac Agent

| Credential | Storage Method |
|------------|----------------|
| VPS API key | ObfuscateMacro (compile-time XOR scramble in binary) |
| Gemini API key | ObfuscateMacro (compile-time XOR scramble in binary) |
| PIN to disable agent | macOS Keychain (set on first install) |
| No credentials in plist files | — |
| No credentials in Info.plist | — |

### VPS Security

```
nginx (TLS termination, reverse proxy)
    → FastAPI (127.0.0.1:8000, not exposed directly)

ufw: allow 80, 443 only
SSH: key-based only, port 22 closed to public (VPN or known IP)
API key: 32-byte random hex, stored in env var, not in code
Dashboard auth: JWT, bcrypt-hashed password in .env
```

---

## Component Boundaries

| Component | Owns | Does NOT Own |
|-----------|------|-------------|
| Mac Agent | Capture, local storage, upload queue | AI analysis, dashboard |
| VPS Ingest API | Receive, validate, store files + DB rows | Analysis (queued separately) |
| Analysis Worker | Gemini API calls, write analyses + alerts | Image storage |
| Web Dashboard | Read-only views | Any write operations |
| PostgreSQL | All persistent data | Image blobs (filesystem owns those) |

---

## Data Flow (Explicit Direction)

```
Mac (Timer fires)
  → SCScreenshotManager captures CGImage
  → Compress to JPEG (quality 0.7)
  → Write to ~/Library/Application Support/SystemHelper/screenshots/
  → Insert row in local SQLite (status=pending)
  → Upload worker picks up pending rows
  → HTTPS POST to /api/v1/upload (multipart: JPEG + metadata)
  → VPS writes JPEG to /var/app/tgmonitor/screenshots/{employee}/{date}/{uuid}.jpg
  → VPS generates thumbnail (Pillow, 320px)
  → VPS inserts screenshots row (analysis_status=pending)
  → Analysis worker picks up pending row
  → Calls Gemini Flash API with base64 image
  → Inserts analyses row
  → If risk_score >= 7: inserts alert row
  → Dashboard polls /api/v1/employees/{id}/screenshots (SWR, 60s)
  → Renders thumbnail grid + risk badges
  → Red alerts surface via /api/v1/alerts (unacknowledged count in nav)
```

---

## Suggested Build Order

Components have strict dependencies. Build in this order:

### Stage 1: VPS Backend (no dependencies)
Build first — Mac agent needs an endpoint to upload to.
1. FastAPI skeleton + PostgreSQL schema + Docker Compose
2. `/api/v1/upload` endpoint — accepts multipart, writes file, inserts DB row
3. Basic auth middleware (API key check)
4. `/api/v1/screenshots` read endpoints
5. Thumbnail generation on upload

### Stage 2: Mac Agent Core (depends on Stage 1 endpoint existing)
Build capture and upload before analysis or dashboard.
1. Menu bar app skeleton (AppKit NSStatusItem, no Dock icon)
2. LaunchAgent plist + KeepAlive persistence
3. ScreenCaptureKit capture loop (5-min timer)
4. Local SQLite queue + JPEG storage
5. HTTPS upload worker with retry logic
6. Credential obfuscation via ObfuscateMacro
7. PIN-protected quit/disable menu

### Stage 3: AI Analysis (depends on Stage 1 DB + image storage)
Analysis is decoupled from upload — add it after upload pipeline works.
1. Background analysis worker (FastAPI BackgroundTasks or separate process)
2. Gemini Flash API integration
3. Alert insertion logic (risk_score threshold)
4. `/api/v1/alerts` endpoints

### Stage 4: Web Dashboard (depends on Stage 1 + Stage 3 producing data)
Build last — validates the entire system visually.
1. Next.js app skeleton + Tailwind
2. Authentication (single password, JWT cookie)
3. Employee list + daily summary page
4. Timeline/screenshot grid view with thumbnails
5. Alert panel (unacknowledged flags)

---

## Scalability Considerations

| Concern | At 5 machines (now) | At 50 machines | At 500 machines |
|---------|---------------------|----------------|-----------------|
| Image storage | Local filesystem, ~7GB/month | ~70GB/month, still OK on VPS | Migrate to S3/B2 |
| Analysis throughput | Serial async worker, trivial | Parallel workers or queue (Celery/Redis) | Distributed workers |
| DB queries | No indexes needed at this scale | Add date-range indexes (already in schema) | Partition by employee+month |
| Dashboard | SWR polling, instant | Still polling, 60s refresh sufficient | WebSockets if needed |
| VPS | 1 vCPU, 1GB RAM sufficient | 2 vCPU, 2GB RAM | Scale horizontally |

---

## Architecture Decisions Record

| Decision | Choice | Rationale | Confidence |
|----------|--------|-----------|------------|
| Mac persistence | LaunchAgent + KeepAlive | Can access user session for screen capture | HIGH |
| Screenshot API | ScreenCaptureKit | CGWindowListCreateImage obsoleted in macOS 15 | HIGH (Apple official) |
| App framework | AppKit + SwiftUI hybrid | MenuBarExtra (SwiftUI-only) needs Ventura+ minimum; AppKit NSStatusItem works on Monterey+ | HIGH |
| Credential obfuscation | ObfuscateMacro | Compile-time scramble, defeats strings analysis | MEDIUM (not cryptographically secure) |
| Backend | FastAPI + PostgreSQL | Async uploads, auto-docs, team-familiar Python | HIGH |
| Image storage | VPS filesystem | 7GB/month is trivially small; S3 adds complexity | HIGH |
| Analysis location | Server-side | Centralizes API key; doesn't impact Mac agent performance | HIGH |
| AI model | Gemini Flash | Cheapest vision model with sufficient accuracy (confirm in STACK.md) | MEDIUM (needs cost validation) |
| Dashboard comms | SWR polling (60s) | Screenshots arrive every 5min; WebSockets unnecessary | HIGH |

---

## Sources

- [ScreenCaptureKit — Apple Developer Documentation](https://developer.apple.com/documentation/screencapturekit/)
- [CGWindowListCreateImage obsoleted in macOS 15 — MacPorts ticket](https://trac.macports.org/ticket/71136)
- [SMAppService API — theevilbit blog](https://theevilbit.github.io/posts/smappservice/)
- [launchd KeepAlive — launchd.info](https://www.launchd.info/)
- [ObfuscateMacro — GitHub p-x9](https://github.com/p-x9/ObfuscateMacro)
- [Swift Confidential — GitHub securevale](https://github.com/securevale/swift-confidential)
- [macOS menu bar app with AppKit — polpiella.dev](https://www.polpiella.dev/a-menu-bar-only-macos-app-using-appkit/)
- [Screen Recording cannot be MDM-granted — Apple Developer Forums](https://developer.apple.com/forums/thread/122414)
- [Building modern Launch Agent on macOS — GitHub Gist](https://gist.github.com/Matejkob/f8b1f6a7606f30777552372bab36c338)
- [A look at ScreenCaptureKit on macOS Sonoma — Nonstrict](https://nonstrict.eu/blog/2023/a-look-at-screencapturekit-on-macos-sonoma/)
