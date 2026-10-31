# Finance Coach

A personal finance companion that parses bank statements (CSV, SMS, PDF), auto-categorises transactions, detects subscriptions, models goal projections with what-if scenarios, nudges on overspending, and offers a voice/text coach — all in the browser.

## Quick start

### Backend (Python 3.11+)

```powershell
# PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # fill in GEMINI_API_KEY (required) and WISPR_API_KEY (optional)
python shared/seed.py          # load synthetic data
python -m uvicorn api.main:app --reload --port 8000
```

```bash
# bash / macOS / Linux
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python shared/seed.py
uvicorn api.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>

### Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Set `VITE_AS_OF=2026-10-15` in `frontend/.env` to lock the date to the synthetic data window.

## Project structure

```
api/            FastAPI app, DB engine, shared deps, error handler
shared/         SQLModel schema, API contract, seed script
data/synthetic/ Fake transactions, SMS messages (generated)
ingest/         Person A — parsers (CSV, SMS, PDF), normaliser
engine/
  categorize/   Person A — rule engine + LLM fallback
  recurring/    Person A — subscription detector
  planner/      Person B — profile, goals, surplus, what-if
  nudges/       Person B — drift detection
  reports/      Person B — monthly report (JSON + HTML)
coach/          Person B — guardrails + Gemini explainer
voice/          Person B — Wispr Flow integration, intent router
frontend/       Vite + React 18 + Tailwind + Recharts
tests/          pytest suite
```

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | No (default: `sqlite:///./coach.db`) | SQLModel database URL |
| `GEMINI_API_KEY` | Yes | Google Gemini API key for LLM features |
| `WISPR_API_KEY` | No | Wispr Flow API key (text fallback if missing) |
| `WISPR_API_URL` | No | Wispr platform URL override |
| `CORS_ORIGIN` | No (default: `http://localhost:5173`) | Frontend origin for CORS |

## Tests

```bash
python -m pytest -q
```

## Ownership

- **Person A**: `/ingest`, `/engine/categorize`, `/engine/recurring`, upload/review/subscriptions frontend pages
- **Person B**: `/engine/planner`, `/engine/nudges`, `/engine/reports`, `/coach`, `/voice`, profile/goals/whatif/nudges/report/voice frontend
- **Shared**: `/shared` (schema, contract, seed), `/api` (app skeleton)

## License

Educational project — not financial advice.
