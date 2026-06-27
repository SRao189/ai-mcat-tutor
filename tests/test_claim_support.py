"""Unit + adversarial tests for Gate 3 deterministic claim support.

Run: python tests/test_claim_support.py   (from worktree root)
No network, no models, no subprocess.
"""
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import claim_support as cs  # noqa: E402
import citations  # noqa: E402

PASSAGE = (
    "A reaction is spontaneous when delta G is negative. Entropy increases in a "
    "spontaneous process. The standard free energy change is 30 kj/mol.")


def ev(claim, passage=PASSAGE, **kw):
    return cs.evaluate_claim(claim, passage, **kw)


# ---- low-level extractor checks --------------------------------------------
def test_number_and_unit_extraction():
    assert cs.numbers("delta G is 30 kj/mol and -2.5") == {30.0, -2.5}
    assert cs.units("30 kj/mol") == {"kj/mol"}
    assert cs.units("the temperature") == set()  # no stray-letter units


def test_equation_symbols():
    syms = cs.equation_symbols("ΔG = ΔH − TΔS")
    assert "delta g" in syms and "delta h" in syms and "delta s" in syms


# ---- adversarial: must FAIL -------------------------------------------------
def test_reversed_sign_fails():
    r = ev("delta G is positive for a spontaneous reaction")
    assert r["status"] == "fail" and any("sign" in x for x in r["failureReasons"])


def test_reversed_direction_fails():
    r = ev("entropy decreases in a spontaneous process")
    assert r["status"] == "fail"
    assert any("direction" in x for x in r["failureReasons"])


def test_wrong_number_fails():
    r = ev("the standard free energy change is 50 kj/mol")
    assert r["status"] == "fail"
    assert any("number-mismatch" in x for x in r["failureReasons"])


def test_wrong_unit_fails():
    r = ev("the standard free energy change is 30 kcal/mol")
    assert r["status"] == "fail"
    assert any("unit-mismatch" in x for x in r["failureReasons"])


def test_unsupported_absolute_language_fails():
    r = ev("a reaction is always spontaneous")
    assert r["status"] == "fail"
    assert any("conditional-vs-absolute" in x for x in r["failureReasons"])


def test_negation_flip_is_ambiguous_not_fail():
    # negation is scope-blind, so a polarity flip is routed to the auditor
    # (ambiguous), never a hard deterministic fail
    r = ev("a reaction is not spontaneous when delta G is negative")
    assert r["status"] == "ambiguous" and r["auditorRequired"] is True
    assert any("negation" in x for x in r["failureReasons"])


def test_bad_arithmetic_fails():
    r = ev("compute work", kind="worked",
           steps=["delta G = 10 - 4 = 5", "done"])
    assert r["status"] == "fail"
    assert any("arithmetic" in x for x in r["failureReasons"])


def test_answer_explanation_inconsistent_fails():
    r = cs.evaluate_claim(
        "delta G negative spontaneous", PASSAGE, kind="question",
        answer="delta G is negative", explanation="delta G is positive here")
    assert r["status"] == "fail"
    assert any("answer-explanation" in x for x in r["failureReasons"])


# ---- adversarial: must PASS or be AMBIGUOUS (never falsely fail) ------------
def test_correct_paraphrase_passes():
    r = ev("When delta G is negative, the reaction proceeds spontaneously")
    assert r["status"] == "pass", r


def test_correct_equation_passes():
    r = ev("ΔG = ΔH − TΔS gibbs free energy", kind="equation",
           expression="ΔG = ΔH − TΔS")
    assert r["status"] == "pass", r


def test_correct_number_passes():
    r = ev("the standard free energy change is 30 kj/mol")
    assert r["status"] == "pass", r


def test_good_arithmetic_passes():
    r = ev("compute", kind="worked", steps=["delta G = 10 - 4 = 6"])
    assert r["status"] == "pass", r


def test_ambiguous_prose_not_false_failed():
    r = ev("This concept is foundational to understanding bioenergetics broadly")
    assert r["status"] == "ambiguous" and r["auditorRequired"] is True


def test_offtopic_reversed_sign_is_not_fail():
    # 'positive' about an unrelated topic must not trip the sign check
    r = ev("a positive attitude helps test takers")
    assert r["status"] != "fail"


# ---- module-level: gather, reuse, claimsVerified ---------------------------
def _wiki(tmp):
    (tmp / "wiki").mkdir()
    (tmp / "wiki" / "t.md").write_text(
        "# T\n\n## Free Energy\n\n" + PASSAGE + "\n", encoding="utf-8")
    return citations.make_citation(tmp, "wiki/t.md#free-energy",
                                   "A reaction is spontaneous when delta G is negative")


def test_module_all_pass_is_verified():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _wiki(tmp)
        module = {"sections": [{"id": "s", "title": "S",
                  "content": "When delta G is negative the reaction is spontaneous",
                  "sourceRefs": [cite]}]}
        out = cs.evaluate_module(module, tmp)
        assert out["claimsVerified"] is True
        assert out["claimPassCount"] == 1 and out["claimFailCount"] == 0


def test_module_with_fail_not_verified():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _wiki(tmp)
        module = {"sections": [{"id": "s", "title": "S",
                  "content": "delta G is positive for a spontaneous reaction",
                  "sourceRefs": [cite]}]}
        out = cs.evaluate_module(module, tmp)
        assert out["claimsVerified"] is False and out["claimFailCount"] == 1


def test_module_unresolvable_citation_skipped():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        module = {"sections": [{"id": "s", "title": "S", "content": "x",
                  "sourceRefs": ["wiki/legacy.md"]}]}
        out = cs.evaluate_module(module, tmp)
        assert out["claimSkippedCount"] == 1 and out["claimsVerified"] is False


def test_excessive_citation_reuse_forces_auditor():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _wiki(tmp)
        # 5 identical-citation passing claims -> reuse threshold tripped
        secs = [{"id": f"s{i}", "title": "S",
                 "content": "When delta G is negative the reaction is spontaneous",
                 "sourceRefs": [cite]} for i in range(5)]
        out = cs.evaluate_module({"sections": secs}, tmp)
        assert any("citation-reuse" in r["checks"] for r in out["claimResults"])
        assert all(r["auditorRequired"] for r in out["claimResults"])


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
