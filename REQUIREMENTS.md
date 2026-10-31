# REQUIREMENTS.md — Hackathon Requirements

## Mandatory components
1. **Data ingestion**: Parse at least CSV bank statements; SMS and PDF are stretch goals.
2. **Auto-categorisation**: Rule engine with LLM fallback; user corrections create rules.
3. **Financial planner**: Profile, goals, surplus calculation, what-if scenarios.
4. **Voice interface**: Use Wispr Flow for speech-to-text; text fallback required.
5. **Guardrails**: Never give securities/investment advice; educational redirect only.
6. **Recurring detection**: Identify subscriptions, alert on price changes and unused services.

## Technical requirements
- Backend: Python + FastAPI
- Frontend: React (any bundler)
- Database: SQLite (via SQLModel/SQLAlchemy)
- LLM: Google Gemini API
- Voice: Wispr Flow API (with text fallback)

## Deliverables
- Working demo covering the SPEC section 10 demo script
- Source code in a Git repository
- README with run instructions for PowerShell and bash

## Evaluation criteria
- Functional completeness of the demo script
- Code quality and test coverage
- Voice integration quality (or graceful text fallback)
- Guardrail effectiveness
- UI polish and usability
