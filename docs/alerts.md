# Alert, reminder and escalation rules

Alerts support officials. They never approve, reject or decide an application.

## Default alert rules

| Code | Entity | Trigger | Offset | Severity |
|---|---|---|---|---|
| APP_SLA_80 | APPLICATION | AGEING (80% of SLA) | — | WARNING |
| APP_SLA_BREACH | APPLICATION | AGEING (SLA elapsed) | — | CRITICAL |
| APP_SLA_EVERY_3 | APPLICATION | AFTER_DUE | +3 days | CRITICAL |
| EVC_T-7 / T-3 / T-1 | EVC | BEFORE_DUE | -7, -3, -1 | INFO / WARNING |
| EVC_T0 | EVC | ON_DUE | 0 | CRITICAL |
| EVC_OVERDUE_DAILY | EVC | AFTER_DUE | daily | CRITICAL |
| UT_T-30 / T-15 / T-7 / T-1 | UNDERTAKING | BEFORE_DUE | -30..-1 | WARNING |
| UT_T0 + daily overdue | UNDERTAKING | ON_DUE / AFTER_DUE | 0 / +1 | CRITICAL |
| DOC_T-90 / T-60 / T-30 / T-7 | DOCUMENT | BEFORE_DUE | -90..-7 | WARNING |
| DOC_T0 + weekly overdue | DOCUMENT | ON_DUE / AFTER_DUE | 0 / +7 | CRITICAL |

## Escalation ladder

| Level | Threshold (days overdue) | Role |
|---|---|---|
| 0 | — | Responsible officer or institution |
| 1 | +3 | Regional Officer |
| 2 | +10 | Bureau Officer |
| 3 | +20 | Designated senior authority (Super Admin in demo) |

Notifications are inserted with a unique `dedupe_key` of `{rule_id}:{entity_type}:{entity_id}:{level}:{recipient_id}:{date_bucket}`. Re-running a job never duplicates the same alert.

Template placeholders: `{institution}`, `{app_id}`, `{due_date}`, `{days_left}`, `{days_overdue}`, `{stage}`, `{officer}`.
