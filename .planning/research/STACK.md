# Technology Stack

**Project:** TGmonitor — Mac Employee Screenshot Monitoring Agent
**Researched:** 2026-03-31
**Overall confidence:** HIGH (all key claims verified against official docs)

---

## Recommended Stack

### Mac Agent (Core Component)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Swift | 6.0+ | Agent language | Native macOS, best system API access, compiled binary |
| SwiftUI | macOS 14+ | Menu bar UI (MenuBarExtra) | Native `MenuBarExtra` scene replaces NSStatusItem boilerplate since Ventura. No AppKit needed for the bar itself. |
| AppKit (NSStatusItem) | — | Fallback for macOS < 13 | Only needed if you target pre-Ventura; drop it if min target is macOS 14 |
| ScreenCaptureKit (SCScreenshotManager) | macOS 14+ | Screenshot capture | `CGWindowListCreateImage` is **obsoleted** (not just deprecated) in macOS 15 Sequoia. SCScreenshotManager is the required replacement. Async, supports per-app filtering, multiple pixel formats. |
| Apple Vision framework | built-in | On-device OCR fallback | Free, on-device, supports VNRecognizeTextRequest. Use to pre-filter trivial screens (lock screen, screensaver) before calling paid API, saving ~15% API cost. |
| LaunchDaemon plist | /Library/LaunchDaemons/ | Startup persistence | Runs as root before login, survives user logout. Harder to kill than LaunchAgent. Requires initial privileged install (admin password). |
| swift-confidential | 0.3.x | Credential obfuscation | Compile-time literal obfuscator via Swift macro. Prevents `strings` tool from extracting API keys from binary. Source: github.com/securevale/swift-confidential |
| UserDefaults + Keychain | built-in | Password protection | Store admin password hash in Keychain; UI lock via NSRunningApplication cannot terminate without this. |

**Note on LSUIElement:** Set `LSUIElement = YES` in Info.plist to hide from Dock and remove app from Cmd+Tab switcher. This is the standard pattern for menu bar agents.

**Disguise strategy:** Bundle app under a custom name (e.g., "System Font Manager" or "Display Calibrator") with a matching system-looking icon. The app name in Activity Monitor and Dock is pulled from Info.plist's CFBundleDisplayName. Change the LaunchDaemon label to match.

---

### Screenshot Capture API Decision (CRITICAL)

**Use: ScreenCaptureKit / SCScreenshotManager**

`CGWindowListCreateImage` was marked unavailable/obsoleted in macOS 15.0 Sequoia. It cannot compile with the current SDK. All new Mac agent code must use ScreenCaptureKit.

```swift
// Correct: macOS 14+ SCScreenshotManager
let filter = SCContentFilter(display: display, excludingWindows: [])
let config = SCStreamConfiguration()
config.width = 1366
config.height = 768
let cgImage = try await SCScreenshotManager.captureImage(
    contentFilter: filter,
    configuration: config
)
```

Screen Recording permission (`NSScreenRecordingUsageDescription`) is still required. For a disguised background agent, handle permission prompt at first-run with a custom explanation dialog before the system prompt appears.

---

### AI Vision Model (CRITICAL COST DECISION)

**Recommended: Gemini 2.5 Flash-Lite via Google AI API**

#### Cost Comparison Table — 480 images/day, 30 days = 14,400 images/month

Image assumptions: 1366x768 JPEG screenshot, compressed to ~200-400KB. Prompt: ~200 input tokens. Response: ~200 output tokens.

**Gemini token calculation for 1366x768:**
- Formula: tiles × 258, where tiles = ceil(W/crop_unit) × ceil(H/crop_unit), crop_unit = floor(short_side / 1.5) = 512
- Tiles: ceil(1366/512) × ceil(768/512) = 3 × 2 = 6 tiles → **1,548 image tokens**

**OpenAI token calculation for 1366x768 (high detail):**
- Scaled to 768px short side → 1366×768 → tiles: ceil(1366/512) × ceil(768/512) = 3 × 2 = 6 tiles
- Tokens: (6 × 170) + 85 = **1,105 tokens**

