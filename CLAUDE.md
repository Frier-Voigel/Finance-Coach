# CLAUDE.md — AI assistant instructions

## Project
Finance Coach: a personal finance companion (FastAPI + React). See SPEC.md for the full specification and PLAN.md for the build plan.

## Stack
- **Backend**: Python 3.11+, FastAPI, SQLModel (SQLite), Pydantic, google-generativeai, httpx
- **Frontend**: React 18, Vite, Tailwind CSS 3, Recharts, react-router-dom v6
- **Voice**: Wispr Flow WebSocket API (optional; text fallback always available)

## Architecture
- Router → Service → Store (SqlStore wraps SQLModel Session)
- Pure logic modules (planner.py, nudges.py, report.py) take/return dicts — no DB dependency
- API errors: `ApiError(status, code, message)` → `{"error": code, "message": message}`
- Dependency injection: `get_store` (session → SqlStore), `get_today` (optional `?as_of` query param)

## Conventions
- Money: whole rupees (int), never float
- Dates: ISO 8601 strings in JSON; `datetime.date` in Python
- Category names: title case ("Food", "Dining Out")
- Every GET/POST that depends on "today" accepts `?as_of=YYYY-MM-DD` for demo/synthetic data
- Error shape everywhere: `{"error": "<code>", "message": "<human text>"}`

## Folder ownership
- Person A: `/ingest`, `/engine/categorize`, `/engine/recurring`
- Person B: `/engine/planner`, `/engine/nudges`, `/engine/reports`, `/coach`, `/voice`
- Shared: `/shared`, `/api` (merge conflicts only in router mounting and frontend routes)

## Testing
- `python -m pytest -q` from root
- `pytest.ini` sets `pythonpath = .`
- Tests use fakes (in-memory SQLite, no network)

## Do NOT
- Give securities or investment advice in any generated text
- Use floats for money
- Edit another person's folder without a PR to `/shared`
