# TGmonitor

## What This Is

A tamper-resistant Mac menu bar agent that silently captures screenshots every 5 minutes, uses AI vision to analyze desktop activity, flags concerning behavior, and streams daily work journals to a VPS web dashboard. Built for monitoring 5 company Macs at JSR dental clinics.

## Core Value

Continuous, automated visibility into employee computer activity with intelligent flagging of concerning behavior — without interrupting the employee's workflow.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Lightweight Mac menu bar agent that runs silently in the background
- [ ] Screenshot capture every 5 minutes (configurable)
- [ ] Tamper-resistant: password required to disable, resistant to being killed/uninstalled
- [ ] Disguised as a different program (custom app name/icon)
- [ ] AI vision analysis of each screenshot (activity description, app detection)
- [ ] Concerning activity detection: file transfers outside network, USB usage, cloud uploads, suspicious behavior
- [ ] 30-day local screenshot retention with automatic cleanup
- [ ] Upload screenshots and analysis to VPS
- [ ] Web dashboard on VPS to view all employees
- [ ] Daily journal/timeline view per employee with thumbnails and AI captions
- [ ] Red flag highlighting for alarming activities
- [ ] Hardcoded VPS credentials encoded in compiled binary (not extractable)
- [ ] Google API key hardcoded and encoded for vision model access

### Out of Scope

- Email notifications — not needed for v1
- Windows/Linux support — all company machines are Macs
- Real-time screen streaming — screenshot-based is sufficient
- Employee self-service portal — only admin/manager views the dashboard
- Mobile app — web dashboard only for now

## Context

- 5 Mac computers across JSR dental clinic locations
- Owner (Thuan) has full legal rights over company-owned machines
- Employees know monitoring software is installed but it runs non-intrusively
- ~96 screenshots/day/machine at 5-min intervals = ~480 screenshots/day total
- At ~500KB compressed each: ~240MB/day, ~7.2GB/month across all machines
- Need cheapest viable AI vision model for analyzing ~480 images/day
- VPS already available for hosting the web dashboard

## Constraints

- **Platform**: macOS only (all company machines are Macs)
- **Cost**: Vision AI model must be cheapest viable option (research needed — Gemini Flash, GPT-4o-mini, Claude Haiku, Apple Vision)
- **Security**: Credentials must be encoded in compiled binary, not extractable via decompilation
- **Privacy**: Screenshots stored locally 30 days, transmitted to VPS encrypted
- **Performance**: Menu bar agent must be lightweight, no noticeable CPU/memory impact
- **Tamper resistance**: Cannot be disabled without password, resistant to Activity Monitor kill, Claude Code, or other dev tools

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mac menu bar agent (not full app) | Lightweight, invisible to user, always running | — Pending |
| Screenshot-based (not screen recording) | Lower CPU/storage, sufficient for activity tracking | — Pending |
| 5-minute interval | Balance between granularity and storage/API cost | — Pending |
| Cheapest vision AI model | Cost optimization for ~480 images/day | — Pending (research needed) |
| Web dashboard on VPS | Central viewing for owner, no per-machine access needed | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 after initialization*
