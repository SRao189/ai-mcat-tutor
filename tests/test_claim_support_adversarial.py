"""Adversarial Gate 3 coverage (contradiction-safety).

Ports the four Codex bypass probes and adds the repair-required cases:
dimensional units, numeric completeness, equation relationships, worked-example
final answers, conditional dilution. Governing rule: a single matching token
must never let a contradiction or unsupported assertion slip through as `pass`.

Run: python tests/test_claim_support_adversarial.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import claim_support as cs  # noqa: E402

SRC_ENERGY = "The standard free energy change is 30 kj/mol."


def ev(claim, passage, **kw):
    return cs.evaluate_claim(claim, passage, **kw)


# ---- the four ported Codex probes ------------------------------------------
def test_codex_unit_prefix_mismatch_not_auto_passed():
    r = ev("The concentration is 30 mM.", "The concentration is 30 M.")
    assert r["status"] == "fail", r


def test_codex_reversed_equation_not_auto_passed():
    r = ev("ΔG = TΔS - ΔH gibbs free energy", "Equation: ΔG = ΔH - TΔS.",
           kind="equation", expression="ΔG = TΔS - ΔH")
    assert r["status"] == "fail", r


def test_codex_extra_wrong_number_not_auto_passed():
    r = ev("The standard free energy change is 30 kj/mol and 50 kj/mol.",
           SRC_ENERGY)
    assert r["status"] == "fail", r


def test_codex_wrong_worked_answer_not_auto_passed():
    r = ev("compute", "A worked example gives delta G = 6.", kind="worked",
           steps=["delta G = 10 - 4 = 6"], answer="5")
    assert r["status"] == "fail", r


# ---- dimensional unit normalization battery --------------------------------
def test_units_30M_vs_30mM_fail():
    assert ev("c is 30 M", "c is 30 mM")["status"] == "fail"


def test_units_60s_vs_1min_equivalent_pass():
    assert ev("t is 60 s", "t is 1 min")["status"] == "pass"


def test_units_1000J_vs_1kJ_equivalent_pass():
    assert ev("e is 1000 J", "e is 1 kJ")["status"] == "pass"


def test_units_30kJmol_vs_30Jmol_fail():
    assert ev("x is 30 kj/mol", "x is 30 j/mol")["status"] == "fail"


def test_seconds_minutes_mismatch_fail():
    assert ev("t is 30 s", "t is 30 min")["status"] == "fail"


# ---- numeric completeness ---------------------------------------------------
def test_matching_number_does_not_mask_extra():
    # 30 matches, 50 does not -> must not pass
    assert ev("values are 30 kj/mol and 50 kj/mol", SRC_ENERGY)["status"] != "pass"


def test_supported_single_quantity_passes():
    assert ev("the change is 30 kj/mol", SRC_ENERGY)["status"] == "pass"


# ---- equation relationships -------------------------------------------------
EQ_SRC = "Gibbs: ΔG = ΔH - TΔS."


def test_equation_reversed_rhs_fails():
    assert ev("ΔG = TΔS - ΔH", EQ_SRC, kind="equation",
              expression="ΔG = TΔS - ΔH")["status"] == "fail"


def test_equation_algebraically_equivalent_passes():
    assert ev("ΔH = ΔG + TΔS", EQ_SRC, kind="equation",
              expression="ΔH = ΔG + TΔS")["status"] == "pass"


def test_equation_ratio_reversed_fails():
    assert ev("x = b/a", "Definition: x = a/b.", kind="equation",
              expression="x = b/a")["status"] == "fail"


def test_equation_unparseable_is_ambiguous():
    r = ev("y = sin(a)^2 + log(b)", "y relates a and b somehow.",
           kind="equation", expression="y = sin(a)^2 + log(b)")
    assert r["status"] == "ambiguous" and r["auditorRequired"] is True


# ---- worked-example final answer -------------------------------------------
def test_worked_final_answer_mismatch_fails():
    r = ev("q", "src", kind="worked", steps=["10 - 4 = 6"], answer="5")
    assert r["status"] == "fail"


def test_worked_final_answer_match_passes():
    r = ev("q", "src", kind="worked", steps=["10 - 4 = 6"], answer="6")
    assert r["status"] == "pass"


def test_worked_unparseable_is_ambiguous():
    r = ev("q", "src", kind="worked", steps=["reason qualitatively"], answer="x")
    assert r["status"] == "ambiguous"


# ---- conditional dilution (padding must not bypass) -------------------------
COND_SRC = "A reaction is spontaneous when delta G is negative."


def test_conditional_diluted_restatement_not_passed():
    # universal claim padded with topic words to dodge a containment threshold
    claim = ("A spontaneous reaction always proceeds; thermodynamics entropy "
             "enthalpy gibbs free energy bioenergetics discussion padding text")
    r = ev(claim, COND_SRC)
    assert r["status"] != "pass", r


def test_conditional_strengthened_to_universal_not_passed():
    # objective 5 allows fail OR ambiguous; we route to ambiguous (never pass)
    r = ev("a reaction is always spontaneous", COND_SRC)
    assert r["status"] != "pass" and r["auditorRequired"] is True


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
