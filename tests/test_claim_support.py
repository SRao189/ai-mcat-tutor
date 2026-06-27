"""Unit tests for the Gate 3 deterministic claim-support engine.

Run: python tests/test_claim_support.py
Contradiction-safe semantics: pass requires >=1 supported concrete assertion and
no contradiction; pure prose and unsupported tokens are ambiguous, not pass.
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
EQ_PASSAGE = "Gibbs free energy: delta G equals delta H minus T delta S."


def ev(claim, passage=PASSAGE, **kw):
    return cs.evaluate_claim(claim, passage, **kw)


# ---- extractors -------------------------------------------------------------
def test_number_and_quantity_extraction():
    assert cs.all_numbers("delta G is 30 and -2.5") == {30.0, -2.5}
    q = cs.parse_quantities("30 kj/mol")
    assert q and q[0][0] == "molar_energy" and q[0][1] == 30000.0


def test_equation_symbols_helper():
    syms = cs.equation_symbols("ΔG = ΔH − TΔS")
    assert "delta g" in syms and "delta s" in syms


# ---- contradictions must FAIL ----------------------------------------------
def test_reversed_sign_fails():
    assert ev("delta G is positive for a spontaneous reaction")["status"] == "fail"


def test_reversed_direction_fails():
    assert ev("entropy decreases in a spontaneous process")["status"] == "fail"


def test_wrong_number_fails():
    assert ev("the standard free energy change is 50 kj/mol")["status"] == "fail"


def test_in_family_unit_mismatch_fails():
    assert ev("x is 30 kj/mol", "x is 30 j/mol")["status"] == "fail"


def test_unsupported_absolute_language_not_passed():
    # universalizing a conditional source is soft -> ambiguous (never pass)
    r = ev("a reaction is always spontaneous")
    assert r["status"] == "ambiguous" and r["auditorRequired"] is True


def test_bad_arithmetic_fails():
    r = ev("compute", kind="worked", steps=["delta G = 10 - 4 = 5", "done"])
    assert r["status"] == "fail"


def test_answer_explanation_inconsistent_fails():
    r = cs.evaluate_claim(
        "delta G negative", PASSAGE, kind="question",
        answer="delta G is negative", explanation="delta G is positive here")
    assert r["status"] == "fail"


# ---- supported concrete assertions PASS ------------------------------------
def test_supported_quantity_passes():
    assert ev("the standard free energy change is 30 kj/mol")["status"] == "pass"


def test_correct_equation_passes():
    r = ev("ΔG = ΔH − TΔS gibbs free energy", EQ_PASSAGE, kind="equation",
           expression="ΔG = ΔH − TΔS")
    assert r["status"] == "pass", r


def test_good_arithmetic_passes():
    assert ev("compute", kind="worked",
              steps=["delta G = 10 - 4 = 6"])["status"] == "pass"


# ---- uncertainty -> AMBIGUOUS (never false pass / false fail) --------------
def test_correct_paraphrase_prose_is_ambiguous():
    # no concrete assertion to confirm -> auditor, not an automatic pass
    r = ev("When delta G is negative, the reaction proceeds spontaneously")
    assert r["status"] == "ambiguous" and r["auditorRequired"] is True


def test_negation_flip_is_ambiguous_not_fail():
    r = ev("a reaction is not spontaneous when delta G is negative")
    assert r["status"] == "ambiguous" and r["auditorRequired"] is True
    assert any("negation" in x for x in r["failureReasons"])


def test_unsupported_extra_number_is_not_pass():
    r = ev("the change is 30 kj/mol and there are 7 magic units")
    assert r["status"] != "pass"  # 7 unsupported


def test_pure_prose_is_ambiguous():
    assert ev("This concept is foundational to bioenergetics")["status"] == "ambiguous"


def test_offtopic_not_false_failed():
    assert ev("a positive attitude helps test takers")["status"] != "fail"


# ---- module orchestration ---------------------------------------------------
def _wiki(tmp):
    (tmp / "wiki").mkdir()
    (tmp / "wiki" / "t.md").write_text(
        "# T\n\n## Free Energy\n\nA reaction is spontaneous when delta G is "
        "negative. The standard free energy change is 30 kj/mol.\n",
        encoding="utf-8")
    return citations.make_citation(
        tmp, "wiki/t.md#free-energy",
        "A reaction is spontaneous when delta G is negative")


def _section(content, cite):
    return {"id": "s", "title": "S", "content": content, "sourceRefs": [cite]}


def test_module_all_pass_is_verified():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _wiki(tmp)
        out = cs.evaluate_module(
            {"sections": [_section("The change is 30 kj/mol", cite)]}, tmp)
        assert out["claimsVerified"] is True and out["claimPassCount"] == 1


def test_module_with_fail_not_verified():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _wiki(tmp)
        out = cs.evaluate_module(
            {"sections": [_section(
                "delta G is positive for a spontaneous reaction", cite)]}, tmp)
        assert out["claimsVerified"] is False and out["claimFailCount"] == 1


def test_module_unresolvable_citation_skipped():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        out = cs.evaluate_module(
            {"sections": [{"id": "s", "title": "S", "content": "x",
                           "sourceRefs": ["wiki/legacy.md"]}]}, tmp)
        assert out["claimSkippedCount"] == 1 and out["claimsVerified"] is False


def test_citation_reuse_is_metadata_not_downgrade():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _wiki(tmp)
        secs = [_section("The change is 30 kj/mol", cite) for _ in range(5)]
        out = cs.evaluate_module({"sections": secs}, tmp)
        # reuse recorded but valid claims stay pass (not forced to auditor)
        assert out["claimPassCount"] == 5 and out["claimsVerified"] is True
        assert any("citation-reuse" in str(r["checks"])
                   for r in out["claimResults"])


def test_source_dependency_hash_changes_with_source():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _wiki(tmp)
        module = {"sections": [_section("The change is 30 kj/mol", cite)]}
        h1 = cs.source_dependency_hash(module, tmp)
        (tmp / "wiki" / "t.md").write_text(
            "# T\n\n## Free Energy\n\nEdited content entirely.\n", encoding="utf-8")
        h2 = cs.source_dependency_hash(module, tmp)
        assert h1 != h2 and h1.startswith("sha256:")


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
