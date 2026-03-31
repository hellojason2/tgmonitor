# Domain Pitfalls: Mac Employee Monitoring / Screenshot Agent

**Domain:** macOS background monitoring agent with AI vision analysis
**Researched:** 2026-03-31
**Confidence:** HIGH (multiple official Apple sources, community verification)

---

## Critical Pitfalls

Mistakes that cause rewrites, blocked deployments, or irreversible user-facing disruption.

---

### Pitfall 1: macOS Sequoia Monthly Screen Recording Permission Nag

**What goes wrong:** Starting with macOS 15 (Sequoia), Apple prompts every user once per month asking whether to continue allowing the screen recording app. On a monitoring agent that is supposed to run silently, this is catastrophic — the employee sees a system dialog saying "[App Name] would like to record your screen."

**Why it happens:** Apple hardened privacy enforcement in macOS 14/15. The `CGWindowListCreateImage` API is fully deprecated/obsoleted in macOS 15.0. Apps using ScreenCaptureKit get the monthly prompt. The `Persistent Content Capture` entitlement (which bypasses this) is undocumented, not publicly obtainable, and appears intended only for VNC/MDM-managed device scenarios.

**Consequences:**
- Employee sees a dialog every month revealing that a screen recording app is running — defeats silent operation
- If employee denies the prompt, screenshots stop silently with no error surfaced to the agent
- No workaround exists without the restricted entitlement or MDM management

**Prevention:**
- Deploy via MDM (Jamf, Mosyle, or Apple Business Manager) and use a TCC configuration profile to pre-grant screen recording permission at the OS level, bypassing the dialog entirely
- If MDM is not used: accept the monthly dialog and build the agent to detect permission loss and alert the admin dashboard (not the employee machine)
- Do NOT attempt to suppress or auto-dismiss the dialog programmatically — Apple will likely break that approach in future updates

**Warning signs:**
- Screenshots start returning blank/black images with no exception thrown
- `CGPreflightScreenCaptureAccess()` returns false after previously returning true
- No upload activity appears in VPS dashboard

**Phase mapping:** Phase 1 (macOS agent core). Must be addressed before any other agent functionality.

---

### Pitfall 2: CGWindowListCreateImage is Obsoleted in macOS 15

**What goes wrong:** If the agent is written using `CGWindowListCreateImage` (the legacy screenshot API), it will fail to compile on macOS 15 (Sequoia) and break silently on macOS 14 (Sonoma) with deprecation warnings.

**Why it happens:** Apple deprecated the API in macOS 14.0 and fully obsoleted it in macOS 15.0. The replacement is `ScreenCaptureKit` with `SCScreenshotManager`.

**Consequences:**
- Build fails on any Mac running macOS 15+ once the deprecated API is removed from SDK
- Apps using it in Sequoia 15.1 show a security warning to users that the app "may be attempting to bypass security settings"

**Prevention:**
- Use `ScreenCaptureKit` from day one: `SCScreenshotManager.captureImage(contentFilter:configuration:)` is the current API
- The API is async — account for this in the capture loop design; do not assume synchronous behavior
- Test on macOS 14 and 15 specifically

**Warning signs:**
- Compiler warnings for `CGWindowListCreateImage` usage
- App shows security dialog on Sequoia 15.1

**Phase mapping:** Phase 1 (screenshot capture core). Foundational API choice — must be correct from the start.

---

### Pitfall 3: TCC Permission Resets on Every Rebuild (Code Signing)

**What goes wrong:** During development and deployment, the screen recording permission granted to the app binary resets after each rebuild because macOS TCC (Transparency, Consent, and Control) tracks permissions by a hash of the binary plus signing identity. Ad-hoc or unsigned builds get a new hash on each compile.

**Why it happens:** TCC stores permissions keyed to the app's bundle identifier AND code signature hash. An unsigned or ad-hoc signed app gets a new effective identity on each build.

**Consequences:**
- Every deployment to a new employee Mac requires manually granting screen recording permission
- If the binary is updated (bug fix, new feature), the permission must be re-granted on each machine
- During development, permission dialogs appear constantly

