"""Cheap regression tests for the deterministic pipeline logic.

Run: cd benchmarks/production-pilot && python -m tests.test_pipeline
No network, no models. Each fix made because real chapters exposed a failure
should leave one assert here.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import core, render, source  # noqa: E402

SRC = """3.1 THERMODYNAMICS
Thermodynamics is the study of the energetics of chemical reactions. Gibbs free
energy is defined as delta G equals delta H minus T delta S. A reaction is
spontaneous when delta G is negative. Entropy is disorder.
"""


def test_normalize_strips_boilerplate_keeps_headings():
    raw = ("MCAT BIOCHEMISTRY REVIEW\n3.1 THERMODYNAMICS\n"
           "40 | For More Free Content, visit PrincetonReview.com\n"
           "Real   content here.\n| 61\n")
    out = source.normalize_raw(raw)
    assert "MCAT BIOCHEMISTRY REVIEW" not in out
    assert "For More Free Content" not in out
    assert "3.1 THERMODYNAMICS" in out          # heading preserved
    assert "Real content here." in out          # internal whitespace collapsed
    assert "| 61" not in out


def test_extract_section_bounds():
    text = "3.1 THERMODYNAMICS\nbody a\nbody b\n3.2 KINETICS\nother\n"
    got = source.extract_section(text, r"^3\.1 THERMODYNAMICS", r"^3\.2 KINETICS")
    assert "body a" in got and "body b" in got and "other" not in got


def _base(section_ids):
    return {
        "id": "m", "title": "M", "objectives": ["o"],
        "sections": [{"id": s, "title": s, "content": "C", "sourceRefs": ["r"]}
                     for s in section_ids],
        "equations": [], "workedExamples": [], "checks": [],
        "practiceQuestions": [{"question": "What is entropy?", "answer": "disorder",
                               "explanation": "Entropy is disorder.", "sourceRefs": ["r"],
                               "reviewTarget": section_ids[0]}],
        "sourceRefs": ["r"], "sourceGaps": [],
    }


def test_merge_additive_and_rejects_bad_id():
    base = _base(["core"])
    grounded = "Gibbs free energy spontaneous reaction entropy disorder"
    good = core.apply_patch(base, {"section_updates": [
        {"section_id": "core", "append_text": grounded}],
        "practice_question_additions": [], "reason": "x"}, SRC)
    assert good["applied_updates"] == 1 and not good["rejected"]
    assert base["sections"][0]["content"] == "C"        # original untouched
    bad = core.apply_patch(base, {"section_updates": [
        {"section_id": "practiceQuestions", "append_text": grounded}],
        "practice_question_additions": [], "reason": "x"}, SRC)
    assert bad["applied_updates"] == 0 and bad["rejected"]


def test_safe_no_op_when_everything_rejected():
    base = _base(["core"])
    res = core.apply_patch(base, {"section_updates": [
        {"section_id": "nope", "append_text": "x"}],
        "practice_question_additions": [], "reason": "x"}, SRC)
    assert res["safe_no_op"] is True


def test_rejects_ungrounded_addition():
    base = _base(["core"])
    res = core.apply_patch(base, {"section_updates": [
        {"section_id": "core",
         "append_text": "Mitochondria photosynthesis chlorophyll ribosome telomere."}],
        "practice_question_additions": [], "reason": "x"}, SRC)
    assert res["applied_updates"] == 0
    assert any(r["reason"] == "ungrounded_section_update" for r in res["rejected"])


def test_rejects_near_duplicate_question():
    base = _base(["core"])
    res = core.apply_patch(base, {"section_updates": [],
        "practice_question_additions": [{
            "question": "What is entropy?", "answer": "disorder of the universe",
            "explanation": "Entropy is disorder spontaneous reaction.",
            "sourceRefs": ["r"], "reviewTarget": "core"}],
        "reason": "x"}, SRC)
    assert res["added_questions"] == 0
    assert any(r["reason"] == "duplicate_question" for r in res["rejected"])


def test_sanitize_strips_qa_sections_and_fabricated_worked():
    # Reproduces the real Gemma chapter-03 failures: assessment items duplicated
    # into sections[], and a worked example with invented "hypothetical" data.
    candidate = {
        "id": "m", "title": "M", "objectives": ["o"],
        "sections": [
            {"id": "intro", "title": "Introduction", "content": "Thermo is the study of energy.",
             "sourceRefs": ["r"]},
            {"id": "assessment-check-1", "title": "Check 1: Laws",
             "content": "Question: X?\nAnswer: Y\nExplanation: Z\nReviewTarget: intro",
             "sourceRefs": ["r"]},
            {"id": "practice", "title": "Practice Questions",
             "content": "(A) a (B) b\nAnswer: (B)\nReviewTarget: intro", "sourceRefs": ["r"]},
        ],
        "equations": [],
        "workedExamples": [
            {"question": "Consider a hypothetical reaction with made-up data...",
             "steps": ["s"], "answer": "42", "sourceRefs": ["r"]},
            {"question": "Using the source's stated value, compute X.",
             "steps": ["s"], "answer": "ok", "sourceRefs": ["r"]},
        ],
        "checks": [], "practiceQuestions": [], "sourceRefs": ["r"], "sourceGaps": [],
    }
    clean, rep = core.sanitize_candidate(candidate)
    ids = [s["id"] for s in clean["sections"]]
    assert ids == ["intro"]                       # only lesson prose remains
    assert "assessment-check-1" in rep["removed_sections"]
    assert len(clean["workedExamples"]) == 1       # fabricated one dropped
    assert clean["workedExamples"][0]["answer"] == "ok"
    assert len(rep["dropped_worked"]) == 1
    assert any("SOURCE GAP" in g for g in clean["sourceGaps"])


def _q(question, answer="a", explanation="e", target="core"):
    return {"question": question, "answer": answer, "explanation": explanation,
            "sourceRefs": ["r"], "reviewTarget": target}


# Tiny thermo source for grounding-based quality checks. Mentions Gibbs energy,
# enthalpy, entropy, spontaneity -- but NOT concentrations.
QSRC = ("Gibbs free energy delta G equals delta H minus T delta S. A reaction is "
        "spontaneous when delta G is negative. Enthalpy is heat. Entropy is disorder. "
        "At equilibrium the forward and reverse reaction rates are equal.")


def test_quality_drops_ungrounded_worked_example():  # failure #2
    cand = _base(["core"])
    cand["workedExamples"] = [
        {"question": "Burn CO with H2O to form glucose at 500 kelvin pressure 3 atm",
         "steps": ["s"], "answer": "12.5 kilojoules", "sourceRefs": ["r"]},
        {"question": "Given delta H and delta S, find delta G spontaneous",
         "steps": ["s"], "answer": "delta G negative", "sourceRefs": ["r"]},
    ]
    clean, rep = core.quality_filter(cand, QSRC)
    assert len(clean["workedExamples"]) == 1
    assert clean["workedExamples"][0]["answer"] == "delta G negative"
    assert rep["ungrounded_worked"] and any("SOURCE GAP" in g for g in clean["sourceGaps"])


def test_quality_strong_grounding_beats_word_overlap():  # failure #6
    # Every WORD is in the source, but the number 42.7 is fabricated -> must drop,
    # proving hard-token grounding overrides broad bag-of-words overlap.
    cand = _base(["core"])
    cand["workedExamples"] = [{
        "question": "Gibbs free energy delta G equals delta H minus T delta S",
        "steps": ["spontaneous when delta G is negative"],
        "answer": "delta G is 42.7", "sourceRefs": ["r"]}]
    clean, rep = core.quality_filter(cand, QSRC)
    assert clean["workedExamples"] == [] and rep["ungrounded_worked"]


def test_quality_documents_missing_worked_example():  # ch4 false-quarantine fix
    cand = _base(["a", "b"])
    cand["objectives"] = ["Explain why a reaction is spontaneous when delta G is negative",
                          "Describe enthalpy heat and entropy disorder"]
    cand["workedExamples"] = []
    cand["checks"] = [_q("q1 delta G"), _q("q2 entropy"), _q("q3 enthalpy")]
    cand["practiceQuestions"] = []
    cand["sourceGaps"] = []
    clean, _ = core.quality_filter(cand, QSRC)
    assert any("worked" in g.lower() and "example" in g.lower() and "SOURCE GAP" in g
               for g in clean["sourceGaps"])
    # the worked-example floor is now satisfied via the documented gap
    assert "worked example" not in " ".join(core.meets_minimums(clean)[1]).lower()


def test_meets_minimums():  # failure #5
    ok = _base(["a", "b"])
    ok["objectives"] = ["o1 grounded", "o2 grounded"]
    ok["practiceQuestions"] = [_q("q1"), _q("q2"), _q("q3")]
    ok["sourceGaps"] = ["SOURCE GAP: none"]
    assert core.meets_minimums(ok)[0] is True
    thin = _base(["a"])                       # 1 section, 1 question, no worked/gap
    good, reasons = core.meets_minimums(thin)
    assert good is False and len(reasons) >= 2


def test_quality_drops_sign_contradiction():  # failure #3
    cand = _base(["core"])
    cand["practiceQuestions"] = [_q(
        "A reaction has positive delta H and negative delta S. Is it spontaneous?",
        answer="Never spontaneous",
        explanation="With positive delta H and positive delta S it is nonspontaneous.")]
    clean, rep = core.quality_filter(cand, QSRC)
    assert clean["practiceQuestions"] == []
    assert rep["sign_contradictions"]


def test_quality_keeps_consistent_signs():  # guard against #3 false positives
    cand = _base(["core"])
    cand["practiceQuestions"] = [_q(
        "When is a reaction spontaneous?",
        explanation="delta G is negative when delta S is positive and delta H is negative.")]
    clean, _ = core.quality_filter(cand, QSRC)
    assert len(clean["practiceQuestions"]) == 1


def test_quality_drops_equilibrium_equal_concentration():  # failure #4
    cand = _base(["core"])
    cand["practiceQuestions"] = [_q(
        "What happens at equilibrium?",
        explanation="Equal forward and reverse rates mean the concentrations are "
                    "equal at equilibrium.")]
    clean, rep = core.quality_filter(cand, QSRC)
    assert clean["practiceQuestions"] == []
    assert rep["equilibrium_equal"]


def test_quality_keeps_correct_equilibrium_statement():  # guard against #4 false positives
    cand = _base(["core"])
    cand["practiceQuestions"] = [_q(
        "What is true at equilibrium?",
        explanation="At equilibrium concentrations are constant but not necessarily "
                    "equal; the forward and reverse rates are equal.")]
    clean, _ = core.quality_filter(cand, QSRC)
    assert len(clean["practiceQuestions"]) == 1


def test_quality_drops_overpromised_objective():  # failure #5
    cand = _base(["core"])
    cand["objectives"] = [
        "Explain why a reaction is spontaneous when delta G is negative",
        "Calculate delta G from reactant and product concentrations",  # not in source
    ]
    clean, rep = core.quality_filter(cand, QSRC)
    assert len(clean["objectives"]) == 1
    assert rep["ungrounded_objectives"]


def test_quality_dedupes_candidate_questions():  # failure #6
    cand = _base(["core"])
    cand["checks"] = [_q("What does it mean that delta G is negative spontaneous?")]
    cand["practiceQuestions"] = [
        _q("What does a negative delta G mean for spontaneous reactions?"),  # near-dup
        _q("What is enthalpy delta H heat in a reaction?")]
    clean, rep = core.quality_filter(cand, QSRC)
    total = len(clean["checks"]) + len(clean["practiceQuestions"])
    assert total == 2 and rep["duplicate_questions"]


def test_enforce_source_refs_normalizes_missing_and_stale_refs():
    cand = _base(["core"])
    cand["sections"][0]["sourceRefs"] = ["raw/Chapter 3.txt#old-slug"]
    del cand["practiceQuestions"][0]["sourceRefs"]
    clean, rep = core.enforce_source_refs(cand, "raw/Chapter 3.txt#3.1")
    assert clean["sections"][0]["sourceRefs"] == ["raw/Chapter 3.txt#3.1"]
    assert clean["practiceQuestions"][0]["sourceRefs"] == ["raw/Chapter 3.txt#3.1"]
    assert clean["sourceRefs"] == ["raw/Chapter 3.txt#3.1"]
    assert rep["disallowed"] and rep["missing"] and len(rep["normalized"]) == 2


def test_enforce_source_refs_uses_subsection_packet_refs():
    from pipeline import chapter
    sub = chapter._prefix_and_tag({
        "objectives": ["o"], "sections": [
            {"id": "s", "title": "T", "content": "c", "sourceRefs": ["raw/Chapter 3.txt#3.2"]}],
        "equations": [], "workedExamples": [], "checks": [_q("q", target="s")],
        "practiceQuestions": [], "sourceRefs": ["raw/Chapter 3.txt#3.2"], "sourceGaps": []},
        "3.1")
    clean, rep = core.enforce_source_refs(
        sub, "raw/Chapter 3.txt#chapter-3",
        {"3.1": "raw/Chapter 3.txt#3.1", "3.2": "raw/Chapter 3.txt#3.2"})
    assert clean["sections"][0]["sourceRefs"] == ["raw/Chapter 3.txt#3.1"]
    assert clean["checks"][0]["sourceRefs"] == ["raw/Chapter 3.txt#3.1"]
    assert clean["sourceRefs"] == ["raw/Chapter 3.txt#3.1"]
    assert len(rep["normalized"]) == 2


def test_render_uses_final_session_only():  # failure #7
    # The renderer is a pure function of the session object it is handed; nothing
    # else (no stale candidate) can leak into the preview.
    a = _base(["core"]); a["title"] = "Alpha"
    b = _base(["core"]); b["title"] = "Beta"
    doc_a, doc_b = render.render_session_html(a), render.render_session_html(b)
    assert "Alpha" in doc_a and "Beta" not in doc_a
    assert "Beta" in doc_b and "Alpha" not in doc_b


def test_component_schemas_bound_output():  # max generated-output limits
    assert core.lesson_schema()["properties"]["objectives"]["maxItems"] == 4
    assert core.lesson_schema()["properties"]["sections"]["maxItems"] == 4
    assert core.eqworked_schema()["properties"]["workedExamples"]["maxItems"] == 2
    a = core.assessment_schema(["s1"])
    assert a["properties"]["checks"]["maxItems"] == 3
    assert a["properties"]["practiceQuestions"]["maxItems"] == 3
    # reviewTarget is constrained to the supplied section ids
    assert a["properties"]["checks"]["items"]["properties"]["reviewTarget"]["enum"] == ["s1"]


def test_merge_components_assembles_and_dedupes_ids():  # component merge + dup ids
    a = {"id": "m", "title": "T", "objectives": ["o1", "o2"], "sections": [
        {"id": "s1", "title": "S1", "content": "c", "sourceRefs": ["r1"]},
        {"id": "s1", "title": "dup", "content": "c2", "sourceRefs": ["r1"]},  # dup id
        {"id": "s2", "title": "S2", "content": "c", "sourceRefs": ["r2"]}]}
    b = {"equations": [{"expression": "e", "meaning": "m", "sourceRefs": ["r3"]}],
         "workedExamples": []}
    c = {"checks": [_q("q1", target="s1")], "practiceQuestions": [_q("q2", target="s2")]}
    s = core.merge_components({"lesson": a, "eqworked": b, "assessment": c}, "raw/x#sec")
    assert [x["id"] for x in s["sections"]] == ["s1", "s2"]      # duplicate id dropped
    assert s["objectives"] == ["o1", "o2"]
    assert len(s["checks"]) == 1 and len(s["practiceQuestions"]) == 1
    assert "r1" in s["sourceRefs"] and "r3" in s["sourceRefs"]


def test_merge_components_missing_component_raises():  # missing component quarantine
    try:
        core.merge_components({"lesson": {}, "eqworked": {}}, "x")  # assessment missing
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "assessment" in str(exc)


def test_component_cache_reused_without_model_call():  # checkpoint reuse
    import tempfile
    from pipeline import run, adapter
    cache = Path(tempfile.mkdtemp()) / "component-lesson.json"
    cache.write_text(json.dumps({"id": "m", "sections": []}), encoding="utf-8")
    orig = adapter.generate_structured

    def boom(*a, **k):
        raise AssertionError("model must not be called when a valid cache exists")

    adapter.generate_structured = boom
    try:
        data, meta = run._gen_component("model", "p", {}, "lbl", 100, cache)
    finally:
        adapter.generate_structured = orig
    assert data["id"] == "m" and meta == {}


def test_html_preview_is_offline_and_renders():
    session = _base(["core"])
    session["title"] = "Thermo Session"
    doc = render.render_session_html(session)
    assert "Thermo Session" in doc
    assert "http://" not in doc and "https://" not in doc
    assert "What is entropy?" in doc


def test_split_subsections_excludes_drills():  # chapter subsection detection
    norm = ("3.1 THERMODYNAMICS\nbody one\n3.2 KINETICS AND ENERGY\nbody two\n"
            "3.1 Drill\nq1\n3.2 Drill\nq2\n")
    subs = source.split_subsections(norm, 3)
    assert [s[0] for s in subs] == ["3.1", "3.2"]          # drills excluded
    assert subs[0][1] == "Thermodynamics" and "body one" in subs[0][2]
    assert "Drill" not in subs[1][2]                       # 3.2 stops before drills


def test_prefix_and_tag_prevents_id_collisions():  # cross-subsection id safety
    from pipeline import chapter
    mk = lambda: {"sections": [{"id": "intro", "title": "I", "content": "c", "sourceRefs": ["r"]}],
                  "equations": [], "workedExamples": [],
                  "checks": [_q("q", target="intro")], "practiceQuestions": []}
    a = chapter._prefix_and_tag(mk(), "3.1")
    b = chapter._prefix_and_tag(mk(), "3.2")
    assert a["sections"][0]["id"] == "3.1-intro" and b["sections"][0]["id"] == "3.2-intro"
    assert a["checks"][0]["reviewTarget"] == "3.1-intro"   # remapped to prefixed id
    assert a["sections"][0]["subsection"] == "3.1"


def test_quality_filter_no_cap_keeps_many_questions():  # chapter merge keeps >5
    cand = _base(["core"])
    cand["objectives"] = ["o grounded delta G spontaneous"]
    checks = ["Define gibbs free energy", "Explain spontaneous reactions",
              "Describe enthalpy changes", "Discuss entropy disorder",
              "Compare forward reverse rates", "Identify negative positive values"]
    practice = ["Summarize thermodynamics conservation laws", "Analyze temperature kelvin effects",
                "Predict reaction favorability outcomes", "Relate molecular kinetic potential"]
    cand["checks"] = [_q(t) for t in checks]
    cand["practiceQuestions"] = [_q(t) for t in practice]
    clean, _ = core.quality_filter(cand, QSRC, cap=False)
    assert len(clean["checks"]) + len(clean["practiceQuestions"]) == 10  # nothing trimmed
    capped, _ = core.quality_filter(cand, QSRC, cap=True)
    assert len(capped["checks"]) + len(capped["practiceQuestions"]) == 5   # cap trims


def test_assemble_chapter_orders_and_dedupes():  # chapter assembly
    from pipeline import chapter
    sub1 = chapter._prefix_and_tag({
        "objectives": ["shared obj"], "sections": [
            {"id": "s", "title": "T1", "content": "c1", "sourceRefs": ["r1"]}],
        "equations": [{"expression": "E=1", "meaning": "m", "sourceRefs": ["r1"]}],
        "workedExamples": [], "checks": [_q("c1", target="s")],
        "practiceQuestions": [], "sourceRefs": ["r1"], "sourceGaps": []}, "3.1")
    sub2 = chapter._prefix_and_tag({
        "objectives": ["shared obj"], "sections": [
            {"id": "s", "title": "T2", "content": "c2", "sourceRefs": ["r2"]}],
        "equations": [{"expression": "E = 1", "meaning": "m", "sourceRefs": ["r2"]}],
        "workedExamples": [], "checks": [_q("c2", target="s")],
        "practiceQuestions": [], "sourceRefs": ["r2"], "sourceGaps": []}, "3.2")
    cfg = {"id": "chapter-03", "chapter_title": "Chapter 3", "title": "x",
           "source_ref": "raw#c3"}
    s = chapter.assemble_chapter(cfg, [("3.1", "A", sub1, "ACCEPTED"),
                                       ("3.2", "B", sub2, "ACCEPTED")])
    assert [x["id"] for x in s["sections"]] == ["3.1-s", "3.2-s"]   # order preserved
    assert s["objectives"] == ["shared obj"]                       # deduped
    s["equations"] = chapter._dedup_equations(s["equations"])
    assert len(s["equations"]) == 1                                # whitespace-insensitive dedup


def test_chapter_render_offline_with_nav():  # one offline page, subsection nav
    session = {
        "id": "chapter-03", "title": "Chapter 3 - Biochemistry Basics",
        "objectives": ["Understand thermodynamics"],
        "sections": [{"id": "3.1-intro", "title": "Intro", "content": "Energy.",
                      "sourceRefs": ["r"], "subsection": "3.1"}],
        "equations": [], "workedExamples": [],
        "checks": [dict(_q("Check one?"), subsection="3.1")],
        "practiceQuestions": [dict(_q("Review one?"), subsection="3.1")],
        "sourceRefs": ["r"], "sourceGaps": ["SOURCE GAP: example"],
        "metadata": {"subsections": [{"id": "3.1", "title": "Thermodynamics",
                                      "status": "ACCEPTED"}]},
    }
    doc = render.render_chapter_html(session)
    assert "http://" not in doc and "https://" not in doc
    assert "Chapter 3 - Biochemistry Basics" in doc
    assert "Thermodynamics" in doc and "Cumulative Chapter Review" in doc
    assert "Check one?" in doc and "Review one?" in doc


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"ERROR {name}: {exc}")
    print(f"\n{'ALL PASS' if not failures else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
