# Finance Coach (Integrated — Person A + Person B)

A living personal money companion that parses bank statements (CSV, SMS, PDF), auto-categorises transactions with rule learning and LLM fallback, detects subscriptions and price changes, models goal projections with what-if scenarios, nudges on overspending drift, and provides an interactive Wispr voice / coach assistant with securities guardrails.

---

## 1. Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm**
- **Google Gemini API Key** (for LLM categorization & explainer)
- *(Optional)* **Wispr Flow API Key** (text fallback works out-of-the-box)

### Step 1: Backend Setup

```powershell
# PowerShell (Windows)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure environment variables
Copy-Item .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here

# Generate synthetic fixtures & seed database
python -m data.synthetic.generate
python shared/seed.py

# Launch FastAPI backend server
python -m uvicorn api.main:app --reload --port 8000
```

```bash
# Bash (Linux / macOS)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here

python3 -m data.synthetic.generate
python3 shared/seed.py

python3 -m uvicorn api.main:app --reload --port 8000
```

Interactive Swagger API Documentation: <http://localhost:8000/docs>

---

### Step 2: Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open application in your browser: <http://localhost:5173>

> **Tip**: Set `VITE_AS_OF=2026-10-15` in `frontend/.env` to anchor the current date to the 6-month synthetic evaluation window.

---

## 2. Integrated Architecture

```
finance-coach/
├── api/
│   ├── main.py              # Root FastAPI app: mounts all A & B routers + /health
│   ├── db.py                # Database engine & session dependency
│   ├── deps.py              # Shared FastAPI dependencies (SqlStore, ?as_of)
│   └── errors.py            # Canonical error handler {"error": code, "message": text}
├── ingest/                  # [Person A] Statement parsers & normalizer
│   ├── csv_parser.py        # 3 CSV layouts with column auto-mapping & multiple date formats
│   ├── sms_parser.py        # Indian bank SMS alert parser (regex + Gemini fallback)
│   ├── pdf_parser.py        # PDF table extraction (pdfplumber)
│   ├── normalizer.py        # UPI / POS / ECOM / NEFT merchant cleaner & deduplication
│   ├── service.py           # Ingestion orchestrator
│   └── router.py            # POST /ingest/upload, POST /ingest/sms
├── engine/
│   ├── categorize/          # [Person A] Categorization engine & correction loop
│   │   ├── rules.py         # Pattern matcher (merchant, contains, regex) + LLM fallback
│   │   ├── service.py       # A3 correction loop (creates rule, back-fills past transactions)
│   │   └── router.py        # GET /transactions, PATCH /transactions/{id}, GET/DELETE /rules
│   ├── recurring/           # [Person A] Subscription & recurring payment detector
│   │   ├── detector.py      # Cadence detector, price change alert (>5%), unused alerts
│   │   └── router.py        # GET /recurring, POST /recurring/{hash}/mark-unused
│   ├── planner/             # [Person B] Living money model & what-if planner
│   │   ├── planner.py       # Surplus math & sequential goal projections
│   │   ├── service.py       # Profile & goal CRUD, what-if simulator
│   │   ├── store.py         # Data access layer (SqlStore)
│   │   └── router.py        # GET/PUT /profile, GET/POST/PATCH /goals, GET /plan, POST /whatif
│   ├── nudges/              # [Person B] Overspending drift detector
│   │   ├── nudges.py        # Drift calculation vs trailing 3-month average (>=20%)
│   │   ├── service.py       # One nudge per category per month, dismissals
│   │   └── router.py        # GET /nudges, POST /nudges/{id}/dismiss
│   └── reports/             # [Person B] Monthly financial review
│       ├── report.py        # JSON report payload & savings rate metrics
│       ├── service.py       # Report builder & printable HTML renderer
│       └── router.py        # GET /reports/{month}?format=json|html
├── coach/                   # [Person B] AI finance coach with securities guardrails
│   ├── guardrails.py        # Rule blocklist: stops stock/crypto advice, educational redirect
│   ├── explain.py           # Plain-language plan explainer (prevents hallucinated numbers)
│   ├── gemini.py            # Gemini client wrapper
│   └── router.py            # POST /coach/ask
├── voice/                   # [Person B] Voice interface with Wispr Flow & text fallback
│   ├── wispr.py             # Short-lived token issuer (org key stays server-side)
│   ├── intent.py            # Regex-first command parser (LOG_EXPENSE, CORRECT_CATEGORY, etc.)
│   ├── llm_intent.py        # Validated Gemini intent parser fallback
│   ├── service.py           # Two-phase confirmation router (wired to A's correction loop)
│   └── router.py            # POST /voice/token, POST /voice/command, POST /voice/confirm
├── shared/                  # Cross-cutting frozen contracts & database schema
│   ├── schema.py            # SQLModel tables (Transaction, Rule, Recurring, Profile, Goal, Nudge, Report, VoiceLog)
│   ├── db.py                # Database connection factory (SQLite)
│   ├── llm.py               # Shared Gemini completion with sha256 in-memory caching
│   ├── seed.py              # Database seeder
│   └── api_contract.md      # Frozen contract for all endpoints
├── data/synthetic/          # Synthetic test datasets
│   ├── files/               # Realistic test files: bank1 (CSV), bank2 (CSV), bank3 (CSV), statement (PDF), sms.txt
│   ├── generate.py          # Generator for 6 months of banking ledger & fixtures
│   └── output/              # generated fixtures (git-ignored; created by `python -m shared.seed`)
└── frontend/                # Unified React 18 + Vite + Tailwind CSS SPA
    └── src/
        ├── App.jsx          # Route definitions & top-level layout
        ├── components/      # Shared layout, toasts, navigation
        └── features/        # Upload, Review, Subscriptions, Profile, Goals, What-If, Nudges, Report, VoiceDock
```