**Prevention:**
- Sign with a stable Developer ID certificate (Apple Developer Program, $99/year) so the TeamIdentifier stays constant across builds
- Alternatively, deploy via MDM with a TCC configuration profile that grants permission by bundle ID — this survives binary updates
- Never deploy unsigned or ad-hoc signed builds to production machines

**Warning signs:**
- Screen recording stops working after binary update on production machines
- TCC permission shows as granted in System Settings but screenshots are black

**Phase mapping:** Phase 1 (deployment setup). Must be established in the very first deployment.

---

### Pitfall 4: Agent Killed via Activity Monitor — No Tamper Resistance

**What goes wrong:** Any employee with basic macOS knowledge can open Activity Monitor, find the agent process (even a disguised one), and force-quit it. Without `KeepAlive` enforcement, monitoring stops permanently until the user logs out and back in (or reboots).

**Why it happens:** `LaunchAgent` with `KeepAlive: true` will auto-restart a killed process in approximately 10 seconds — but this is only in effect if the plist is correctly installed. A `LaunchAgent` (user-level, `~/Library/LaunchAgents/`) can be unloaded by the same user with `launchctl unload` without requiring a password. Login Items visible in System Settings > General > Login Items can be toggled off by any user.

**Consequences:**
- Employee kills the agent, monitoring stops for the rest of the day
- Employee removes the LaunchAgent plist, monitoring never restarts

**Prevention:**
- Install as a `LaunchDaemon` (root-level, `/Library/LaunchDaemons/`) with `KeepAlive: true` — user-level processes cannot unload root-level daemons without administrator password
- Set correct plist ownership: root:wheel, mode 644
- Do NOT use Login Items (visible in System Settings and trivially disabled)
- Do NOT use `~/Library/LaunchAgents/` — user can delete or unload without sudo
- Use SIP (System Integrity Protection) to protect `/Library/LaunchDaemons/` from modification — SIP is enabled by default on all modern Macs
- The agent binary itself should live in `/Library/` or `/usr/local/lib/` not in `~/Applications/`

**Warning signs:**
- Dashboard shows gaps in screenshot timeline for a specific machine
- Agent is running as LaunchAgent rather than LaunchDaemon in ps output

**Phase mapping:** Phase 1 (persistence layer). LaunchDaemon installation must be part of the initial installer.

---

### Pitfall 5: Credentials Are Trivially Extractable from the Binary

**What goes wrong:** The PROJECT.md specifies "hardcoded VPS credentials encoded in compiled binary (not extractable)" and "Google API key hardcoded and encoded." Both of these are significantly more breakable than they appear. Running `strings /path/to/binary` or using a disassembler like Hopper or IDA Free will expose embedded strings, including XOR-obfuscated ones if the key is static.

**Why it happens:** There is no cryptographic primitive that makes secrets stored in a binary "not extractable." Any static encoding (Base64, XOR, simple cipher) can be reversed by examining the binary at runtime via `lldb` or `dtrace` — the key must be in memory to use it, so it can always be read at the point of use.

**Consequences:**
- Employee with moderate technical skill extracts the Google API key and incurs large vision API charges on your account
- VPS credentials extracted allow direct SSH or database access to the monitoring server
- Leaked API key enables an attacker to exfiltrate all stored screenshots from VPS

**Prevention:**
- **VPS API endpoint:** Rather than embedding VPS credentials, the agent should authenticate to a purpose-built REST API on the VPS using a short-lived token or HMAC-signed requests. The REST API lives on the VPS and has the actual database credentials in environment variables — never in the binary
- **Vision API key:** Route all Gemini/vision calls through the VPS backend proxy. The agent sends the raw screenshot to `POST /analyze` on your VPS; the VPS calls Gemini with its securely stored key. The agent binary never sees the Google API key
- **If a secret must be in the binary:** Use a combination of compile-time obfuscation (LLVM obfuscator pass) + runtime decryption where the decryption key is derived from a hardware identifier (machine UUID) — this at least makes the key non-portable even if extracted
- **Google API key restriction:** Add IP address restrictions in Google Cloud Console so the key only works from the VPS IP, not from arbitrary machines

**Warning signs:**
- Unexpected Gemini API usage spikes (set billing alerts)
- Unauthorized logins to VPS from non-clinic IPs

**Phase mapping:** Phase 1 (security design). Architectural decision that cannot be retrofitted cheaply.

