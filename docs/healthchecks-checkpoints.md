# Healthchecks benchmark trajectory

The problem is an API-only cumulative clone inspired by `healthchecks/healthchecks`. Every checkpoint is a complete product feature and all prior tests remain active.

| CP | Feature |
|---:|---|
| 1 | Interval-based monitoring |
| 2 | Execution lifecycle signals |
| 3 | Ping history |
| 4 | Cron schedules |
| 5 | OnCalendar schedules |
| 6 | Pause / Resume |
| 7 | Tags and filtering |
| 8 | Slug ping URLs and auto-provisioning |
| 9 | Email pings |
| 10 | Ping filtering rules |
| 11 | Multiple projects and API keys |
| 12 | Copy and transfer checks |
| 13 | Team management and ACL |
| 14 | Webhook notifications |
| 15 | Public status badges |
| 16 | Downtime history and analytics |
| 17 | Scheduled reports |
| 18 | Down reminders (nags) |

The trajectory intentionally defers multi-project ACL and notifications until late checkpoints so early architecture choices are stressed by later changes. External effects (SMTP ingest, webhook delivery, email reports) have importable seams for deterministic offline evaluation.
