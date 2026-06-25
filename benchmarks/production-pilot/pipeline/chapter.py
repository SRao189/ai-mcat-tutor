"""Chapter-level orchestrator: ONE unified tutoring session for a whole chapter,
built from internally chunked, bounded per-subsection generation.

    python -m pipeline.chapter --config config/chapters.json --chapter chapter-03

The user-facing output is a single final-session.json + one session-preview.html.
Generation is never one giant call: each numbered subsection runs the bounded
three-component flow (lesson / equations+worked / assessment), components cache
independently, and everything merges into one chapter session with subsection-
prefixed ids. Reuses run.py's prompts/helpers and core's schemas/gate verbatim.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from . import adapter, core, render, run, source

# Per-component output caps (tokens). Bounded so no single call runs away.
_CAPS = {"lesson": 1500, "eqworked": 1000, "assessment": 1400}


# --------------------------------------------------------------------------- #
# Per-subsection generation + chapter assembly helpers
# --------------------------------------------------------------------------- #
def _prefix_and_tag(sub: dict[str, Any], subid: str) -> dict[str, Any]:
    """Prefix section ids with the subsection id (collision-proof) and tag every
    item with its subsection so the renderer can group by source order."""
    idmap: dict[str, str] = {}
    for s in sub.get("sections", []):
        old = s.get("id", "s")
        new = f"{subid}-{old}"
        idmap[old] = new
        s["id"] = new
        s["subsection"] = subid
    for coll in ("equations", "workedExamples"):
        for it in sub.get(coll, []):
            it["subsection"] = subid
    for coll in ("checks", "practiceQuestions"):
        for q in sub.get(coll, []):
            q["subsection"] = subid
            if q.get("reviewTarget") in idmap:
                q["reviewTarget"] = idmap[q["reviewTarget"]]
    return sub


def _gen_subsection(gmodel: str, subid: str, ctx: str, body: str, ref: str,
                    comp_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    lesson, ml = run._gen_component(
        gmodel, run.lesson_prompt(ctx), core.lesson_schema(),
        f"{subid}:gemma:lesson", _CAPS["lesson"], comp_dir / f"{subid}-lesson.json")
    section_ids = [s["id"] for s in lesson.get("sections", []) if s.get("id")]
    eqw, me = run._gen_component(
        gmodel, run.eqworked_prompt(ctx), core.eqworked_schema(),
        f"{subid}:gemma:eqworked", _CAPS["eqworked"], comp_dir / f"{subid}-eqworked.json")
    assess, ma = run._gen_component(
        gmodel, run.assessment_prompt(ctx, section_ids),
        core.assessment_schema(section_ids),
        f"{subid}:gemma:assessment", _CAPS["assessment"], comp_dir / f"{subid}-assessment.json")
    sub = core.merge_components(
        {"lesson": lesson, "eqworked": eqw, "assessment": assess}, ref)
    sub = _prefix_and_tag(sub, subid)
    sub, _ = core.sanitize_candidate(sub)
    sub, _ = core.quality_filter(sub, body)  # per-subsection caps apply here
    tokens = {k: m.get("eval_count") for k, m in
              (("lesson", ml), ("eqworked", me), ("assessment", ma))}
    return sub, tokens


def _gap_subsection(subid: str, title: str, exc: Exception) -> dict[str, Any]:
    return {
        "objectives": [], "sections": [], "equations": [], "workedExamples": [],
        "checks": [], "practiceQuestions": [], "sourceRefs": [],
        "sourceGaps": [f"SOURCE GAP ({subid} {title}): subsection could not be "
                       f"generated ({exc})"],
    }


def _uniq(items: list) -> list:
    out: list = []
    for x in items:
        if x not in out:
            out.append(x)
    return out


def _dedup_equations(eqs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for e in eqs:
        key = "".join(str(e.get("expression", "")).split()).lower()
        if key and key not in seen:
            seen.add(key)
            out.append(e)
    return out


def assemble_chapter(chapter_cfg: dict, sub_results: list[tuple]) -> dict[str, Any]:
    """Concatenate accepted subsection outputs (already prefixed/tagged) into one
    chapter session, preserving subsection order."""
    agg: dict[str, list] = {k: [] for k in
                            ("objectives", "sections", "equations", "workedExamples",
                             "checks", "practiceQuestions", "sourceGaps", "sourceRefs")}
    for _subid, _title, sub, _status in sub_results:
        for k in agg:
            agg[k] += sub.get(k, [])
    return {
        "id": chapter_cfg["id"],
        "title": chapter_cfg.get("chapter_title", chapter_cfg["title"]),
        "objectives": _uniq(agg["objectives"])[:8],
        "sections": agg["sections"],
        "equations": agg["equations"],
        "workedExamples": agg["workedExamples"],
        "checks": agg["checks"],
        "practiceQuestions": agg["practiceQuestions"],
        "sourceRefs": _uniq(agg["sourceRefs"]) or [chapter_cfg["source_ref"]],
        "sourceGaps": _uniq(agg["sourceGaps"]),
    }


def _migrate_legacy_cache(out: Path, comp_dir: Path) -> None:
    """Reuse the already-accepted single-run 3.1 component caches if present."""
    for comp in ("lesson", "eqworked", "assessment"):
        legacy = out / f"component-{comp}.json"
        target = comp_dir / f"3.1-{comp}.json"
        if legacy.exists() and not target.exists():
            target.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  reuse: seeded {target.name} from accepted single-run cache")


# --------------------------------------------------------------------------- #
# Chapter-wide audit + (justified) additive enrichment -- best effort, guarded
# --------------------------------------------------------------------------- #
def _chapter_audit(session: dict, model: str, out: Path, perf: dict) -> dict:
    digest = "\n\n".join(s.get("content", "") for s in session.get("sections", []))[:5000]
    ap = run.audit_prompt(digest, json.dumps(session, ensure_ascii=False))
    t0 = time.perf_counter()
    try:
        res = adapter.generate_structured(
            model, ap, run._audit_schema(), run.est_ctx(ap, 1500),
            "chapter:phi", num_predict=900, read_timeout=600)
        adapter.unload(model)
        audit = json.loads(res["raw"])
    except Exception as exc:  # noqa: BLE001 - audit is secondary to the deterministic gate
        adapter.unload(model)
        audit = {"verdict": "unavailable", "summary": f"audit skipped: {exc}",
                 "unsupported_claims": [], "recommended_repairs": []}
        print(f"  chapter audit skipped: {exc}")
    perf["stages"]["audit"] = {"seconds": round(time.perf_counter() - t0, 3),
                               "verdict": audit.get("verdict")}
    (out / "final-audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit


def _maybe_enrich(session: dict, audit: dict, source_text: str, model: str,
                  out: Path, perf: dict) -> dict:
    justified = audit.get("verdict") in ("pass_with_concerns", "fail") and (
        audit.get("unsupported_claims") or audit.get("recommended_repairs"))
    if not justified:
        perf["stages"]["enrich"] = {"note": "no_enrichment_needed"}
        return session
    section_ids = [s["id"] for s in session.get("sections", []) if s.get("id")]
    digest = "\n\n".join(s.get("content", "") for s in session["sections"])[:5000]
    pp = run.patch_prompt(section_ids, digest, json.dumps(session, ensure_ascii=False),
                          json.dumps(audit, ensure_ascii=False))
    t0 = time.perf_counter()
    note = "no_enrichment_needed"
    try:
        res = adapter.generate_structured(
            model, pp, core.patch_schema(section_ids), run.est_ctx(pp, 1500),
            "chapter:qwen", num_predict=900, read_timeout=600)
        adapter.unload(model)
        patch = json.loads(res["raw"])
        (out / "qwen-patch.json").write_text(
            json.dumps(patch, indent=2, ensure_ascii=False), encoding="utf-8")
        merged = core.apply_patch(session, patch, source_text)
        if not merged["safe_no_op"] and run.no_deletions(session, merged["enriched"]):
            session = merged["enriched"]
            note = f"applied:{merged['applied_updates']} updates,{merged['added_questions']} questions"
        else:
            note = "SAFE_NO_OP" if merged["safe_no_op"] else "rejected_kept_merged"
    except Exception as exc:  # noqa: BLE001
        adapter.unload(model)
        note = f"enrich skipped: {exc}"
        print(f"  chapter enrich skipped: {exc}")
    perf["stages"]["enrich"] = {"seconds": round(time.perf_counter() - t0, 3), "note": note}
    return session


# --------------------------------------------------------------------------- #
# Build one chapter
# --------------------------------------------------------------------------- #
def build_chapter(chapter_cfg: dict, models: dict, out_root: Path) -> dict[str, Any]:
    cid = chapter_cfg["id"]
    out = out_root / cid
    ctx_dir, comp_dir = out / "contexts", out / "components"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    comp_dir.mkdir(parents=True, exist_ok=True)
    cp = out / "checkpoint.json"
    perf: dict[str, Any] = {"chapter": cid, "mode": "full-chapter",
                            "subsections": {}, "stages": {}}

    raw_path = core.resolve(chapter_cfg["raw_source"])
    normalized = source.normalize_raw(raw_path.read_text(encoding="utf-8-sig"))
    (out / "full-normalized-source.md").write_text(normalized, encoding="utf-8")
    core.save_checkpoint(cp, "NORMALIZED")

    chnum = int(chapter_cfg.get("chapter_number", cid.split("-")[-1]))
    subs = source.split_subsections(normalized, chnum)
    core.save_checkpoint(cp, "SPLIT", {"subsections": [s[0] for s in subs]})
    print(f"  subsections: {[s[0] + ' ' + s[1] for s in subs]}")

    _migrate_legacy_cache(out, comp_dir)
    gmodel = models["generator"]
    sub_results: list[tuple] = []
    for subid, title, body in subs:
        ref = f'{chapter_cfg["raw_source"]}#{subid}'
        ctx = source.build_context_packet(
            body, f"{title} ({subid})", ref, chapter_cfg["raw_source"])
        (ctx_dir / f"{subid}.md").write_text(ctx, encoding="utf-8")
        core.save_checkpoint(cp, "SUBSECTION", {"current": subid})
        t0 = time.perf_counter()
        try:
            sub, tokens = _gen_subsection(gmodel, subid, ctx, body, ref, comp_dir)
            if not sub.get("sections"):
                raise ValueError("no grounded lesson sections after filtering")
            status = "ACCEPTED"
        except Exception as exc:  # noqa: BLE001 - one bad subsection must not kill the chapter
            sub, tokens = _gap_subsection(subid, title, exc), {}
            status = f"SOURCE GAP ({subid}): {exc}"
            print(f"  [{subid}] SOURCE-GAPPED: {exc}")
        perf["subsections"][subid] = {
            "seconds": round(time.perf_counter() - t0, 3), "tokens": tokens,
            "status": status,
            "reused": bool(tokens) and all(v is None for v in tokens.values())}
        sub_results.append((subid, title, sub, status))
        core.save_checkpoint(cp, "SUBSECTION_DONE", {"done": subid, "status": status})

    # Assemble + chapter-wide sanitation/quality (no per-subsection caps) + dedup.
    session = assemble_chapter(chapter_cfg, sub_results)
    session, _ = core.sanitize_candidate(session)
    session, qual = core.quality_filter(session, normalized, cap=False)
    session["equations"] = _dedup_equations(session.get("equations", []))
    session["practiceQuestions"] = session.get("practiceQuestions", [])[:10]  # 5-10 review
    session["metadata"] = {
        "chapter": session["title"], "source_ref": chapter_cfg["source_ref"],
        "raw_source": chapter_cfg["raw_source"], "generator_model": gmodel,
        "generated_at": run._now(), "generation": "chapter-bounded-components",
        "subsections": [{"id": s[0], "title": s[1], "status": s[3]} for s in sub_results],
    }
    (out / "chapter-cleaning-report.json").write_text(
        json.dumps(qual, indent=2), encoding="utf-8")
    core.save_checkpoint(cp, "MERGED")

    final = out / "final-session.json"
    final.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")
    ok, vout = core.run_validator(final, out / "final-validation.json")
    if not ok:
        raise RuntimeError(f"chapter validation failed: {vout}")

    audit = _chapter_audit(session, models["auditor"], out, perf)
    core.save_checkpoint(cp, "AUDITED", {"verdict": audit.get("verdict")})
    session = _maybe_enrich(session, audit, normalized, models["enricher"], out, perf)
    final.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")
    ok2, fvout = core.run_validator(final, out / "final-validation.json")
    if not ok2:
        raise RuntimeError(f"post-enrichment validation failed: {fvout}")
    core.save_checkpoint(cp, "ENRICHED")

    html = render.render_chapter_html(session)
    (out / "session-preview.html").write_text(html, encoding="utf-8")
    if "http://" in html or "https://" in html:
        raise RuntimeError("preview contains external requests")

    accepted_subs = sum(1 for s in sub_results if s[3] == "ACCEPTED")
    perf["status"] = "ACCEPTED"
    perf["totals"] = {
        "accepted_subsections": accepted_subs, "subsections": len(sub_results),
        "sections": len(session["sections"]), "equations": len(session["equations"]),
        "workedExamples": len(session["workedExamples"]), "checks": len(session["checks"]),
        "review_questions": len(session["practiceQuestions"]),
        "sourceGaps": len(session["sourceGaps"]),
        "chapter_tokens": sum(v for sub in perf["subsections"].values()
                              for v in sub["tokens"].values() if v),
    }
    (out / "performance.json").write_text(json.dumps(perf, indent=2), encoding="utf-8")
    core.save_checkpoint(cp, "ACCEPTED")
    print(f"\n[{cid}] ACCEPTED  ({accepted_subs}/{len(sub_results)} subsections) -> "
          f"{out / 'session-preview.html'}")
    return perf


def main() -> int:
    ap = argparse.ArgumentParser(description="MCAT chapter-level session builder")
    ap.add_argument("--config", default=str(core.PILOT_ROOT / "config" / "chapters.json"))
    ap.add_argument("--chapter", required=True)
    a = ap.parse_args()
    cfg = core.load_config(Path(a.config))
    models = cfg["models"]
    out_root = core.resolve(cfg["output_dir"])
    out_root.mkdir(parents=True, exist_ok=True)
    ch = next(c for c in cfg["chapters"] if c["id"] == a.chapter)
    try:
        build_chapter(ch, models, out_root)
        return 0
    except Exception as exc:  # noqa: BLE001 - quarantine, never abort
        for m in models.values():
            adapter.unload(m)
        out = out_root / a.chapter
        out.mkdir(parents=True, exist_ok=True)
        core.save_checkpoint(out / "checkpoint.json", "QUARANTINED", {"error": str(exc)})
        (out / "quarantine-report.json").write_text(
            json.dumps({"chapter": a.chapter, "error": str(exc), "at": run._now()},
                       indent=2), encoding="utf-8")
        print(f"\n[{a.chapter}] QUARANTINED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