| Model | Input price ($/MTok) | Output price ($/MTok) | Tokens/image (in) | Total cost/image | Monthly (14,400 imgs) | Notes |
|-------|---------------------|----------------------|-------------------|------------------|-----------------------|-------|
| **Gemini 2.5 Flash-Lite** | $0.10 | $0.40 | 1,548 + 200 = 1,748 | **$0.000255** | **$3.67** | RECOMMENDED. $0.10/MTok verified from Google deprecation docs |
| **GPT-4o-mini (low detail)** | $0.15 | $0.60 | 85 + 200 = 285 | **$0.000163** | **$2.35** | Low detail = 85 flat tokens. Loses screen detail — may miss activity. Not recommended for monitoring. |
| **GPT-4o-mini (high detail)** | $0.15 | $0.60 | 1,105 + 200 = 1,305 | **$0.000316** | **$4.55** | More detail but more expensive than Gemini 2.5 Flash-Lite. OpenAI ecosystem lock-in. |
| **Gemini 2.5 Flash** | $0.30 | $2.50 | 1,548 + 200 = 1,748 | **$0.001024** | **$14.75** | 4x the cost of Flash-Lite. Same image quality for this task. Not recommended. |
| **Claude Haiku 3 (batch)** | $0.125 | $0.625 | ~1,334 + 200 = 1,534 | **$0.000317** | **$4.57** | Via Batch API (50% discount). Haiku 3 is lowest-cost Anthropic model. Comparable to GPT-4o-mini high detail. |
| **Claude Haiku 3.5** | $0.80 | $4.00 | ~1,334 + 200 = 1,534 | **$0.001867** | **$26.89** | Too expensive for this volume. |
| **Apple Vision (on-device)** | FREE | FREE | N/A | **$0.00** | **$0.00** | OCR + basic classification only. Cannot describe holistic screen activity or detect app context. NOT sufficient as primary analyzer. Use as pre-filter. |

**Winner: Gemini 2.5 Flash-Lite at ~$3.67/month for all 5 machines combined.**

GPT-4o-mini low detail at $2.35/month is cheaper but sacrifices description quality. For activity monitoring (detecting "USB drive plugged in", "uploading to Google Drive", "file manager open"), full detail is necessary. Gemini 2.5 Flash-Lite high-quality at $3.67/month is the right trade-off.

**Do not use Gemini 2.0 Flash** — it is deprecated and shuts down June 1, 2026.

**Hybrid strategy (optional, saves ~15% cost):** Run Apple Vision OCR first. If the screen shows a lock screen, screensaver, or blank desktop (detected by low OCR text content), skip the API call. This can reduce monthly API calls by 10-15%.

---

### Web Dashboard (VPS)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.115+ | REST API backend | Python, fast, async, minimal boilerplate. Single `main.py` can serve the entire API. Thuan's existing Python expertise. |
| Next.js | 15.x | Web frontend | App Router, React Server Components, SSR built-in. Best for timeline/thumbnail views. Well-supported ecosystem. |
| PostgreSQL | 16+ | Metadata database | Store screenshot records, AI analysis, timestamps, flags. Not for image blobs. |
| SQLite | — | DO NOT USE for production | Cannot handle 5 concurrent agents writing simultaneously without WAL tuning. Use PostgreSQL. |
| Local VPS filesystem + nginx | — | Image file serving | Store JPEG files in `/var/data/screenshots/{machine_id}/{date}/` and serve via nginx. Fast, free, no egress cost. |
| Redis | 7.x | Optional job queue | If upload queue grows, use Redis + RQ (Python). Skip for MVP — direct HTTP upload is fine for 5 machines. |

**Image storage strategy:** Do NOT store screenshots in PostgreSQL as BLOBs. Performance degrades rapidly with binary blobs in relational DBs. Store on VPS filesystem, reference path in PostgreSQL. 7.2GB/month storage is trivial (most VPS have 20-100GB disk). Serve thumbnails via nginx with `proxy_cache` for dashboard performance.

**Database schema (simplified):**
```sql
screenshots (
  id UUID PRIMARY KEY,
  machine_id VARCHAR(50),
  captured_at TIMESTAMPTZ,
  file_path TEXT,         -- /var/data/screenshots/{machine}/{date}/{id}.jpg
  thumbnail_path TEXT,
  ai_description TEXT,
  ai_apps_detected TEXT[],
  ai_flagged BOOLEAN,
  ai_flag_reason TEXT,
  uploaded_at TIMESTAMPTZ
)
```

---

### Infrastructure

| Component | Technology | Why |
|-----------|------------|-----|
| VPS | Any existing VPS (Nginx + Docker) | Already available per PROJECT.md |
| Container | Docker Compose | FastAPI + PostgreSQL + Nginx in single compose file |
| Image serving | Nginx static files | Direct disk reads, no app-layer overhead |
| TLS | Let's Encrypt / Certbot | Free TLS for dashboard HTTPS |
| Auth | HTTP Basic Auth or simple JWT | Dashboard is admin-only, single user (Thuan). No OAuth needed. |
| Agent upload | HTTPS POST to FastAPI | Authenticated with hardcoded API key (obfuscated in binary) |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Screenshot API | ScreenCaptureKit | CGWindowListCreateImage | Obsoleted in macOS 15, cannot compile |
| Vision AI | Gemini 2.5 Flash-Lite | Gemini 2.5 Flash | 4x more expensive, no quality benefit at this task |
| Vision AI | Gemini 2.5 Flash-Lite | GPT-4o-mini low detail | Low detail misses screen context needed for monitoring |
| Vision AI | Gemini 2.5 Flash-Lite | Claude Haiku 3 (batch) | Similar cost, adds Anthropic account dependency, slower batch processing |
| Persistence | LaunchDaemon | LaunchAgent | LaunchAgent is per-user, killed on logout; daemon runs system-wide at boot |
| Storage | Filesystem + PostgreSQL | PostgreSQL BLOBs | BLOB storage in PG degrades at scale, harder to serve via CDN/nginx |
| Storage | Filesystem + PostgreSQL | S3/Backblaze B2 | Overkill for 7.2GB/month on a VPS with available disk |
| Frontend | Next.js | Plain HTML+JS | Next.js gives pagination, SSR thumbnails, image optimization (`<Image>`) out of the box |
| Backend | FastAPI | Express/Node | Python aligns with Thuan's existing stack; faster to iterate |
| Mac UI | SwiftUI MenuBarExtra | AppKit NSStatusItem | MenuBarExtra is the modern API since macOS 13 Ventura; less boilerplate |
| Obfuscation | swift-confidential | Manual XOR | swift-confidential is a maintained Swift Package Manager plugin; macro-based, no manual encoding |

