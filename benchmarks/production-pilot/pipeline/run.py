"""Production-pilot orchestrator.

Drives raw chapter -> normalized source -> context packet -> Gemma session ->
Phi audit -> (justified) Qwen additive patch -> deterministic validation ->
offline HTML, with checkpoints, one retry per model stage, and per-chapter
quarantine. Restartable: completed stages with valid artifacts are skipped.

    python -m pipeline.run --config config/chapters.json [--chapters chapter-03]
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import adapter, core, render, source


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #
def gen_prompt(context_text: str) -> str:
    return f"""
You are generating one complete MCAT tutoring session as a single JSON object.

Your output is validated against the supplied JSON schema. Match it exactly,
include every required field, return only JSON (no code fences, no commentary).

Grounding rules:
- Use only information present in the context packet.
- Do not add outside factual knowledge, even if scientifically plausible.
- Where required material is missing from the packet, add a short entry to
  sourceGaps beginning with "SOURCE GAP" instead of inventing content.
- Every section, equation, worked example, and question needs a sourceRefs entry.

Tutoring-session requirements:
- 2 to 4 learning objectives.
- Plain-English explanations with key terms emphasized using **bold**.
- sections[] is ONLY explanatory lesson prose. Never put questions, multiple-
  choice options, "Answer:", "Explanation:", or "ReviewTarget:" lines inside a
  section. Every assessment item belongs in checks[] or practiceQuestions[].
- Equations only where the packet supports them.
- Only include a worked example that is actually worked out in the packet. Never
  invent a reaction, numbers, or data. If the packet has no worked example,
  leave workedExamples empty.
- 3 to 5 mixed assessment questions across checks + practiceQuestions, each with
  an answer, an explanation, and a reviewTarget naming a section id.
- Teach in an approachable Khan Academy-style voice; connect math to meaning.

CONTEXT PACKET START
{context_text}
CONTEXT PACKET END
""".strip()


def audit_prompt(context_text: str, candidate_json: str) -> str:
    return f"""
Act as an independent quality auditor for an MCAT tutoring session.

Audit rules:
- Treat the context packet as the only permitted factual source.
- Do not introduce outside facts.
- Identify claims absent from or conflicting with the packet.
- Check that source references genuinely support their sections.
- Check equation accuracy and that "equations" are truly equations.
- Evaluate conceptual progression, clarity, and completeness.
- Check whether assessments test material actually taught.
- Do not rewrite the session. Report only specific, actionable findings.

CONTEXT PACKET START
{context_text}
CONTEXT PACKET END

CANDIDATE SESSION START
{candidate_json}
CANDIDATE SESSION END
""".strip()


def patch_prompt(section_ids: list[str], context_text: str,
                 candidate_json: str, audit_json: str) -> str:
    return f"""
Create a small additive enrichment patch for an MCAT tutoring session.

Use only the supplied context packet as factual authority.

Allowed actions:
- Append one short clarification to an existing section.
- Add one or two application-level practice questions.

Forbidden actions:
- Do not rewrite the session or delete/replace existing content.
- Do not create new section IDs or use "practiceQuestions" as a section ID.
- Do not introduce outside facts or generic filler.
- Do not place SOURCE GAP in lesson prose.

Address the auditor's concrete concerns only when the packet supports the fix.

Valid section IDs:
{json.dumps(section_ids, indent=2)}

CONTEXT PACKET START
{context_text}
CONTEXT PACKET END

CURRENT SESSION START
{candidate_json}
CURRENT SESSION END