---

## Moderate Pitfalls

---

### Pitfall 6: Screenshot Interval Timer Wakes CPU Unnecessarily

**What goes wrong:** Using a repeating `NSTimer` or `DispatchQueue.asyncAfter` loop for the 5-minute capture interval prevents the CPU from entering deep idle states, causing elevated battery drain on MacBook-based clinic machines.

**Why it happens:** `NSTimer` with standard scheduling fires on a precise cadence that keeps the CPU from coalescing wakeup events with other system timers.

**Prevention:**
- Use `NSBackgroundActivityScheduler` with a suitable interval and `qualityOfService: .background` — this API explicitly tells macOS to coalesce wakeups
- Set `NSTimer.tolerance` to 30 seconds if NSTimer is used — allows the OS to shift firing time for power optimization
- Avoid doing any work in the timer callback beyond dispatching a screenshot task; keep the main thread idle otherwise

**Warning signs:**
- `powermetrics` shows the agent process as a top energy consumer
- Battery status shows "apps using significant energy" alert for the agent

**Phase mapping:** Phase 1 (capture loop implementation).

---

### Pitfall 7: Upload Failures Cause Silent Data Loss

**What goes wrong:** Network connectivity at dental clinics is intermittent (slow WiFi, router reboots, ISP outages). If the agent uploads screenshots immediately after capture with no retry queue, a network blip causes permanent loss of screenshots for that period.

**Why it happens:** Naive implementation: capture → upload → on failure, discard and continue. No local queue, no retry backoff.

**Consequences:**
- Timeline gaps in the VPS dashboard for affected periods
- If the disk queue fills (30 days × 5 machines × ~500KB), old screenshots get deleted before upload

**Prevention:**
- Maintain a local upload queue: store screenshot to disk first, then attempt upload
- On upload failure, mark the file as "pending upload" and retry with exponential backoff (1min, 5min, 30min, 1hr)
- Use `NWPathMonitor` to detect connectivity restoration and trigger queue flush
- The 30-day local retention requirement already implies local disk storage — use this as the upload source, not a separate temp copy

**Warning signs:**
- VPS dashboard shows consistent gaps at the same time of day (overnight, early morning)
- Local screenshot directory grows unexpectedly large

**Phase mapping:** Phase 2 (upload pipeline).

---

### Pitfall 8: Vision AI Cost Overrun from Uncompressed or Full-Resolution Images

**What goes wrong:** Sending raw PNG screenshots from Retina displays (2560x1600 px, 3–10MB each) to Gemini Flash costs substantially more per image due to token counting by pixel area. At 480 images/day × 30 days, cost overruns can be significant.

**Why it happens:** Gemini Flash charges ~$0.0011 per image at standard resolution. A full Retina screenshot may be tokenized at a higher rate than a downscaled version. The relationship is non-linear — halving resolution more than halves cost.

**Prevention:**
- Resize screenshots to 1280x800 px (standard 1x resolution) before sending to vision API — sufficient for activity recognition
- Use JPEG at 85% quality rather than PNG for API uploads (PNG for local storage if needed for forensics, JPEG for API)
- Test: send a 1280x800 JPEG vs full Retina PNG to Gemini Flash and compare cost per image
- Calculate break-even: at ~$0.0011/image × 480/day = $0.53/day = $16/month — this is already cheap; validate actual cost doesn't spike with full-resolution

**Warning signs:**
- Gemini billing shows higher-than-expected token consumption per image
- Daily API cost significantly exceeds $16/month estimate

**Phase mapping:** Phase 2 (vision integration). Set up before enabling vision on all 5 machines.

---

### Pitfall 9: App Disguise Breaks TCC Bundle ID Tracking

**What goes wrong:** The project requires the agent be "disguised as a different program (custom app name/icon)." If the bundle ID is changed as part of the disguise (e.g., from `com.jsr.monitor` to `com.apple.photolibrary-helper`), every rename invalidates the TCC permission granted to the previous bundle ID.

**Why it happens:** TCC tracks permissions by bundle identifier. Changing the bundle ID is functionally a new app from TCC's perspective.

