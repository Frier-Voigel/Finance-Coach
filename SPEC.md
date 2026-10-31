# SPEC.md — Finance Coach Specification

## 1. Overview
Finance Coach is a browser-based personal finance companion for Indian users. It ingests bank statements (CSV, PDF, SMS), auto-categorises transactions, detects recurring subscriptions, projects savings goals, and provides a voice/text coaching interface — all without giving securities advice.

## 2. Data ingestion (Person A)
- **CSV parser**: auto-map columns (date, description, debit/credit/amount, balance); handle multiple Indian date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD).
- **SMS parser**: regex-first extraction of amount, merchant, date from Indian bank SMS patterns; LLM fallback for unmatched formats.
- **PDF parser**: pdfplumber table extraction with LLM fallback for messy layouts.
- **Normaliser**: strip UPI IDs, reference numbers, trailing digits from merchant names; deduplicate across sources.

## 3. Categorisation (Person A)
- Rule engine: pattern types `merchant`, `contains`, `regex` → category.
- LLM fallback with caching (Gemini).
- Default categories: Food, Groceries, Transport, Shopping, Entertainment, Bills, Health, Education, Travel, Transfers, ATM, Other.
- User corrections create rules and retroactively re-categorise non-user-set transactions.

## 4. Recurring detection (Person A)
- Identify subscriptions by merchant frequency + amount stability.
- Cadences: weekly, monthly, yearly.
- Alerts: price change, unused (no recent usage after subscription charge), cancelled.

## 5. Planner and what-if (Person B)
- Profile: monthly income, fixed costs (name→amount map), emergency fund current/target.
- Goals: name, target amount, current saved, optional target date, priority.
- Surplus = income − fixed costs − average variable spend (3-month trailing).
- Goals funded sequentially by priority; emergency fund is implicit priority-0 goal.
- What-if scenarios: category percentage cut, category absolute change, fixed-cost delta, income delta → before/after projections with months saved.

## 6. Voice layer (Person B) — mandated component
- **Wispr Flow** integration: POST /voice/token returns a short-lived access token (org key stays server-side); browser opens a WebSocket to Wispr, streams 16 kHz PCM via AudioWorklet.
- **Intent router**: regex-first, validated LLM fallback. Intent types: LOG_EXPENSE, CORRECT_CATEGORY, SET_PROFILE, SET_GOAL, WHAT_IF, ASK_STATUS, UNKNOWN.
- **Confirmation**: POST /voice/command parses but writes nothing; POST /voice/confirm executes write intents.
- **Text fallback**: same endpoints, always available.

## 7. Data model (SQLModel tables)

| Table | Key columns |
|-------|------------|
| `transactions` | id, date, amount (int ₹), direction (debit/credit), description, merchant, category, category_source (rule/llm/user), source (csv/pdf/sms/voice), raw_text, account |
| `rules` | id, pattern, match_type (contains/regex/merchant), category, created_from_txn_id, created_at |
| `recurring` | id, merchant, amount, cadence (weekly/monthly/yearly), last_seen, next_expected, status (active/changed/unused/cancelled) |
| `profile` | id, monthly_income, fixed_costs_json, emergency_fund_current, emergency_fund_target, updated_at |
| `goals` | id, name, target_amount, current_amount, target_date, priority |
| `nudges` | id, created_at, type, message, severity (high/medium/low), dismissed |
| `reports` | id, month (YYYY-MM), json_payload, generated_at |
| `voice_log` | id, created_at, transcript, intent_json, confirmed, result |

Money is stored as whole rupees (int). Dates are ISO 8601.

## 8. Guardrails and coach (Person B)
- Rule-based blocklist catches securities/investment questions (stocks, crypto, mutual funds, SIP, etc.).
- Blocked queries receive an educational redirect, never securities advice.
- Coach explainer wraps planner output in plain language via Gemini; post-check rejects hallucinated numbers.
- Every response ends with "Educational modelling only, not financial advice."

## 9. Nudges (Person B)
- Drift detection: if category spend this month > trailing 3-month average by ≥ 20%, generate a nudge.
- Severity: ≥ 50% → high, else medium.
- One nudge per category per month; dismissed nudges are not recreated.

## 10. Demo script
1. Upload a CSV → transactions appear categorised.
2. Correct a category via inline edit → "rule learned" toast, past transactions updated.
3. Show subscriptions page with a price-change alert.
4. Set profile (income, fixed costs, emergency fund target).
5. Add two goals → see projections.
6. What-if: "cut dining out by 30%" → see months saved.
7. Voice: "Log 500 rupees for lunch" → confirm → transaction appears.
8. Voice: "Change category of Swiggy to Dining" → confirm → rule created.
9. Monthly report with chart.
10. Ask coach a securities question → educational redirect.
