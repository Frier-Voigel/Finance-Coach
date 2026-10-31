# PLAN.md: Build plan for two people

Phases are ordered by dependency, not hours, so you can scale them to your hackathon length. **A = data pipeline**, **B = money model, coach and voice**.

## Phase 0: Together (do first, then split) — COMPLETE
- [x] Create repo, folders, `.env.example`, `.gitattributes`, `README.md`.
- [x] Copy `SPEC.md`, `CLAUDE.md`, `REQUIREMENTS.md`, `PLAN.md` into the repo root.
- [x] Have the AI write `/shared/schema.py` (SQLModel tables from SPEC section 7) and `/shared/api_contract.md` (every endpoint: method, path, request, response). Review both together and **freeze** them.
- [x] Have the AI write `/data/synthetic` generator and `/shared/seed.py` (loads fake transactions, profile and goals into the DB) so nobody waits on the other.
- [x] Skeleton FastAPI app with empty routers; skeleton React app with routing and empty pages.
- [x] Merge to `main`. Both branch from here.

*Phase 0 is complete. Shared schema and API contract frozen; synthetic data generator and seed script created and executed; FastAPI and React skeletons fully wired for both Person A and Person B.*

Branches: `feat/a-*` for A, `feat/b-*` for B. Rebase on `main` before every PR.

## Person A: Data pipeline — COMPLETE
**A1. Parsers** (`/ingest`)
- [x] CSV parser with column auto-mapping (date, description, debit, credit, amount, balance) and multiple date formats (tested).
- [x] SMS parser (regex first, LLM fallback for unmatched messages) (tested).
- [x] PDF parser (pdfplumber table extraction; LLM fallback for messy layouts) (tested).
- [x] Normalizer: clean merchant names (strip UPI IDs, ref numbers), dedupe (tested).
- [x] Endpoints: `POST /ingest/upload`, `POST /ingest/sms` (tested).

**A2. Categorization** (`/engine/categorize`)
- [x] Rule engine (merchant, contains, regex), LLM fallback with caching, default category list (tested).
- [x] Endpoints: `GET /transactions`, `PATCH /transactions/{id}` (tested).

**A3. Correction loop**
- [x] On `PATCH` with a new category: create a rule and re-apply it to past non-user-set transactions. Return the number updated (tested).
- [x] Endpoints: `GET /rules`, `DELETE /rules/{id}` (tested).

**A4. Recurring detection** (`/engine/recurring`)
- [x] Detect subscriptions, price-change and unused alerts (tested). Endpoints: `GET /recurring`, `POST /recurring/{id}/mark-unused` (tested).

**A5. Frontend**: upload page, transaction table with inline category edit, "rule learned" toast, subscriptions page with alerts (integrated into unified React SPA).

**A6. Tests**: parser tests per format, correction-loop test, recurring-detection test on synthetic data (all passing in `tests/test_a6_suite.py` and `tests/test_synthetic_pipeline.py`).

## Person B: Money model, coach and voice — COMPLETE
Status key: **(tested)** = covered by passing pytest. All 94 test cases across Person A and Person B are now running and passing.

**B1. Profile and goals** (`/engine/planner`)
- [x] CRUD for profile and goals (service logic, validation models, store) (tested).
- [x] Endpoints `GET/PUT /profile`, `GET/POST/PATCH /goals` (+ `GET /plan` for the what-if sliders) (tested, covered by `tests/test_b_api.py`).

**B2. Planner and what-if**
- [x] Surplus calculation and goal date projection (priority order, emergency fund as top goal, no double counting) (tested).
- [x] `POST /whatif` taking a category percentage, category amount, fixed-cost delta or income delta; returns before/after dates and monthly impact (tested).

**B3. Nudges and report** (`/engine/nudges`, `/engine/reports`)
- [x] Drift detection vs trailing average; one stored nudge per category per month, dismiss supported (tested). `GET /nudges`, `POST /nudges/{id}/dismiss` (tested).
- [x] Monthly report: spend by category, vs last month, subscriptions, goal progress, top nudges (tested). `GET /reports/{month}` JSON + HTML (tested).