**Prevention:**
- Choose a single stable bundle ID at project start (e.g., `com.jsr.systemhelper`) and never change it
- The disguise should be limited to: display name, icon, and process name — not the bundle ID
- Do not mimic system bundle IDs (e.g., `com.apple.*`) — Gatekeeper and SIP will block or flag this behavior
- Renaming the app after MDM TCC profile deployment requires updating the MDM profile's bundle ID reference

**Warning signs:**
- Screen recording permission disappears after a build that changed the bundle ID
- System logs show TCC denial for the new bundle ID

**Phase mapping:** Phase 1 (app identity setup). Set bundle ID once, freeze it.

---

### Pitfall 10: macOS Update Breaks Screen Recording Silently

**What goes wrong:** Apple's macOS major updates (annually, September/October) frequently introduce breaking changes to screen capture APIs, TCC permission behavior, and entitlement requirements. Apps break silently — they continue running but screenshots become black or return errors.

**Why it happens:** Apple has changed screen capture behavior in Catalina (TCC introduced), Monterey (ScreenCaptureKit introduced), Ventura (SCK required for new features), Sonoma (SCK changes), and Sequoia (monthly prompts, CGWindowListCreateImage obsoleted). Each release introduces new requirements.

**Prevention:**
- Test against each new macOS beta (join Apple Developer Program — free tier available — to access betas)
- Subscribe to Apple Developer release notes and ScreenCaptureKit WWDC sessions each year
- Build the agent to log a "screenshot capture failed" event to the VPS dashboard — so you know when something breaks before employees notice gaps
- Maintain a dedicated test Mac running the latest macOS beta in the clinic (or use a VM with macOS for basic testing)
- Pin the macOS version on production clinic Macs until the agent is verified on the new version (MDM can delay auto-updates)

**Warning signs:**
- All 5 machines show screenshot gaps starting from the same date (macOS update day)
- Agent process is running but no new screenshots appear locally

**Phase mapping:** Phase 1 (monitoring/alerting). Build health reporting into v1.

---

## Minor Pitfalls

---

### Pitfall 11: JPEG Artifacts Degrade AI Vision Accuracy for Text Detection

**What goes wrong:** JPEG compression at low quality (< 70%) introduces block artifacts around text, making OCR and vision AI classification less accurate. The AI may misread application names, URLs, or file paths in the screenshot.

**Prevention:**
- Use JPEG quality 80–85% minimum for images sent to vision API
- For local 30-day archival, use 90% JPEG or PNG depending on storage budget
- Test vision AI accuracy at quality 75, 80, 85, 90 with representative screenshots from clinic workstations

**Phase mapping:** Phase 2 (image pipeline tuning).

---

### Pitfall 12: Multi-Display Capture Captures Wrong Screen

**What goes wrong:** On Macs connected to external monitors, `SCDisplay` enumeration in ScreenCaptureKit may not consistently return the "primary" display. If the employee's primary work is on a second display, the agent may capture the wrong screen.

**Prevention:**
- Capture all connected displays separately or capture the display at index 0 of `SCShareableContent.displays` sorted by `displayID`
- Log which display was captured in metadata so admin can see if a secondary display exists but is not being captured
- Consider capturing all displays and stitching, or alternate captures between displays

**Phase mapping:** Phase 2 (capture configuration).

---

### Pitfall 13: Local Storage Grows Without Automatic Pruning

**What goes wrong:** 30-day retention of ~500KB screenshots per capture × 5 min intervals = ~144 screenshots/day/machine = ~72MB/day = ~2.2GB/month local. Without enforced pruning, disk fills on smaller MacBook SSDs.

**Prevention:**
- Run a cleanup job daily (via `NSBackgroundActivityScheduler`) deleting screenshots older than 30 days
- Cap total local storage at a configurable ceiling (e.g., 3GB); delete oldest files first if limit is reached
- Log disk usage stats to VPS dashboard

**Phase mapping:** Phase 2 (storage management).

---

### Pitfall 14: Legal Notice Requirement Even on Company Machines

**What goes wrong:** In Vietnam, even on company-owned machines, labor law and data protection regulations may require employers to notify employees that their computer activity is monitored. Failure to provide this notice may create legal exposure during termination disputes or labor audits.

**Why it happens:** The project notes "employees know monitoring software is installed" — but verbal notice may not be sufficient. Many jurisdictions require written notice in the employment contract or onboarding documentation.

