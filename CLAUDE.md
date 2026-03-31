<!-- GSD:project-start source:PROJECT.md -->
## Project

**TGmonitor**

A tamper-resistant Mac menu bar agent that silently captures screenshots every 5 minutes, uses AI vision to analyze desktop activity, flags concerning behavior, and streams daily work journals to a VPS web dashboard. Built for monitoring 5 company Macs at JSR dental clinics.

**Core Value:** Continuous, automated visibility into employee computer activity with intelligent flagging of concerning behavior — without interrupting the employee's workflow.

### Constraints

- **Platform**: macOS only (all company machines are Macs)
- **Cost**: Vision AI model must be cheapest viable option (research needed — Gemini Flash, GPT-4o-mini, Claude Haiku, Apple Vision)
- **Security**: Credentials must be encoded in compiled binary, not extractable via decompilation
- **Privacy**: Screenshots stored locally 30 days, transmitted to VPS encrypted
- **Performance**: Menu bar agent must be lightweight, no noticeable CPU/memory impact
- **Tamper resistance**: Cannot be disabled without password, resistant to Activity Monitor kill, Claude Code, or other dev tools
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
### Screenshot Capture API Decision (CRITICAL)
### AI Vision Model (CRITICAL COST DECISION)
#### Cost Comparison Table — 480 images/day, 30 days = 14,400 images/month
- Formula: tiles × 258, where tiles = ceil(W/crop_unit) × ceil(H/crop_unit), crop_unit = floor(short_side / 1.5) = 512
- Tiles: ceil(1366/512) × ceil(768/512) = 3 × 2 = 6 tiles → **1,548 image tokens**
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
### Web Dashboard (VPS)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.115+ | REST API backend | Python, fast, async, minimal boilerplate. Single `main.py` can serve the entire API. Thuan's existing Python expertise. |
| Next.js | 15.x | Web frontend | App Router, React Server Components, SSR built-in. Best for timeline/thumbnail views. Well-supported ecosystem. |
| PostgreSQL | 16+ | Metadata database | Store screenshot records, AI analysis, timestamps, flags. Not for image blobs. |
| SQLite | — | DO NOT USE for production | Cannot handle 5 concurrent agents writing simultaneously without WAL tuning. Use PostgreSQL. |
| Local VPS filesystem + nginx | — | Image file serving | Store JPEG files in `/var/data/screenshots/{machine_id}/{date}/` and serve via nginx. Fast, free, no egress cost. |
| Redis | 7.x | Optional job queue | If upload queue grows, use Redis + RQ (Python). Skip for MVP — direct HTTP upload is fine for 5 machines. |
### Infrastructure
| Component | Technology | Why |
|-----------|------------|-----|
| VPS | Any existing VPS (Nginx + Docker) | Already available per PROJECT.md |
| Container | Docker Compose | FastAPI + PostgreSQL + Nginx in single compose file |
| Image serving | Nginx static files | Direct disk reads, no app-layer overhead |
| TLS | Let's Encrypt / Certbot | Free TLS for dashboard HTTPS |
| Auth | HTTP Basic Auth or simple JWT | Dashboard is admin-only, single user (Thuan). No OAuth needed. |
| Agent upload | HTTPS POST to FastAPI | Authenticated with hardcoded API key (obfuscated in binary) |
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
## Installation
### Mac Agent (Swift Package Manager)
- `com.apple.security.screen-recording` (ScreenCaptureKit)
- No App Sandbox (required for LaunchDaemon system-level access)
### VPS Backend
# Python backend
# Frontend
# Docker Compose
## Security Notes
### Credential Obfuscation in Binary
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