AUDIT START
{audit_json}
AUDIT END
""".strip()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def est_ctx(text: str, output_budget: int = 6000) -> int:
    """num_ctx must hold prompt + generated output. Sessions are large (~5k
    tokens), so reserve output_budget; undersizing truncates the JSON."""
    approx_tokens = len(text) // 3 + output_budget
    for size in (8192, 12288, 16384, 24576, 32768):
        if approx_tokens < size * 0.9:
            return size
    return 32768


def no_deletions(before: dict[str, Any], after: dict[str, Any]) -> bool:
    bs = {s["id"]: s.get("content", "") for s in before.get("sections", []) if s.get("id")}
    as_ = {s["id"]: s.get("content", "") for s in after.get("sections", []) if s.get("id")}
    if not set(bs).issubset(as_):
        return False
    for sid, content in bs.items():
        if content not in as_[sid]:  # original content must remain (append-only)
            return False
    return len(after.get("practiceQuestions", [])) >= len(before.get("practiceQuestions", []))


def synthetic_valid_module() -> dict[str, Any]:
    return {
        "id": "preflight", "title": "Preflight", "objectives": ["Check"],
        "sections": [{"id": "s1", "title": "S1", "content": "Body.",
                      "sourceRefs": ["ref"]}],
        "equations": [], "workedExamples": [],
        "checks": [], "practiceQuestions": [],
        "sourceRefs": ["ref"], "sourceGaps": [],
    }


def preflight(chapter: dict, out: Path, context_text: str, source_text: str,
              model: str, stage: str, section_ids: list[str] | None) -> bool:
    print(f"=== PREFLIGHT ({stage}) chapter={chapter['id']} ===")
    ok = True

    def check(label: str, passed: bool) -> None:
        nonlocal ok
        print(f"  [{'OK ' if passed else 'FAIL'}] {label}")
        ok = ok and passed

    check("raw source / validator / schema present", all(
        p.exists() for p in (core.resolve(chapter["raw_source"]), core.VALIDATOR, core.SCHEMA_FILE)))
    check("normalized source is readable non-empty text", len(source_text.strip()) > 200)
    check("context packet non-empty", len(context_text.strip()) > 200)

    try:
        json.dumps(core.session_schema()); json.dumps(core.patch_schema(section_ids or ["x"]))
        check("requested JSON schemas serialize", True)
    except Exception as exc:  # noqa: BLE001
        check(f"schema serialize ({exc})", False)

    # validator smoke on a synthetic valid module
    smoke = out / "preflight-smoke.json"
    smoke.write_text(json.dumps(synthetic_valid_module()), encoding="utf-8")
    v_ok, _ = core.run_validator(smoke, out / "preflight-smoke-report.json")
    check("deterministic validator works", v_ok)
    smoke.unlink(missing_ok=True)
    (out / "preflight-smoke-report.json").unlink(missing_ok=True)

    if section_ids:
        check("allowed section IDs present", len(section_ids) > 0)
        base = {"id": "m", "title": "M", "objectives": ["o"],
                "sections": [{"id": sid, "title": sid, "content": "C", "sourceRefs": ["r"]}
                             for sid in section_ids],
                "equations": [], "workedExamples": [], "checks": [],
                "practiceQuestions": [], "sourceRefs": ["r"], "sourceGaps": []}
        grounded_text = " ".join(list(core._content_words(source_text))[:10]) or "redox energy"
        good = core.apply_patch(base, {"section_updates": [
            {"section_id": section_ids[0], "append_text": grounded_text}],
            "practice_question_additions": [], "reason": "x"}, source_text)
        bad = core.apply_patch(base, {"section_updates": [
            {"section_id": "practiceQuestions", "append_text": "x"}],
            "practice_question_additions": [], "reason": "x"}, source_text)
        check("merger applies valid synthetic patch", good["applied_updates"] == 1)
        check("merger rejects invalid section id, no deletion",
              bad["applied_updates"] == 0 and bool(bad["rejected"])
              and no_deletions(base, bad["enriched"]))

    check(f"model {model} installed", adapter.model_available(model))
    print(f"  STAGE={stage} MODEL={model} CHAPTER={chapter['id']} "
          f"timeout~{adapter.OVERALL_TIMEOUT}s")
    print(f"=== PREFLIGHT {'PASSED' if ok else 'FAILED'} ===\n")
    return ok


def model_call(fn, *args, retries: int = 1) -> dict[str, Any]:
    """One automatic retry per model stage."""
    last = None
    for attempt in range(retries + 1):
        try:
            return fn(*args)
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  model stage error (attempt {attempt + 1}): {exc}")
    raise RuntimeError(f"model stage failed after {retries + 1} attempts: {last}")


# --------------------------------------------------------------------------- #
# Per-chapter pipeline
# --------------------------------------------------------------------------- #
def process_chapter(chapter: dict, models: dict, out_root: Path) -> dict[str, Any]:
    cid = chapter["id"]
    out = out_root / cid
    out.mkdir(parents=True, exist_ok=True)
    cp_file = out / "checkpoint.json"
    perf: dict[str, Any] = {"chapter": cid, "stages": {}}
    rejected_additions: list[dict] = []

    def stage_time(name: str, t0: float, meta: dict | None = None) -> None:
        perf["stages"][name] = {"seconds": round(time.perf_counter() - t0, 3)}
        if meta:
            perf["stages"][name]["prompt_eval_count"] = meta.get("prompt_eval_count")
            perf["stages"][name]["eval_count"] = meta.get("eval_count")

    try:
        # 1. DISCOVERED -> NORMALIZED
        raw_path = core.resolve(chapter["raw_source"])
        if not raw_path.exists():
            raise FileNotFoundError(f"raw source missing: {raw_path}")
        core.save_checkpoint(cp_file, "DISCOVERED", {"raw_source": str(raw_path)})

        normalized = source.normalize_raw(raw_path.read_text(encoding="utf-8-sig"))
        norm_file = out / "normalized-source.md"
        norm_file.write_text(normalized, encoding="utf-8")
        core.save_checkpoint(cp_file, "NORMALIZED")

        # 2. CONTEXT_READY
        section_text = source.extract_section(
            normalized, chapter["section_start"], chapter.get("section_stop"))
        context_text = source.build_context_packet(
            section_text, chapter["packet_title"], chapter["source_ref"],
            chapter["raw_source"])
        ctx_file = out / "context.md"
        ctx_file.write_text(context_text, encoding="utf-8")
        core.save_checkpoint(cp_file, "CONTEXT_READY")
        # source_text used for grounding = the packet's source material only
        source_text = section_text

        # 3. GENERATING -> GENERATED -> STRUCTURE_VALIDATED (one retry)
        cand_file = out / "candidate-session.json"
        cand_valid = False
        candidate: dict[str, Any] = {}
        if not preflight(chapter, out, context_text, source_text,
                         models["generator"], "GENERATE", None):
            raise RuntimeError("generation preflight failed")

        # Resume: a parseable cached generation is reused so re-running re-applies
        # the deterministic cleaning/quality gate WITHOUT a fresh (expensive,
        # deterministic) Gemma call. ponytail: reuse-raw-if-present.
        raw_file = out / "candidate-raw.txt"
        cached_raw: str | None = None
        if raw_file.exists():
            try:
                cached_raw = raw_file.read_text(encoding="utf-8")
                json.loads(cached_raw)  # only reuse if it parses
                print(f"  resume: reusing cached {raw_file.name} (no model call)")
            except (json.JSONDecodeError, OSError):
                cached_raw = None

        for attempt in range(2):  # initial + one retry
            core.save_checkpoint(cp_file, "GENERATING", {"generate_attempt": attempt + 1})
            t0 = time.perf_counter()
            if cached_raw is not None and attempt == 0:
                raw, gen_meta = cached_raw, {}
            else:
                gp = gen_prompt(context_text)
                res = adapter.generate_structured(
                    models["generator"], gp,
                    # full sessions run long; reserve generous output room or the
                    # JSON truncates mid-string (observed ~8k+ output tokens).
                    core.session_schema(), est_ctx(gp, 10000), f"{cid}:gemma")
                adapter.unload(models["generator"])
                raw, gen_meta = res["raw"], res["meta"]
                raw_file.write_text(raw, encoding="utf-8")
            try:
                candidate = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"  candidate not JSON: {exc}")
                cached_raw = None  # force a real regeneration on retry
                continue
            candidate, sani = core.sanitize_candidate(candidate)
            candidate, qual = core.quality_filter(candidate, source_text)
            if sani["removed_sections"] or sani["dropped_worked"]:
                print(f"  sanitized: removed sections={sani['removed_sections']} "
                      f"dropped_worked={len(sani['dropped_worked'])}")
            if any(qual.values()):
                print(f"  quality gate dropped: "
                      f"{ {k: len(v) for k, v in qual.items() if v} }")
            (out / "candidate-cleaning-report.json").write_text(
                json.dumps({"sanitation": sani, "quality": qual}, indent=2),
                encoding="utf-8")
            candidate["metadata"] = {
                "chapter": chapter["title"], "source_ref": chapter["source_ref"],
                "raw_source": chapter["raw_source"], "generator_model": models["generator"],
                "generated_at": _now(),
            }
            cand_file.write_text(json.dumps(candidate, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
            stage_time("generate", t0, gen_meta)
            core.save_checkpoint(cp_file, "GENERATED")
            struct_ok, vout = core.run_validator(cand_file, out / "candidate-validation.json")
            min_ok, min_reasons = core.meets_minimums(candidate)
            if not min_ok:
                print(f"  below educational minimums: {min_reasons}")
            cand_valid = struct_ok and min_ok
            if cand_valid:
                break
            print(f"  candidate failed validation/minimums (attempt {attempt + 1}):\n{vout}")

        if not cand_valid:
            raise RuntimeError(
                "candidate failed structural validation or educational minimums after retry")
        core.save_checkpoint(cp_file, "STRUCTURE_VALIDATED")

        # 4. AUDITING -> AUDITED (one retry)
        core.save_checkpoint(cp_file, "AUDITING")
        t0 = time.perf_counter()
        ap = audit_prompt(context_text, json.dumps(candidate, ensure_ascii=False))
        audit_res = model_call(
            adapter.generate_structured, models["auditor"],
            ap, _audit_schema(), est_ctx(ap, 2500), f"{cid}:phi")
        adapter.unload(models["auditor"])
        audit = json.loads(audit_res["raw"])
        (out / "phi-audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
        stage_time("audit", t0, audit_res["meta"])
        core.save_checkpoint(cp_file, "AUDITED", {"audit_verdict": audit.get("verdict")})

        # 5. ENRICHING -> ENRICHED (Qwen only when justified)
        final = candidate
        enrich_note = "no_enrichment_needed"
        justified = audit.get("verdict") in ("pass_with_concerns", "fail") and (
            audit.get("unsupported_claims") or audit.get("recommended_repairs"))
        section_ids = [s["id"] for s in candidate.get("sections", []) if s.get("id")]

        if justified:
            core.save_checkpoint(cp_file, "ENRICHING")
            if not preflight(chapter, out, context_text, source_text,
                             models["enricher"], "ENRICH", section_ids):
                raise RuntimeError("enrichment preflight failed")
            t0 = time.perf_counter()
            pp = patch_prompt(section_ids, context_text,
                              json.dumps(candidate, ensure_ascii=False),
                              json.dumps(audit, ensure_ascii=False))
            patch_res = model_call(
                adapter.generate_structured, models["enricher"],
                pp, core.patch_schema(section_ids), est_ctx(pp, 2000), f"{cid}:qwen")
            adapter.unload(models["enricher"])
            patch = json.loads(patch_res["raw"])
            (out / "qwen-patch.json").write_text(json.dumps(patch, indent=2, ensure_ascii=False),
                                                 encoding="utf-8")
            stage_time("enrich", t0, patch_res["meta"])
            merged = core.apply_patch(candidate, patch, source_text)
            rejected_additions = merged["rejected"]
            if merged["safe_no_op"]:
                enrich_note = "SAFE_NO_OP"
            else:
                # validate enriched + regression (no deletions) before accepting
                enr_file = out / "enriched-session.json"
                enr_file.write_text(json.dumps(merged["enriched"], indent=2, ensure_ascii=False),
                                    encoding="utf-8")
                enr_valid, _ = core.run_validator(enr_file, out / "enriched-validation.json")
                if enr_valid and no_deletions(candidate, merged["enriched"]):
                    final = merged["enriched"]
                    enrich_note = (f"applied:{merged['applied_updates']} updates, "
                                   f"{merged['added_questions']} questions")
                else:
                    enrich_note = "enrichment_rejected_kept_candidate"
            core.save_checkpoint(cp_file, "ENRICHED", {"enrich_note": enrich_note})

        # 6. FINAL_AUDIT -> ACCEPTED
        final_file = out / "final-session.json"
        final_file.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
        core.save_checkpoint(cp_file, "FINAL_AUDIT")
        final_valid, fvout = core.run_validator(final_file, out / "final-validation.json")
        if not (final_valid and no_deletions(candidate, final)):
            raise RuntimeError(f"final validation/regression failed:\n{fvout}")

        # 7. HTML preview
        html_doc = render.render_session_html(final)
        preview = out / "session-preview.html"
        preview.write_text(html_doc, encoding="utf-8")
        if "http://" in html_doc or "https://" in html_doc:
            raise RuntimeError("HTML preview contains external requests")

        perf["enrich_note"] = enrich_note
        perf["rejected_additions"] = rejected_additions
        perf["status"] = "ACCEPTED"
        core.save_checkpoint(cp_file, "ACCEPTED", {"enrich_note": enrich_note})
        (out / "performance.json").write_text(json.dumps(perf, indent=2), encoding="utf-8")
        print(f"\n[{cid}] ACCEPTED -> {preview}")
        return perf

    except Exception as exc:  # noqa: BLE001 - quarantine, never abort the run
        adapter.unload(models["generator"])
        adapter.unload(models["auditor"])
        adapter.unload(models["enricher"])
        perf["status"] = "QUARANTINED"
        perf["error"] = str(exc)
        core.save_checkpoint(cp_file, "QUARANTINED", {"error": str(exc)})
        out.mkdir(parents=True, exist_ok=True)
        (out / "quarantine-report.json").write_text(
            json.dumps({"chapter": cid, "error": str(exc), "at": _now(), "perf": perf},
                       indent=2), encoding="utf-8")
        (out / "performance.json").write_text(json.dumps(perf, indent=2), encoding="utf-8")
        print(f"\n[{cid}] QUARANTINED: {exc}")
        return perf


def _audit_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "verdict": {"type": "string",
                        "enum": ["pass", "pass_with_concerns", "fail"]},
            "unsupported_claims": {"type": "array", "items": {
                "type": "object",
                "properties": {"claim": {"type": "string"}, "location": {"type": "string"},
                               "reason": {"type": "string"}},
                "required": ["claim", "location", "reason"],
                "additionalProperties": False}},
            "equation_issues": {"type": "array", "items": {"type": "string"}},
            "source_reference_issues": {"type": "array", "items": {"type": "string"}},
            "pedagogy_issues": {"type": "array", "items": {"type": "string"}},
            "assessment_issues": {"type": "array", "items": {"type": "string"}},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "recommended_repairs": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
        },
        "required": ["verdict", "unsupported_claims", "equation_issues",
                     "source_reference_issues", "pedagogy_issues", "assessment_issues",
                     "strengths", "recommended_repairs", "summary"],
        "additionalProperties": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="MCAT production-pilot orchestrator")
    parser.add_argument("--config", default=str(core.PILOT_ROOT / "config" / "chapters.json"))
    parser.add_argument("--chapters", default="", help="comma-separated chapter ids to run")
    args = parser.parse_args()

    cfg = core.load_config(Path(args.config))
    models = cfg["models"]
    out_root = core.resolve(cfg["output_dir"])
    out_root.mkdir(parents=True, exist_ok=True)

    wanted = {c.strip() for c in args.chapters.split(",") if c.strip()}
    chapters = [c for c in cfg["chapters"] if not wanted or c["id"] in wanted]

    results = []
    for ch in chapters:  # strictly sequential: one model loaded at a time
        results.append(process_chapter(ch, models, out_root))

    print("\n===== PILOT SUMMARY =====")
    for r in results:
        print(f"  {r['chapter']}: {r['status']}  ({r.get('enrich_note', r.get('error', ''))})")
    (out_root / "pilot-summary.json").write_text(
        json.dumps({"at": _now(), "results": results}, indent=2), encoding="utf-8")
    return 0 if all(r["status"] == "ACCEPTED" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
