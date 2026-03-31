# Feature Landscape: Employee Monitoring / Screenshot Agent

**Domain:** Mac employee monitoring and screenshot-based time tracking
**Researched:** 2026-03-31
**Project:** TGmonitor — 5-Mac dental clinic monitoring agent

---

## Competitive Reference Products

| Product | Core Positioning |
|---------|-----------------|
| Hubstaff | Remote team time tracking with optional screenshots; employee-friendly, privacy-first |
| Time Doctor | Precise proof-of-work for billing; screenshot + distraction nudges; payroll integration |
| ActivTrak | AI-driven productivity analytics; behavioral patterns; no keystroke logging |
| Teramind | Enterprise DLP + insider threat; OCR, stealth mode, behavior rules engine |
| DeskTime | Auto time tracking; app categorization; lightweight; random screenshot intervals |
| Monitask | Screenshot-focused; real-time live view; lightweight SaaS |
| WebWork | AI performance scoring from activity signals; automated summaries |

---

## Table Stakes

Features users (managers) expect. Missing = product feels broken or unreliable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Periodic screenshot capture | Core value delivery — visual proof of activity | Low | All products do this. Interval typically 5–30 min, configurable. Random or fixed. |
| Configurable capture interval | Different roles need different granularity | Low | DeskTime: 3/5/10/15/30 min options. Hubstaff: up to 3 per 10 min. |
| Screenshot thumbnail gallery | Primary way managers review activity | Low | Grid view by employee + day is the standard UI pattern. |
| Timestamp on every screenshot | Without this, screenshots are unactionable | Low | Every product does this. Includes app name and window title as metadata. |
| Per-employee view | Owner needs to distinguish between 5 machines | Low | Flat list filtering by employee name / machine ID. |
| Daily timeline view | Chronological activity review | Medium | Timeline of screenshot thumbnails with gaps showing idle/offline periods. |
| Active vs idle detection | Distinguish working vs away | Low-Medium | Mouse/keyboard event counting. Activity level % per interval. |
| App/window title tracking | Context for each screenshot | Low | Read active window title; no keylogging required. |
| Local data storage | Offline resilience; compliance | Low | All products store locally first, then sync. 30–90 day retention standard. |
| Upload to central dashboard | Central visibility for owner | Medium | All SaaS products stream to cloud. This project targets a VPS. |
| Screenshot retention policy | Storage management | Low | Auto-delete after N days (Teramind default: 90 days; project target: 30 days). |
| Agent runs on login | Monitoring must survive reboots | Low | LaunchAgent (macOS plist) — industry standard pattern. |

---

## Differentiators

Features that separate products or add meaningful value. Not universally expected.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI vision analysis of screenshots | Natural language description of what employee is doing — no manual review | High | Core differentiator for TGmonitor. Most competitors use app/URL tracking instead of image analysis. Teramind uses OCR; newer products starting to use vision models. |
| Automatic AI caption per screenshot | Manager reads 2-sentence summary instead of studying image | High | TGmonitor's primary differentiator. "Employee is reviewing a patient billing spreadsheet in Excel." |
| Red flag / alert highlighting | Surface concerning screenshots without manual scan | High | Most products alert on rule violations (app blocklist, file transfer volume). TGmonitor targets AI-detected behavioral anomalies visible in the screenshot. |
| App category auto-detection from screenshot | Identify app from visual content when window title is ambiguous | Medium-High | Teramind + OCR approach. Vision model approach is newer and stronger. |
| Concerning activity detection | USB insertion, cloud upload in progress, personal browsing | High | Hubstaff/ActivTrak detect via system APIs. TGmonitor detects visually (Finder copy dialog, browser upload, USB icon) — lower fidelity but no kernel extension needed. |
| Stealth / disguised agent | Monitoring runs without employee awareness of what process it is | Medium | Teramind offers this commercially. Custom app name + icon on TGmonitor achieves basic disguise. |
| Tamper resistance | Agent cannot be killed or removed by standard user | High | Teramind claims tamper-proof install. On macOS this requires specific hardening (privilege escalation, watchdog, plist protection). |
| Daily AI work journal | End-of-day narrative summary of employee activity | High | Not standard in current products. TGmonitor can generate this from aggregated screenshot captions. Strong differentiator. |
| Activity productivity scoring | Classify time as productive / unproductive / idle | Medium | DeskTime, ActivTrak do this via app categorization rules. TGmonitor can infer from vision analysis. |
| Multi-monitor support | Capture all active screens | Medium | Hubstaff supports multiple monitors. Important if employees use external displays. |
| Behavioral baseline + anomaly detection | Flag deviation from normal behavior patterns | High | ActivTrak, WebWork do this statistically. TGmonitor v1 does not need this; flag only specific visual patterns. |
| Live / real-time view | See current screen without waiting for interval | High | Monitask, Teramind offer this. Out of scope for TGmonitor v1. |
| OCR on screenshots | Extract text from captured images | High | Teramind flagship feature. Enables searching for typed content, document names. Not needed for TGmonitor v1. |