---

## Installation

### Mac Agent (Swift Package Manager)

```swift
// Package.swift dependencies
.package(url: "https://github.com/securevale/swift-confidential", from: "0.3.0")
```

Xcode project entitlements required:
- `com.apple.security.screen-recording` (ScreenCaptureKit)
- No App Sandbox (required for LaunchDaemon system-level access)

### VPS Backend

```bash
# Python backend
pip install fastapi uvicorn[standard] psycopg2-binary python-multipart pillow

# Frontend
npx create-next-app@latest dashboard --typescript --app --no-src-dir

# Docker Compose
docker compose up -d  # FastAPI + PostgreSQL + Nginx
```

---

## Security Notes

### Credential Obfuscation in Binary

Use `swift-confidential` to obfuscate the VPS API endpoint and Google API key at compile time:

```swift
// This string is NOT stored as plain text in the binary
@Obfuscated var vpsEndpoint = "https://monitor.yourdomain.com"
@Obfuscated var googleApiKey = "AIza..."
```

The macro transforms literals into encrypted byte arrays decoded only at runtime. Strings will not appear in `strings ./TGmonitor` output.

**Important:** This is obfuscation, not encryption. A determined attacker with a debugger can extract values at runtime. For an internal corporate tool on company-owned machines, this is sufficient protection. The goal is to prevent casual discovery via static analysis, not nation-state adversaries.

### Tamper Resistance

- LaunchDaemon with `KeepAlive: true` and `ThrottleInterval: 10` relaunches within 10 seconds if killed
- Disable `RunAtLoad: false` alternative so it only triggers on keep-alive
- The daemon binary should be owned by root:wheel with 755 permissions so a non-admin user cannot delete it
- Wrap the binary in a macOS app bundle disguised as a system utility (custom CFBundleName, CFBundleDisplayName, and system-looking icon)
- A password dialog (stored hash in Keychain) should gate any UI that allows disabling capture

### Transport Security

- All uploads over HTTPS (TLS 1.2+)
- FastAPI endpoint requires `X-API-Key` header matching the obfuscated key
- Screenshots encrypted in transit via TLS; no additional file-level encryption needed at this scale

---

## Sources

- [Gemini API Pricing (Official)](https://ai.google.dev/gemini-api/docs/pricing) — Verified 2026-03-31
- [Gemini 2.0 Flash Deprecation Notice](https://ai.google.dev/gemini-api/docs/deprecations) — Shuts down June 1, 2026
- [Gemini 2.5 Flash-Lite stable release](https://developers.googleblog.com/en/gemini-25-flash-lite-is-now-stable-and-generally-available/) — Replacement for 2.0 Flash
- [Anthropic Pricing (Official)](https://platform.claude.com/docs/en/about-claude/pricing) — Verified 2026-03-31
- [OpenAI Pricing (Official)](https://openai.com/api/pricing/) — Verified via search 2026-03-31
- [ScreenCaptureKit deprecation of CGWindowListCreateImage](https://trac.macports.org/ticket/71136) — Obsoleted macOS 15
- [Apple ScreenCaptureKit Docs](https://developer.apple.com/documentation/screencapturekit/)
- [swift-confidential GitHub](https://github.com/securevale/swift-confidential) — Active, SPM plugin
- [Gemini Vision image tokenization formula](https://ai.google.dev/gemini-api/docs/vision) — 258 tokens/tile, tile=768px
- [OpenAI image token calculation](https://community.openai.com/t/gpt-4o-mini-high-vision-cost/872382) — 170 tokens/512px tile + 85 base
- [SwiftUI MenuBarExtra (macOS 13+)](https://sarunw.com/posts/swiftui-menu-bar-app/) — Standard modern approach
- [LaunchDaemon vs LaunchAgent persistence](https://attack.mitre.org/techniques/T1543/004/) — System-level daemon runs at boot
