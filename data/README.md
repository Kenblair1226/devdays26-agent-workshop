# Synthetic workshop data

All names and usage values in this directory are fictional.

| File | Purpose |
| --- | --- |
| `ai-credit-usage.json` | Normalized organization billing AI-credit usage |
| `department-mapping.json` | Explicit user-to-cost-center/department attribution |
| `users-28-day.ndjson` | Behavioral usage metrics used by recommendation rules |
| `seats.json` | Mock Copilot seat inventory and last activity |
| `budgets.json` | Mock organization and user-level AI-credit budgets |

The billing data is a snapshot as of `2026-09-03T23:59:59Z`; it is not real-time.
It intentionally contains sparse samples in the 28-day training window
`2026-08-07` through `2026-09-03`. Missing days are not observed zeros; totals refer
to these samples rather than a complete organization report.

These are normalized teaching schemas, not verbatim GitHub REST responses.
Unit prices and discounts are fictional. Net AI credits are not raw model
tokens, and the amounts do not include license fees or Azure hosting costs.

Department aggregation uses pre-resolved cost-center or organizer mappings and
places unknown users in `Unallocated`. User/team memberships alone are not an
authoritative financial mapping. Null seat activity is unknown, not evidence of
inactivity. The user metrics cover their separate fixed 28-day window.

The identical JSON/NDJSON fixtures are included in `starter/data` and
`solution/data` so each code deployment is self-contained. Keep the copies in
sync; the solution's checkpoint tests check their semantic equality.