---

## Anti-Features

Things to deliberately NOT build for this specific use case (5 Macs, dental clinic, owner-operated).

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Keystroke logging | Captures passwords, patient PII, HIPAA risk; not needed for visual monitoring | Screenshot + window title sufficient for activity context |
| Email / chat content monitoring | HIPAA exposure; legal risk in Vietnam; far beyond scope | Not needed — visual screenshots reveal context |
| Real-time screen streaming / video recording | 100x+ storage and bandwidth cost; CPU intensive; screenshot-based is sufficient | 5-min screenshot intervals provide adequate granularity |
| Employee self-service portal | Owner-only access model; adding employee portal doubles surface area | Admin-only dashboard |
| Productivity score / gamification | Dental clinic context — not a KPI-driven knowledge work environment | AI captions + flags give owner qualitative visibility |
| Payroll / billing integration | Not relevant for salaried clinic employees | No integration needed |
| GPS / mobile tracking | Mac desktop monitoring only | Desktop agent only |
| Policy rules engine | Complex behavioral rule authoring requires ongoing maintenance | AI vision flags + owner judgment replaces rules |
| Whitelist / blacklist app categorization | Requires maintaining category lists; AI caption handles this automatically | AI caption describes app context naturally |
| Multi-tenant / team hierarchy | Single owner, 5 machines — no org hierarchy needed | Flat employee list on dashboard |
| Public API / webhooks | No downstream integrations planned | Internal VPS only |
| Browser extension | Agent is OS-level; browser extension adds complexity without benefit | OS-level screenshot captures browser activity in screenshot |

---

## Feature Dependencies

```
Screenshot capture
  └── Timestamp metadata
  └── Window title / app detection
  └── Local storage (30-day)
        └── Upload to VPS
              └── Web dashboard (thumbnail gallery)
                    └── Daily timeline view
                    └── Per-employee view

AI vision analysis
  └── Screenshot capture (input)
  └── Activity caption (output)
        └── Daily journal aggregation
        └── Red flag detection
              └── Flag highlighting in dashboard

Tamper resistance
  └── LaunchAgent (persistence on login)
  └── Watchdog process (restart if killed)
  └── Password-protected disable mechanism

Agent disguise
  └── Custom app name + icon
  └── Process name obfuscation
```

---

## MVP Recommendation

Prioritize for TGmonitor v1:

1. **Screenshot capture every 5 min** — core value, everything else depends on this
2. **AI vision caption per screenshot** — the primary differentiator over commodity monitoring tools
3. **Red flag detection** — what the owner actually cares about; identifies concerning behavior
4. **Local storage + VPS upload** — enables dashboard access
5. **Daily timeline with thumbnails + captions** — primary dashboard UX
6. **Tamper resistance** — prevents circumvention; required for monitoring to be reliable
7. **Agent disguise** — basic stealth via custom app name/icon

