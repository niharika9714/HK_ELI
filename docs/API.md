# API contract

All protected endpoints use the verified server session/identity. Obtain CSRF from `GET /api/session`; send it as `X-CSRF-Token` for every POST. Local test login is `POST /api/login {"user_id":"synthetic-hk-rm"}` and returns a rotated CSRF token. This route is unavailable when corporate identity mode is configured.

| Endpoint | Behavior |
|---|---|
| `GET /api/dashboards` | Current user and authorized configured dashboard keys |
| `POST /api/v1/requests` | `{question,dashboards:[],formats:[]}` → 202 `{run_id,status}`; optional typed `plan` revalidated server-side |
| `GET /api/v1/runs/{id}` | Pending/running/completed/failed/cancelled/interrupted; owned answer and trace |
| `POST /api/v1/runs/{id}/cancel` | Requests cancellation; terminal jobs remain terminal |
| `GET /api/v1/runs/{id}/evidence` | Scoped evidence records |
| `GET /api/v1/runs/{id}/trace` | Sanitized task state and run measurements |
| `GET /api/v1/skills` | Authorized versioned skills with JSON input/output schemas |
| `GET /api/v1/tableau/assets?dashboard=key` | Authorized live discovered views and reviewed definitions |
| `POST /api/v1/tableau/resolve` | Validates exact `ViewRequest` against discovered scope |
| `POST /api/v1/tableau/embed` | Fresh short-lived embedding JWT and original-view descriptor |
| `POST /api/v1/tableau/analyze` | Queues typed scoped analytical skill |
| `POST /api/v1/pricing/solve` | Queues explicitly indicative synthetic coupon/strike draft |
| `POST /api/v1/artifacts` | `{run_id,formats:["pdf"]}` creates protected draft from owned existing evidence |
| `GET /api/v1/artifacts/{id}` | Protected draft; `?manifest=true` returns full provenance |
| `GET /api/v1/health` | Process health, no external connectivity assertion |
| `GET /api/v1/ready` | State database check, mode; external connections not probed |

Compatibility aliases: `/api/chat`, `/api/jobs/{id}`, `/api/embed-token`. These preserve the primary route names and job/embed roles; the new typed response is documented here and is not a promise of every historical frontend payload being interchangeable.

`ViewRequest` is `{dashboard,view_id,filters:{field:[values]},parameters:{field:value},highlights:{field:[values]},required_grain,analysis}`. Omitting filters retains published defaults. `analysis` uses action `analyze`, exact source view_id, dimensions, measure, aggregation, optional calendar period/date_column, and chart. Supported typed aggregates are approved sums; published summary row counts and means are deliberately refused. Export parameters are refused until equivalence is verified. Explicit task plans and all input/output schemas are visible through the skill registry.

Example fixture request: `{"question":"Q6: Review upcoming maturity and rollover opportunities","dashboards":[],"formats":["docx","xlsx"]}`. Poll the returned run ID until terminal. A completed job may contain a partial analytical answer: inspect `task_statuses` and warnings. Source failure is never evidence that a different financial chart answers the original request.

Response `analysis.results` contains task data; `visualizations` contains original Tableau descriptors; `narrative` contains cited claims; `evidence` contains records; `source_modes`, `warnings`, `artifacts`, `plan` and measured `metrics` explain scope. Permission failures return 403; absent/expired/other-owner resources return 404; invalid payloads return 400; active job saturation returns 429. Task failures use sanitized exception categories in trace warnings. No raw credential-bearing upstream errors are exposed.

`requirement_coverage` reports the original quoted requirements, their task/parameter bindings and unresolved reasons. Plans without an inventory (legacy explicit plans/fixtures) report `not_assessed`. New live plans must cover the independently inventoried request; unsupported or missing-input branches return limitations. This is structural validation, not proof of semantic equivalence. See `PLANNING.md`. No clarification/resume endpoint or live bank API contract was added.

Document follow-up update: requests now accept `conversation_id`/`context_turn_ids`, with owned conversation create/list/get/delete endpoints. A saved result can return `needs_format` with a `document_format` clarification and resume on a format reply in the same chat. This is document-specific and does not change bank/pricing API contracts. All chat/API document rendering uses one final builder. See `CHAT_DOCUMENTS.md` for the complete contract and retention rules.
