# Project Research Summary

**Project:** TGmonitor — Mac Employee Screenshot Monitoring Agent
**Domain:** macOS background monitoring agent with AI vision analysis + VPS dashboard
**Researched:** 2026-03-31
**Confidence:** HIGH

---

## Executive Summary

TGmonitor is a stealth macOS background agent that captures periodic screenshots, uploads them to a self-hosted VPS backend, and uses AI vision to automatically describe and flag employee activity. The domain is well-established (Hubstaff, Teramind, DeskTime, ActivTrak are commercial references), but TGmonitor's differentiator is replacing the standard app-blocklist / URL-categorization approach with AI vision analysis — giving natural language descriptions of activity rather than binary allow/block rules. This is technically feasible and the cheapest capable model (Gemini 2.5 Flash-Lite at ~$3.67/month for all 5 machines combined) makes the economics trivial.

The recommended architecture is a 4-component system: Swift-based Mac agent (capture + local queue + upload) → FastAPI VPS backend (ingest + file storage + AI analysis) → PostgreSQL (metadata) → Next.js dashboard (timeline view + alerts). The critical path runs through the Mac agent — every other component depends on working screenshot capture and upload. macOS 15 Sequoia obsoleted `CGWindowListCreateImage`; ScreenCaptureKit with `SCScreenshotManager` is the only valid capture API. The persistence layer must be a LaunchDaemon at `/Library/LaunchDaemons/` (root-level) rather than a user-level LaunchAgent to survive employee kill attempts.

The highest-risk area is macOS permission management. Apple's TCC system requires screen recording permission, which resets on code signature changes and triggers a monthly system dialog in macOS 15+ that would expose the agent to employees. The mitigation is either MDM-managed TCC profiles (Jamf/Mosyle) for silent pre-authorization, or building the agent to detect permission loss and alert the admin dashboard. Before any deployment, written monitoring disclosure must be added to employee contracts (Vietnam labor law compliance).

---

## Key Findings

### Recommended Stack

The Mac agent must be written in Swift 6.0+ using ScreenCaptureKit for capture (`CGWindowListCreateImage` cannot compile on macOS 15), SwiftUI `MenuBarExtra` for the menu bar UI, and a LaunchDaemon plist for persistence. Credentials embedded in the binary should be obfuscated at compile time using `swift-confidential` or `ObfuscateMacro`, but more importantly the Gemini API key should never live in the binary at all — route all vision API calls through the VPS backend proxy so the key stays server-side.