**Defer to v2:**
- OCR on screenshots (complex, not needed when vision model reads screen content naturally)
- Real-time live view (disproportionate complexity vs. 5-min polling)
- Behavioral baseline / anomaly trending (needs historical data accumulation first)
- Multi-monitor capture (add after v1 validation; most clinic machines likely single monitor)
- Daily AI journal narrative (nice to have — can be added after captions work reliably)

---

## Screenshot Capture: Industry Parameter Reference

| Parameter | Typical Range | TGmonitor Target |
|-----------|--------------|-----------------|
| Capture interval | 3–30 min (some products: up to 3/10 min) | 5 min (configurable) |
| Image format | JPEG compressed | JPEG, ~500KB/screenshot |
| Resolution | Full screen resolution | Native resolution, compressed |
| Multiple monitors | Supported by Hubstaff, Teramind | Capture primary screen first; secondary later |
| Trigger types | Time-based, event-based (file transfer, app launch) | Time-based v1; event-triggered later |
| Random vs fixed | DeskTime: random within interval; others: fixed | Fixed interval (predictable for testing) |
| Retention local | 30–90 days | 30 days |
| Blur / privacy | Optional in Hubstaff, Teramind | Not needed (owner has full rights) |

---

## Alert / Flag Taxonomy

What the monitoring ecosystem flags as concerning — calibrated against TGmonitor's context:

| Alert Type | How Industry Detects | TGmonitor Approach | Priority |
|------------|---------------------|--------------------|----------|
| Large file transfer / USB activity | System API (file system events) | Vision: Finder copy dialog, USB icon visible | High |
| Cloud upload in progress | Network monitoring / browser extension | Vision: browser showing Dropbox/Drive upload | Medium |
| Personal social media / video | App blocklist / URL categorization | Vision: AI identifies Facebook, YouTube, etc. | Medium |
| Unauthorized app running | App list monitoring | Vision: AI describes unfamiliar app | Medium |
| Extended idle / away | Mouse/keyboard inactivity | Activity level % from input events | Low |
| Sensitive document exposure | OCR + keyword match | Vision: AI notes document type / content | Low-v1 |
| Suspicious behavior pattern | Behavioral baseline deviation | Manual review triggered by flags | Deferred |

---

## Confidence Assessment

| Area | Confidence | Sources |
|------|------------|---------|
| Table stakes features | HIGH | Multiple products directly verified: Hubstaff, DeskTime, Teramind, Monitask |
| Screenshot parameters | HIGH | Official Hubstaff, DeskTime, Teramind docs |
| Differentiators (AI vision) | MEDIUM | WebWork, WebSearch; AI vision for screenshots is emerging — not all products detailed |
| Tamper resistance | MEDIUM | Teramind claims tamper-proof; macOS-specific mechanisms not disclosed by vendors |
| Alert taxonomy | MEDIUM | Multiple sources; USB/file alerts well-documented; AI vision flagging is newer |
| Anti-feature recommendations | HIGH | Derived from project scope (5 Macs, dental clinic, owner-operated) — well-matched to context |

---

## Sources

- [Hubstaff Screenshot Features](https://hubstaff.com/time-tracker-with-screenshots)
- [Teramind Screenshot Monitoring](https://www.teramind.co/features/employee-screenshot-monitoring/)
- [Teramind Hidden Monitoring](https://www.teramind.co/solutions/hidden-employee-monitoring/)
- [DeskTime Features](https://desktime.com/features/time-tracking-with-screenshots)
- [WebWork AI Monitoring](https://www.webwork-tracker.com/features/ai-employee-monitoring-software)
- [Monitask Screenshot Monitoring](https://www.monitask.com/en/blog/employee-monitoring-software-with-screenshots)
- [ActivTrak vs Time Doctor Comparison](https://peoplemanagingpeople.com/tools/activtrak-vs-time-doctor/)
- [Best Employee Monitoring Software 2026](https://hubstaff.com/blog/best-employee-monitoring-software/)
- [USB File Transfer Monitoring](https://www.currentware.com/products/accesspatrol/usb-device-reports/)
