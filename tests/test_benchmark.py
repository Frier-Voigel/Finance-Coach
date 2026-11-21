"""The accuracy benchmark: corrections must help, and the Gemini stage must be reported only when an LLM is supplied."""
from data.synthetic.truth import KNOWN, UNSEEN, build_rows
from engine.categorize.benchmark import run_benchmark
from engine.categorize.rules import _llm_cache


def test_corrections_improve_accuracy_and_llm_stage_is_optional():
    rows = build_rows()
    stages = run_benchmark(rows)["stages"]
    accs = [s["accuracy"] for s in stages]
    assert stages[0]["stage"] == "Rules only" and "Gemini" not in " ".join(s["stage"] for s in stages)
    assert accs == sorted(accs) and accs[-1] > accs[0] + 20  # each correction can only help


def test_llm_stage_counts_answers():
    _llm_cache.clear()
    truth = {**KNOWN, **UNSEEN}
    fake = lambda prompt: truth.get(prompt.split("Merchant: ")[1].split("\n")[0], "Other")  # noqa: E731 - stands in for Gemini
    out = run_benchmark(build_rows(), fake)["stages"]
    assert out[1]["stage"] == "Rules + Gemini" and out[1]["ai_answered"] > 0 and out[1]["accuracy"] > out[0]["accuracy"]