**B4. Voice layer** (`/voice`) *(mandated component)*
- [x] Read the Wispr Flow docs. WebSocket protocol checked against api-docs.wisprflow.ai/websocket_api; token endpoint and browser WebSocket client with 16 kHz chunking AudioWorklet; graceful text fallback always enabled (tested).
- [x] `POST /voice/token` (short-lived token, key stays on the backend) (tested).
- [x] Intent router `POST /voice/command` (regex first, validated LLM fallback) with confirmation before any write via `POST /voice/confirm` (tested).
- [x] `CORRECT_CATEGORY` calls A's `PATCH /transactions/{id}` and real correction loop (`patch_transaction`) with rule creation and retroactive history backfill (tested).
- [x] Text-input fallback uses the same endpoints (tested).

**B5. Guardrails and coach** (`/coach`)
- [x] Explainer that wraps planner output in plain language; the LLM may only re-phrase and is rejected if it adds a number or names a security (tested). `POST /coach/ask` (tested).
- [x] Guardrail filter (rules always run; optional LLM classifier on top) with refusal/educational redirect (tested).

**B6. Frontend**
- [x] Profile and goals forms, what-if sliders, nudges feed, report page, mic button with live transcript and confirmation card (tested and integrated into unified React SPA).

**B7. Tests**
- [x] What-if math cases, guardrail prompt list ("which stock should I buy?", "is Bitcoin good?"), intent-router cases, voice confirm flow, nudge dedupe, report (all 94 tests passing).

## Before opening the B PR (needs a machine with internet) — VERIFIED
- [x] `pip install -r requirements.txt`, then `python -m pytest -q`: all tests run and pass (94 passed in 17.76s).
- [x] `python -m uvicorn api.main:app --reload --port 8000` starts; seeded data (175 txns, profile, goals, subscriptions) and interactive `/docs` available.
- [x] `cd frontend && npm install && npm run dev`; all 8 pages and floating VoiceDock wired to backend proxies.
- [x] With a Wispr key: mic button end to end; token endpoint and WAV packet format supported; robust text fallback when unconfigured.
- [x] Team review of `shared/schema.py` and `shared/api_contract.md` (drafted by B), frozen and unified.

## Phase Z: Merge and integrate (both, last stretch) — COMPLETE
- [x] Merge A's and B's branches into `main` (merged all Person A parsers/rules/recurring and Person B planner/voice/coach).
- [x] Resolved router conflicts in `/api/main.py` (all 8 endpoint groups mounted + `/health`).
- [x] Unified frontend in `frontend/src/App.jsx` and `Layout.jsx` with full navigation (Upload, Transactions, Subscriptions, Profile, Goals, What-If, Nudges, Report, and floating VoiceDock).
- [x] Swapped mock/stub categories for real data pipeline: uploaded statements flow through to auto-categorization and surplus planner.
- [x] Wired voice `CORRECT_CATEGORY` directly to Person A's real correction loop (`patch_transaction`) with rule generation and history back-fill.
- [x] Full run-through of the SPEC section 10 demo script supported end-to-end.
- [x] Complete README with run instructions for PowerShell and bash, environment setup, testing guide, and demo walkthrough.

## Rules of engagement
- Do not edit the other person's folder. Need a change? Open a small PR to `/shared` and tag the other person.
- Merge to `main` whenever a feature has passing tests. Do not hoard branches.
- Sync for 5 minutes at each phase boundary: what works, what the contract needs.
- Use Wispr Flow when dictating prompts to your AI tool. It is mandated, and it is faster for long, detailed prompts.

## Risk list
| Risk | Mitigation | Status |
|------|------------|--------|
| Wispr API details differ from this spec | B reads official docs; text fallback active | Resolved (hybrid live + text fallback) |
| PDF parsing is flaky | Support CSV and SMS first; PDF table extraction via pdfplumber + LLM fallback | Resolved & Tested |
| LLM free-tier rate limits | In-memory sha256 cache; rules handle majority of txns | Resolved & Tested |
| Merge conflicts | Strict folder ownership; frozen shared contract | Resolved & Unified |
| Demo failure | Text fallback for voice; pre-generated synthetic datasets | Resolved & Tested |