**Prevention:**
- Add monitoring disclosure to employee contracts and onboarding paperwork: "This computer is monitored. Screenshots are captured every 5 minutes and reviewed by management."
- Retain signed copies of the disclosure
- This is a legal/HR item, not a technical one — but failure to address it becomes a technical project's liability

**Phase mapping:** Pre-Phase 1 (before any deployment). Do this before installing on any machine.

---

## Phase-Specific Warnings Summary

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| macOS agent setup | Monthly screen recording permission dialog (Sequoia) | MDM-managed TCC profile or accept dialog + admin alert |
| Screenshot capture API | CGWindowListCreateImage obsoleted in macOS 15 | Use ScreenCaptureKit from day one |
| Persistence mechanism | LaunchAgent user can kill/unload without password | Use LaunchDaemon in /Library/LaunchDaemons/ |
| Credential storage | API keys extractable from binary via `strings` | Route all external API calls through VPS backend proxy |
| macOS updates | Annual API breakage (ScreenCaptureKit changes) | Subscribe to betas, pin macOS version via MDM, build health alerts |
| Code signing | TCC permission resets on every rebuild | Developer ID certificate + stable bundle ID |
| Upload pipeline | Network failures cause silent data loss | Local-first storage with retry queue |
| Vision API cost | Full Retina screenshots over-bill | Resize to 1280x800 JPEG 85% before API call |
| Multi-display | Wrong display captured | Enumerate all SCDisplay objects, capture primary or all |
| Legal compliance | No written monitoring notice to employees | Written disclosure in employment contract before deployment |

---

## Sources

- [Sequoia Screen Recording Prompts and Persistent Content Capture Entitlement — Michael Tsai Blog](https://mjtsai.com/blog/2024/08/08/sequoia-screen-recording-prompts-and-the-persistent-content-capture-entitlement/)
- [macOS Sequoia monthly screen recording prompt — 9to5Mac](https://9to5mac.com/2024/08/14/macos-sequoia-screen-recording-prompt-monthly/)
- [CGWindowListCreateImage obsoleted in macOS 15 — MacPorts bug tracker](https://trac.macports.org/ticket/71136)
- [A look at ScreenCaptureKit on macOS Sonoma — Nonstrict](https://nonstrict.eu/blog/2023/a-look-at-screencapturekit-on-macos-sonoma/)
- [ScreenCaptureKit official Apple documentation](https://developer.apple.com/documentation/screencapturekit/)
- [Capturing screen content in macOS — Apple Developer](https://developer.apple.com/documentation/ScreenCaptureKit/capturing-screen-content-in-macos)
- [macOS TCC Screen Recording permission process attribution — Apple Developer Forums](https://developer.apple.com/forums/thread/760483)
- [LaunchAgents and LaunchDaemons Complete Guide — MundoBytes](https://mundobytes.com/en/How-to-use-launchagents-and-launchdaemons-on-macOS/)
- [launchd KeepAlive examples — GitHub/tjluoma](https://github.com/tjluoma/launchd-keepalive)
- [OWASP: API Keys Hardcoded in App Package — MASWE-0005](https://mas.owasp.org/MASWE/MASVS-AUTH/MASWE-0005/)
- [Securing your Gemini API key — Google AI Developers Forum](https://discuss.ai.google.dev/t/securing-your-gemini-api-key-is-crucial/106912)
- [How Google AI Studio Securely Proxies Gemini Requests](https://glaforge.dev/posts/2026/02/09/decoded-how-google-ai-studio-securely-proxies-gemini-api-requests/)
- [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Energy Efficiency Guide for Mac Apps: Timers — Apple Developer Library](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/Timers.html)
- [Employee Monitoring Laws by State 2025 — flowace](https://flowace.ai/blog/employee-monitoring-laws/)
- [Mac Privacy: Sandboxed Mac apps can record your screen without you knowing — Felix Krause](https://krausefx.com/blog/mac-privacy-sandboxed-mac-apps-can-take-screenshots)
- [What are app entitlements — Eclectic Light Company](https://eclecticlight.co/2025/03/24/what-are-app-entitlements-and-what-do-they-do/)
- [MachObfuscator — GitHub/kam800](https://github.com/kam800/MachObfuscator)