**Core technologies:**
- **Swift 6.0 + ScreenCaptureKit**: Mac agent language and screenshot API — only supported path on macOS 15+
- **SwiftUI MenuBarExtra**: Menu bar UI — modern native API since macOS 13, replaces NSStatusItem boilerplate
- **LaunchDaemon** (`/Library/LaunchDaemons/`): Persistence — root-level, survives user kill/unload without admin password
- **ObfuscateMacro / swift-confidential**: Compile-time credential obfuscation — defeats `strings` inspection
- **Gemini 2.5 Flash-Lite**: AI vision model — cheapest capable model at $3.67/month for 5 machines; do NOT use Gemini 2.0 Flash (deprecated, shuts down June 2026)
- **FastAPI 0.115+**: VPS backend — async, Python (aligns with Thuan's stack), auto-docs, multipart upload support
- **PostgreSQL 16+**: Metadata database — NOT SQLite (cannot handle concurrent writes from 5 agents)
- **VPS filesystem + nginx**: Image storage — 7.2GB/month is trivially small; S3/B2 is premature optimization
- **Next.js 15**: Dashboard frontend — App Router, SSR thumbnails, SWR 60s polling sufficient (no WebSockets needed)

### Expected Features

**Must have (table stakes):**
- Periodic screenshot capture every 5 minutes (configurable) — core value delivery
- Timestamp + app name + window title metadata on every screenshot
- Local storage with 30-day retention on each Mac
- Upload to VPS with retry queue on network failure
- Per-employee view in dashboard (distinguish 5 machines)
- Daily timeline view with thumbnail grid
- AI caption per screenshot — TGmonitor's primary differentiator over commodity tools

**Should have (competitive):**
- Red flag / alert highlighting — USB activity, cloud upload in progress, personal browsing detection via vision
- Tamper resistance — LaunchDaemon KeepAlive + PIN-protected quit
- Agent disguise — custom app name ("SystemHelper"), matching icon, no Dock entry
- Agent health reporting to dashboard — detects when capture stops silently

**Defer to v2+:**
- OCR (vision model handles text detection naturally; dedicated OCR adds complexity without benefit)
- Real-time live view (disproportionate complexity for 5 machines)
- Multi-monitor capture (add after v1 validation; clinic machines likely single monitor)
- Behavioral baseline / anomaly trending (needs historical data accumulation first)
- Daily AI journal narrative (addable once per-screenshot captions are reliable)
- Activity productivity scoring

**Anti-features (do not build):**
- Keystroke logging — HIPAA risk, captures patient PII, far beyond scope
- Real-time video recording — 100x storage/bandwidth cost, unnecessary
- Email/chat content monitoring — HIPAA exposure, legal risk
- Employee self-service portal, payroll integration, multi-tenant hierarchy

### Architecture Approach

The system decomposes cleanly into 4 independent components with a strict dependency chain: Mac Agent (capture + local queue) feeds the VPS Ingest API (receive + store), which feeds the AI Analysis Worker (Gemini calls + alert generation), which feeds the Web Dashboard (read-only views). The Mac agent uses two cooperating LaunchDaemon processes — a watchdog helper that monitors and restarts the main agent — providing KeepAlive resilience without kernel extensions. AI analysis is deliberately server-side to keep the Gemini API key off every Mac and avoid impacting capture timing.

**Major components:**
1. **Mac Agent (Swift)** — capture pipeline, local SQLite queue, HTTPS upload worker with exponential backoff retry
2. **VPS Ingest API (FastAPI)** — multipart upload endpoint, JPEG storage, thumbnail generation (Pillow), PostgreSQL inserts
3. **AI Analysis Worker (Python/FastAPI BackgroundTasks)** — async Gemini Flash calls, risk scoring, alert insertion (risk_score >= 7)
4. **Web Dashboard (Next.js)** — read-only timeline/thumbnail views, alert panel, SWR 60s polling

### Critical Pitfalls

1. **macOS 15 monthly screen recording dialog** — Apple prompts employees monthly to re-approve screen recording, exposing the agent. Mitigation: MDM-managed TCC configuration profile (Jamf/Mosyle) to silently pre-authorize, OR accept dialog + build admin alerts when permission is denied. Address before Phase 1 deployment.

2. **LaunchAgent vs LaunchDaemon** — A user-level LaunchAgent (`~/Library/LaunchAgents/`) can be unloaded or deleted without a password. Must use root-level LaunchDaemon (`/Library/LaunchDaemons/`, owned root:wheel 644) — user cannot touch it without admin credentials. Foundational — cannot be changed post-install without a new installer.

3. **Gemini API key in binary** — Any key embedded in the binary is extractable via debugger at runtime regardless of obfuscation. Mitigation: route all Gemini calls through the VPS backend. Agent sends screenshot to `POST /analyze` on VPS; VPS calls Gemini with its env-var-stored key. Agent binary never touches the Google API key.

4. **TCC permission reset on binary changes** — Screen recording permission resets when code signature changes. Mitigation: sign all production builds with a stable Apple Developer ID certificate ($99/year), and use a stable bundle ID (set once, never change). MDM TCC profile also survives binary updates if bundle ID is stable.

5. **Annual macOS updates silently break capture** — Apple changes ScreenCaptureKit behavior every year. Mitigation: build agent health reporting (screenshot capture failures logged to VPS dashboard) so breaks are detected immediately; pin macOS version on clinic Macs via MDM until agent is verified on new version.

---

## Implications for Roadmap

Based on research, the build order is strictly dependency-driven. The VPS backend must exist before the Mac agent can upload. The Mac agent must be shipping screenshots before AI analysis is useful. The dashboard is only meaningful once data flows. Do not build in parallel across these four stages.

### Phase 0: Legal + Security Groundwork (Pre-deployment)
**Rationale:** Legal compliance and security architecture decisions cannot be retrofitted. Both must be settled before any binary touches a clinic machine.
**Delivers:** Signed employment monitoring disclosures; Apple Developer ID certificate enrolled; stable bundle ID chosen; MDM strategy decided (Jamf/Mosyle vs. manual TCC grant workflow)
**Addresses:** Pitfall 14 (legal notice), Pitfall 3 (TCC code signing), Pitfall 9 (stable bundle ID)
**Avoids:** Legal exposure in Vietnam; TCC permission resets on every update; post-deployment architecture rewrites

### Phase 1: VPS Backend Foundation
**Rationale:** Mac agent needs an upload endpoint to exist before capture is testable end-to-end. Build the receiver first.
**Delivers:** FastAPI app + PostgreSQL schema + Docker Compose; `/api/v1/upload` endpoint; API key auth middleware; file storage at `/var/app/tgmonitor/screenshots/`; thumbnail generation on upload
**Uses:** FastAPI 0.115+, PostgreSQL 16+, Pillow, nginx, Docker Compose
**Implements:** VPS Ingest API component, database schema (employees, screenshots, analyses, alerts tables)
**Avoids:** Pitfall 5 (API key stays in env var on VPS, not in any Mac binary)

### Phase 2: Mac Agent Core
**Rationale:** Capture + upload is the critical path. Everything downstream is blocked until this works reliably.
**Delivers:** Swift menu bar app skeleton; LaunchDaemon plist with KeepAlive; ScreenCaptureKit capture loop (5-min timer using NSBackgroundActivityScheduler); local SQLite queue; HTTPS upload worker with exponential backoff; ObfuscateMacro credential obfuscation; PIN-protected quit
**Uses:** Swift 6.0, ScreenCaptureKit / SCScreenshotManager, AppKit + SwiftUI MenuBarExtra, ObfuscateMacro, NWPathMonitor
**Implements:** Mac Agent component
**Avoids:** Pitfall 1 (monthly dialog — MDM or detection logic), Pitfall 2 (ScreenCaptureKit not CGWindowListCreateImage), Pitfall 4 (LaunchDaemon not LaunchAgent), Pitfall 6 (NSBackgroundActivityScheduler not NSTimer), Pitfall 7 (local-first queue with retry)

### Phase 3: AI Analysis Pipeline
**Rationale:** Decoupled from upload — add after screenshots are flowing reliably to VPS. The analysis worker can process the backlog.
**Delivers:** FastAPI BackgroundTasks worker; Gemini 2.5 Flash-Lite integration (images resized to 1280x800 JPEG 85% before API call); risk scoring; alert insertion (threshold risk_score >= 7); `/api/v1/alerts` endpoints
**Uses:** Gemini 2.5 Flash-Lite, Python asyncio, Pillow for resize
**Implements:** AI Analysis Worker component
**Avoids:** Pitfall 5 (Gemini key on VPS only, never in Mac binary), Pitfall 8 (resize to 1280x800 to control token cost), Pitfall 11 (JPEG 85% quality for AI accuracy)

### Phase 4: Web Dashboard
**Rationale:** Build last — validates the full data pipeline visually. Only useful once Phases 1-3 produce real data.
**Delivers:** Next.js app with auth (single JWT cookie); employee list + daily summary; timeline/thumbnail grid (SWR 60s polling); alert panel; screenshot detail modal with AI caption + risk score
**Uses:** Next.js 15, Tailwind CSS, SWR
**Implements:** Web Dashboard component
**Avoids:** Over-engineering (no WebSockets needed for 5-min screenshot interval)

### Phase Ordering Rationale

- Phase 0 is non-negotiable first — legal disclosure and code signing decisions are impossible to add retroactively without re-deploying to all machines
- VPS before Mac agent — the agent needs a working upload endpoint during development to validate the full pipeline
- AI analysis after upload pipeline — analysis is decoupled and can be added without touching the Mac agent; analyzing a backlog of already-uploaded screenshots is safe
- Dashboard last — it is a pure consumer; building it before data exists leads to building against mock data and debugging twice
- LaunchDaemon choice locks in the persistence model and installation process early — changing from LaunchAgent to LaunchDaemon after deployment requires a new privileged installer

### Research Flags

Phases needing deeper research during planning:
- **Phase 0 (MDM strategy):** Jamf vs. Mosyle pricing and configuration complexity for TCC profile deployment not fully researched. Needs pricing + 5-Mac setup evaluation. If MDM is out of budget, the fallback (manual TCC + admin dashboard alerts) needs detailed design.
- **Phase 2 (Tamper resistance limits):** Without a kernel extension, the LaunchDaemon KeepAlive is the practical maximum. SIP protection of `/Library/LaunchDaemons/` is confirmed but the specific sequence an employee could use to defeat it (boot into recovery mode) has not been fully modeled.

Phases with standard patterns (skip research-phase):
- **Phase 1 (FastAPI + PostgreSQL + Docker Compose):** Extremely well-documented. Standard async Python web API. No further research needed.
- **Phase 3 (Gemini API integration):** Pricing verified, token calculation confirmed, API is straightforward REST. No surprises expected.
- **Phase 4 (Next.js + SWR dashboard):** Standard read-only dashboard. Well-documented patterns. SWR polling is trivial.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All key claims verified against official Apple docs, Google pricing docs, Anthropic pricing. CGWindowListCreateImage obsolescence confirmed via MacPorts bug tracker and Apple SDK. Gemini 2.5 Flash-Lite pricing verified from Google deprecation and pricing docs. |
| Features | HIGH | Table stakes verified against Hubstaff, DeskTime, Teramind, Monitask official feature pages. AI vision differentiation is emerging — not all competitors detail it — but the approach is technically sound. |
| Architecture | HIGH | LaunchAgent vs LaunchDaemon distinction verified via Apple developer docs. ScreenCaptureKit pipeline documented against Apple official docs. Analysis decoupling is standard queue pattern. |
| Pitfalls | HIGH | Monthly screen recording dialog confirmed via Apple developer forums and 9to5Mac. CGWindowListCreateImage obsolescence confirmed. TCC permission reset on unsigned builds well-documented. Credential extraction via debugger is a known OWASP pattern. |

**Overall confidence:** HIGH

### Gaps to Address

- **MDM strategy decision:** Research did not evaluate Jamf vs. Mosyle vs. Apple Business Manager pricing and complexity for 5 Macs. This is the highest-impact unresolved decision — it determines whether the monthly screen recording dialog is a real threat or a solved problem. Recommend pricing this in Phase 0.
- **Vietnam labor law specifics:** The legal notice requirement is based on general labor law principles. Actual Vietnamese data protection regulations (PDPD 2023) were not reviewed. Thuan should verify with legal counsel before deployment.
- **macOS version distribution on clinic Macs:** Research assumed macOS 14/15. If any clinic Mac runs macOS 13 (Ventura) or earlier, some API choices need validation. The `CGWindowListCreateImage` obsolescence is macOS 15+ only — macOS 13/14 can still use it with deprecation warnings but it compiles. However, building with ScreenCaptureKit from day one is still correct.
- **Network topology at clinics:** Upload retry logic is designed for intermittent connectivity. If clinic networks are air-gapped or have significant VPS upload latency, the retry interval design may need tuning.

---

## Sources

### Primary (HIGH confidence)
- [Gemini API Pricing (Official)](https://ai.google.dev/gemini-api/docs/pricing) — Gemini 2.5 Flash-Lite pricing ($0.10/MTok input), token calculation formula
- [Gemini 2.0 Flash Deprecation Notice](https://ai.google.dev/gemini-api/docs/deprecations) — Confirmed shutdown June 1, 2026
- [Apple ScreenCaptureKit Documentation](https://developer.apple.com/documentation/screencapturekit/) — SCScreenshotManager API
- [CGWindowListCreateImage obsoleted — MacPorts ticket](https://trac.macports.org/ticket/71136) — macOS 15 obsolescence confirmed
- [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — Claude Haiku 3 comparison pricing
- [OpenAI API Pricing](https://openai.com/api/pricing/) — GPT-4o-mini comparison pricing
- [swift-confidential](https://github.com/securevale/swift-confidential) — Compile-time credential obfuscation SPM package
- [ObfuscateMacro](https://github.com/p-x9/ObfuscateMacro) — Alternative Swift macro obfuscation

### Secondary (MEDIUM confidence)
- [Hubstaff Screenshot Features](https://hubstaff.com/time-tracker-with-screenshots) — Table stakes feature benchmarking
- [Teramind Screenshot Monitoring](https://www.teramind.co/features/employee-screenshot-monitoring/) — Enterprise feature comparison, tamper resistance claims
- [DeskTime Features](https://desktime.com/features/time-tracking-with-screenshots) — Capture interval parameters
- [macOS Sequoia monthly screen recording prompt — 9to5Mac](https://9to5mac.com/2024/08/14/macos-sequoia-screen-recording-prompt-monthly/) — Monthly dialog behavior
- [Persistent Content Capture Entitlement — Michael Tsai](https://mjtsai.com/blog/2024/08/08/sequoia-screen-recording-prompts-and-the-persistent-content-capture-entitlement/) — Confirms restricted entitlement not publicly obtainable
- [LaunchDaemons vs LaunchAgents — launchd.info](https://www.launchd.info/) — KeepAlive, RunAtLoad behavior
- [ActivTrak vs Time Doctor comparison](https://peoplemanagingpeople.com/tools/activtrak-vs-time-doctor/) — Productivity scoring context

### Tertiary (informational)
- [OWASP MASWE-0005 — Hardcoded API Keys](https://mas.owasp.org/MASWE/MASVS-AUTH/MASWE-0005/) — Credential extraction risk model
- [MITRE ATT&CK T1543.004 — LaunchDaemon](https://attack.mitre.org/techniques/T1543/004/) — Persistence mechanism reference

---

*Research completed: 2026-03-31*
*Ready for roadmap: yes*
