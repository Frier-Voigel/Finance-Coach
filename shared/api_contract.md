# API Contract — Complete Specification (FROZEN)

Jointly reviewed and frozen for Phase 0.
Errors everywhere follow: `{ "error": "<code>", "message": "<human readable text>" }`.
Money is represented as whole rupees (int).
Dates are ISO 8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`).
Endpoints that depend on "today" accept `?as_of=YYYY-MM-DD` for deterministic evaluation with synthetic data.

---

## 1. Person A: Data Ingestion & Correction

### A1. Ingest (`/ingest`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `POST /ingest/upload` | Multipart form (`file: UploadFile`) | `{ "parsed": int, "inserted": int, "transactions": [Transaction] }` | Parses CSV or PDF bank statement, normalises merchants, de-duplicates, categorises, and inserts into DB. |
| `POST /ingest/sms` | `{ "text": str }` or `{ "messages": [str] }` | `{ "parsed": int, "inserted": int, "transactions": [Transaction] }` | Extracts bank SMS transactions using regex patterns with LLM fallback. |

### A2. Transactions & Categorisation (`/transactions`, `/engine/categorize`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `GET /transactions` | Query params: `category?`, `start?`, `end?`, `limit?` (default 50) | `[Transaction]` | Returns transactions ordered by date descending. |
| `PATCH /transactions/{id}` | `{ "category": str }` | `{ "updated": int, "rule_created": bool, "transaction": Transaction }` | Sets user-specified category, creates a pattern rule, and retroactively updates past non-user-set matching transactions. Returns total count updated. |

### A3. Rules (`/rules`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `GET /rules` | None | `[Rule]` | Lists all active categorization rules ordered by `created_at` descending. |
| `DELETE /rules/{id}` | None | `{ "deleted": bool }` | Deletes a learned rule. `404 rule_not_found`. |

### A4. Recurring & Subscriptions (`/recurring`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `GET /recurring` | None | `[Recurring]` | Lists detected subscriptions and recurring payments with status (`active`, `changed`, `unused`, `cancelled`). |
| `POST /recurring/{id}/mark-unused` | None | `Recurring` | Marks a subscription as unused for review/cancellation alerts. `404 recurring_not_found`. |

---

## 2. Person B: Money Model, Coach and Voice

### B1. Profile and Goals (`/profile`, `/goals`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `GET /profile` | None | `{ "monthly_income": int, "fixed_costs": { "name": int }, "emergency_fund_current": int, "emergency_fund_target": int, "updated_at": str \| null }` | Retrieves user profile (zeros if never set). |
| `PUT /profile` | `{ "monthly_income": int, "fixed_costs"?: dict, "emergency_fund_current"?: int, "emergency_fund_target"?: int }` | Profile object | Updates profile configuration. |
| `GET /goals` | None | `{ "surplus": int, "goals": [GoalProjection], "emergency_fund": GoalProjection \| null }` | Returns projected funding timeline for goals and emergency fund based on current monthly surplus. |
| `POST /goals` (201) | `{ "name": str, "target_amount": int, "current_amount"?: int, "target_date"?: str, "priority"?: int }` | `Goal` | Creates a new goal. Priority defaults to the end of the queue. |
| `PATCH /goals/{id}` | Any subset of `POST /goals` fields | `Goal` | Updates goal details or progress. `404 goal_not_found`. |

`GoalProjection` = `{ "id": int \| null, "name": str, "target_amount": int, "current_amount": int, "target_date": str \| null, "priority": int, "remaining": int, "months_needed": int \| null, "projected_date": str \| null, "on_track": bool, "required_monthly": int \| null }`.

### B2. Planner and What-If (`/plan`, `/whatif`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `GET /plan` | None | `{ "profile": Profile, "variable": { "Category": int }, "surplus": int, "projections": [GoalProjection] }` | Returns current spending baseline and sequential goal projections. |
| `POST /whatif` | `{ "kind": "category_pct" \| "category_abs" \| "fixed_abs" \| "income_abs", "category"?: str, "pct"?: float, "name"?: str, "delta"?: int }` | `{ "surplus_before": int, "surplus_after": int, "surplus_delta": int, "before": [GoalProjection], "after": [GoalProjection + months_saved] }` | Simulates financial adjustments and computes months saved/delayed per goal. `422 unknown_category`, `422 validation_error`. |

### B3. Nudges and Reports (`/nudges`, `/reports`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `GET /nudges` | None | `[Nudge]` | Returns active spending drift nudges. Generates/refreshes drift alerts when category spend exceeds trailing average by ≥ 20%. |
| `POST /nudges/{id}/dismiss` | None | `Nudge` | Dismisses a nudge so it is not shown again this month. `404 nudge_not_found`. |
| `GET /reports/{month}` | Query `format=json\|html` (`YYYY-MM`) | JSON report object or standalone HTML document | Comprehensive monthly review: income, spent, saved, savings rate %, spend by category comparison, subscriptions, goal status, nudges. `422 bad_month`. |

### B4. Voice Layer (`/voice`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `POST /voice/token` | `{ "client_id"?: str }` | `{ "access_token": str, "expires_in": int, "ws_url": str }` | Issues a short-lived Wispr Flow WebSocket token without exposing API keys to the browser. Returns `503` if unconfigured. |
| `POST /voice/command` | `{ "text": str }` | `{ "log_id": int, "transcript": str, "blocked": bool, "reply": str \| null, "intents": [Intent] }` | Parses text or transcribed speech into structured intents (regex first, validated Gemini fallback). Read-only intents execute immediately; write intents remain pending confirmation. |
| `POST /voice/confirm` | `{ "log_id": int, "accept": bool }` | `{ "confirmed": bool, "results": [ExecutionResult] }` | Executes or cancels staged intents. `404 log_not_found`, `409 already_resolved`. |

Intent types: `LOG_EXPENSE`, `CORRECT_CATEGORY`, `SET_PROFILE`, `SET_GOAL`, `WHAT_IF`, `ASK_STATUS`, `UNKNOWN`.

### B5. Coach (`/coach`)
| Method + Path | Request Body | Response | Description |
|---|---|---|---|
| `POST /coach/ask` | `{ "question": str }` | `{ "answer": str, "blocked": bool }` | Plain-language finance coaching. Guardrails block securities/investment queries and return an educational disclaimer. Every reply terminates with disclaimer. |

---

## 3. Cross-Module Contracts
1. **Category Names**: Standard title casing is used across all modules (`"Food"`, `"Groceries"`, `"Transport"`, `"Shopping"`, `"Entertainment"`, `"Bills"`, `"Health"`, `"Education"`, `"Travel"`, `"Transfers"`, `"ATM"`, `"Other"`).
2. **Correction Loop**: When Person B executes `CORRECT_CATEGORY` via voice confirm, it invokes Person A's `PATCH /transactions/{id}` or updates `Transaction.category` and generates a `Rule`.
3. **Database Access**: Person A writes transactions and rules; Person B reads transactions and recurring tables to compute surplus and detect drift. Confirmed `LOG_EXPENSE` commands create a transaction with `source = "voice"`.
