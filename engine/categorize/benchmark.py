"""Measure categorisation accuracy: rules only, rules + Gemini, and after the user corrects N merchants.

    python -m engine.categorize.benchmark          # rules only + corrections
    python -m engine.categorize.benchmark --llm    # also asks Gemini (needs GEMINI_API_KEY)
"""
from __future__ import annotations

import sys
from typing import Callable

from engine.categorize.rules import categorize
from shared.schema import Rule

Row = tuple[str, str, str]  # merchant, description, true category
CORRECTIONS = (1, 3, 5, 10)


def _predict(rows: list[Row], rules: list[Rule], llm) -> list[tuple[str, str]]:
    return [categorize(m, d, rules, llm) for m, d, _ in rows]


def _accuracy(rows: list[Row], preds: list[tuple[str, str]]) -> float:
    return round(100 * sum(p[0] == r[2] for p, r in zip(preds, rows)) / len(rows), 1)


def _correct(rows: list[Row], llm, n: int) -> list[Rule]:
    """The user fixes the first n wrong merchants they see; each fix becomes a rule, as in patch_transaction."""
    rules: list[Rule] = []
    for (m, _, truth), (cat, _) in zip(rows, _predict(rows, [], llm)):
        if len(rules) == n:
            break
        if cat != truth and not any(r.pattern == m for r in rules):
            rules.append(Rule(pattern=m, match_type="merchant", category=truth))
    return rules


def run_benchmark(rows: list[Row], llm: Callable[[str], str] | None = None) -> dict:
    """Accuracy (%) at each stage. `llm` is optional; without it the Gemini stages are left out."""
    base = _predict(rows, [], None)
    stages = [{"stage": "Rules only", "accuracy": _accuracy(rows, base)}]
    start = None
    if llm:
        preds = _predict(rows, [], llm)
        answered = sum(src == "llm" for _, src in preds)
        stages.append({"stage": "Rules + Gemini", "accuracy": _accuracy(rows, preds), "ai_answered": answered})
        start = llm
    label = "+ Gemini" if llm else "rules only"
    for n in CORRECTIONS:
        rules = _correct(rows, start, n)
        stages.append({"stage": f"After {n} correction{'s' * (n > 1)} ({label})", "accuracy": _accuracy(rows, _predict(rows, rules, start))})
    return {"total": len(rows), "stages": stages}


def _llm() -> Callable[[str], str] | None:
    import os
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    from shared.llm import complete
    return complete


def main(argv: list[str]) -> None:
    from data.synthetic.truth import build_rows
    rows = build_rows()
    llm = _llm() if "--llm" in argv else None
    if "--llm" in argv and llm is None:
        print("GEMINI_API_KEY is not set, so the Gemini stages are skipped.\n")
    print(f"{len(rows)} labelled synthetic transactions\n\n| Stage | Accuracy |\n|---|---|")
    for s in run_benchmark(rows, llm)["stages"]:
        print(f"| {s['stage']} | {s['accuracy']}% |")


if __name__ == "__main__":
    main(sys.argv[1:])