---

## 3. How to Test the Project

### Running Backend Unit & Integration Tests

Run the complete test suite (both Person A and Person B test suites):

```bash
# Run all tests
python -m pytest -v

# Run Person A pipeline tests (Ingest, Categorization, Correction Loop, Recurring)
python -m pytest tests/test_a6_suite.py -v

# Run Person B financial model & voice tests
python -m pytest tests/test_b_engine.py tests/test_b_services.py tests/test_b_voice_guard.py tests/test_b_api.py -v

# Run synthetic data determinism tests
python -m pytest tests/test_phase0_data.py -v
```

---

## 4. End-to-End Demo Script Walkthrough (SPEC Section 10)

Follow this step-by-step walkthrough in the web UI (<http://localhost:5173>):

1. **Step 1: Ingest Bank Statements**
   - Navigate to the **Upload** page.
   - Click "Choose File" and upload `data/synthetic/files/bank1_apr_may.csv` (or use the one-click synthetic sample button).
   - Notice the Ingestion Summary card confirming parsed transactions, skipping duplicates.
   - Also paste SMS alerts from `data/synthetic/files/sms_sep.txt` into the SMS box and submit.

2. **Step 2: Review Transactions & Test Rule Learning (A3 Correction Loop)**
   - Navigate to **Transactions**.
   - Find a transaction (e.g. `Swiggy` currently tagged as `Food` or `Uncategorised`).
   - Use the inline dropdown to change its category to `Dining`.
   - Notice the **"Rule learned" toast** appearing:
     `Rule learned: "SWIGGY" → "Dining". Updated X historical transaction(s).`
   - All past Swiggy transactions update automatically to `Dining`.
   - Click the "Learned Rules" button to view and manage active rules.

3. **Step 3: Subscriptions & Price-Change Alerts**
   - Navigate to **Subscriptions**.
   - Notice detected subscriptions:
     - **Netflix**: Flagged with **Price Changed** alert (September price increase from ₹649 to ₹799).
     - **Spotify**: Active monthly subscription (₹119/mo).
     - **GymFit**: Click **Mark as Unused** to flag the unused gym membership for cancellation.

4. **Step 4: Configure Living Money Profile**
   - Navigate to **Profile**.
   - Set Monthly Income: `₹75,000`.
   - Add fixed costs: `rent` (₹18,000), `insurance` (₹2,500), `bike emi` (₹4,500).
   - Set Emergency Fund: Saved `₹50,000`, Target `₹250,000`.
   - Click "Save Profile".

5. **Step 5: Goals & Surplus Projections**
   - Navigate to **Goals**.
   - See the monthly surplus calculated automatically after accounting for fixed and trailing variable expenses.
   - Add a Goal: `Japan Trip`, Target: `₹180,000`, Saved: `₹40,000`, Target Date: `2027-10-01`.
   - See sequential funding timeline, months needed, and "on track" indicator.

6. **Step 6: What-If Simulator**
   - Navigate to **What-If**.
   - Select Scenario: "Spending in a category (%)".
   - Select `Dining` and slide the adjustment to `-30%`.
   - Instantly see:
     - Monthly surplus increase (e.g. `+₹1,800`).
     - Months saved on each goal (e.g. hitting the Japan Trip 2 months earlier).

7. **Step 7: Overspending Nudges & Monthly Review**
   - Navigate to **Nudges**:
     - See drift alerts flagged whenever spending in a category deviates by ≥20% from the trailing average.
     - Dismiss any reviewed nudge.
   - Navigate to **Report**:
     - View interactive Recharts category spend comparison vs previous month.
     - Click "Open printable HTML" for a standalone printer-friendly report.

8. **Step 8: Voice Commands & Confirmation Flow**
   - Use the persistent **Voice** bar at the bottom:
   - **Log an Expense**: Type or speak `"Log 500 rupees for lunch"` → see confirmation card with details → Click **Confirm** → Transaction is created.
   - **Voice Category Correction**: Type or speak `"Change category of Swiggy to Dining"` → Click **Confirm** → Calls Person A's real correction loop and learns the rule.
   - **What-If via Voice**: Type or speak `"What if I cut dining out by 30%?"` → Coach answers with projected savings.

9. **Step 9: Securities Guardrails Test**
   - In the voice bar or coach prompt, type:
     `"Which stock should I buy?"` or `"Is Bitcoin good to invest in?"`
   - Verify that the guardrail activates immediately and returns the educational redirect:
     `"I'm a budgeting and savings coach — I can't give advice on specific securities or investments... Educational modelling only, not financial advice."`

---

## 5. Environment Variables Reference

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./coach.db` | SQLModel database location |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key for fallback categorization, plain-language explainer, and voice intents |
| `WISPR_API_KEY` | *(empty)* | Wispr Flow API key for browser WebSocket streaming (text fallback active when absent) |
| `WISPR_API_URL` | `https://platform-api.wisprflow.ai/api/v1/dash` | Wispr platform endpoint |
| `CORS_ORIGIN` | `http://localhost:5173` | Allowed frontend origin for CORS |
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL for frontend |
| `VITE_AS_OF` | `2026-10-15` | Simulated date for deterministic synthetic evaluation |

---

## 6. License & Disclaimer

Educational modeling project. **Not financial advice.**
