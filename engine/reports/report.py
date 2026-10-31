"""Monthly review report (Person B): JSON dict + simple HTML."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from html import escape

from dateutil.relativedelta import relativedelta

from engine.planner.planner import avg_monthly_by_category, emergency_goal, monthly_surplus, project_goals

FOOTER = "Educational modelling only, not financial advice."


def _spend(txns: list[dict], year: int, month: int) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for t in txns:
        if t["direction"] == "debit" and (t["date"].year, t["date"].month) == (year, month):
            out[t["category"]] += t["amount"]
    return dict(out)


_PER_MONTH = {"weekly": 52 / 12, "monthly": 1, "yearly": 1 / 12}


def subscription_rows(recurring: list[dict]) -> list[dict]:
    """Active/changed/unused subscriptions with their cost normalised to a month (whole rupees)."""
    return [
        {**{k: r[k] for k in ("merchant", "amount", "cadence", "status")},
         "monthly_cost": round(r["amount"] * _PER_MONTH.get(r["cadence"], 1))}
        for r in recurring if r["status"] != "cancelled"
    ]


def monthly_report(txns: list[dict], month: str, profile: dict, goals: list[dict], nudges: list[dict] | None = None,
                   recurring: list[dict] | None = None) -> dict:
    """month = 'YYYY-MM'. Goal dates use the same surplus model as the planner."""
    y, m = map(int, month.split("-"))
    first = date(y, m, 1)
    prev = first - relativedelta(months=1)
    cur, last = _spend(txns, y, m), _spend(txns, prev.year, prev.month)
    total, prev_total = sum(cur.values()), sum(last.values())
    income = profile["monthly_income"]
    usual = avg_monthly_by_category(txns, first, exclude=profile["fixed_costs"])
    surplus = monthly_surplus(income, profile["fixed_costs"], usual)
    eg = emergency_goal(profile, goals)
    subs = subscription_rows(recurring or [])
    return {
        "month": month,
        "income": income,
        "total_spent": total,
        "saved": income - total,
        "savings_rate_pct": round((income - total) / income * 100) if income else 0,
        "vs_last_month": total - prev_total,
        "by_category": sorted(
            ({"category": c, "spent": v, "last_month": last.get(c, 0), "change": v - last.get(c, 0)} for c, v in cur.items()),
            key=lambda r: -r["spent"],
        ),
        "goals": project_goals(([eg] if eg else []) + goals, surplus, first),
        "subscriptions": subs,
        "subscriptions_monthly_total": sum(s["monthly_cost"] for s in subs),
        "nudges": nudges or [],
        "footer": FOOTER,
    }


def render_html(r: dict) -> str:
    rows = "".join(
        f"<tr><td>{escape(c['category'])}</td><td>₹{c['spent']:,}</td><td>{c['change']:+,}</td></tr>" for c in r["by_category"]
    )
    goals = "".join(
        f"<li>{escape(g['name'])}: {g['projected_date'] or 'not reachable at current surplus'}"
        f"{' (on track)' if g['on_track'] else ''}</li>" for g in r["goals"]
    )
    nudges = "".join(f"<li>{escape(n['message'])}</li>" for n in r["nudges"])
    subs = "".join(
        f"<li>{escape(s['merchant'])}: ₹{s['amount']:,} {escape(s['cadence'])}"
        f"{'' if s['status'] == 'active' else ' (' + escape(s['status']) + ')'}</li>" for s in r["subscriptions"]
    )
    return (
        f"<h1>Monthly review {escape(r['month'])}</h1>"
        f"<p>Income ₹{r['income']:,} · Spent ₹{r['total_spent']:,} · Savings rate {r['savings_rate_pct']}% "
        f"· vs last month {r['vs_last_month']:+,}</p>"
        f"<table><tr><th>Category</th><th>Spent</th><th>Change</th></tr>{rows}</table>"
        f"<h2>Subscriptions (₹{r['subscriptions_monthly_total']:,}/month)</h2><ul>{subs}</ul>"
        f"<h2>Goals</h2><ul>{goals}</ul><h2>Nudges</h2><ul>{nudges}</ul><p><small>{FOOTER}</small></p>"
    )


def render_page(r: dict) -> str:
    """Standalone HTML document for GET /reports/{month}?format=html."""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Monthly review {escape(r['month'])}</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:.4rem;text-align:left}</style>"
        f"</head><body>{render_html(r)}</body></html>"
    )
