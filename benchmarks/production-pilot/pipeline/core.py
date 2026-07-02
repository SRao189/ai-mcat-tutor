"""Orchestration core: config, state machine, schemas, merge logic, validation.

Storage is plain local filesystem here. The only environment-specific pieces are
this module's path handling (swap for S3/object storage later) and adapter.py
(swap for a hosted model endpoint). See README.md.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PILOT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = REPO_ROOT / "schemas" / "module.schema.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate-module.py"

# Explicit checkpointed states (Phase 4 of the mission).
STATES = [
    "DISCOVERED", "NORMALIZED", "CONTEXT_READY", "GENERATING", "GENERATED",
    "STRUCTURE_VALIDATED", "AUDITING", "AUDITED", "ENRICHING", "ENRICHED",
    "FINAL_AUDIT", "ACCEPTED", "QUARANTINED",
]

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "has", "have", "which", "when", "what", "into", "their", "they", "them",
    "will", "would", "than", "then", "these", "those", "such", "also", "more",
    "most", "some", "can", "may", "where", "while", "because", "between", "both",
    "each", "other", "your", "you", "its", "it's", "about", "there", "here",
}


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve(rel: str) -> Path:
    """Resolve a config path relative to the repo root (portable, not absolute)."""
    return (REPO_ROOT / rel).resolve()


# --------------------------------------------------------------------------- #
# Checkpoints (idempotent / restartable)
# --------------------------------------------------------------------------- #
def load_checkpoint(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {"state": None, "history": []}


def save_checkpoint(path: Path, state: str, extra: dict[str, Any] | None = None) -> None:
    cp = load_checkpoint(path)
    cp["state"] = state
    cp["history"] = cp.get("history", []) + [state]
    if extra:
        cp.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cp, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
def session_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Bounded-component schemas (one runaway single call -> three capped calls).
# Each is small + maxItems-bounded so a num_predict cap is never hit mid-JSON.
# --------------------------------------------------------------------------- #
_SECTION = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "content": {"type": "string", "minLength": 1},
        "sourceRefs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    },
    "required": ["id", "title", "content", "sourceRefs"],
    "additionalProperties": False,
}
_EQUATION = {
    "type": "object",
    "properties": {
        "expression": {"type": "string", "minLength": 1},
        "meaning": {"type": "string", "minLength": 1},
        "sourceRefs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    },
    "required": ["expression", "meaning", "sourceRefs"],
    "additionalProperties": False,
}
_WORKED = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "minLength": 1},
        "steps": {"type": "array", "items": {"type": "string"}},
        "answer": {"type": "string", "minLength": 1},
        "sourceRefs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    },
    "required": ["question", "steps", "answer", "sourceRefs"],
    "additionalProperties": False,
}


def lesson_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1},
            "objectives": {"type": "array", "minItems": 2, "maxItems": 4,
                           "items": {"type": "string", "minLength": 1}},
            "sections": {"type": "array", "minItems": 2, "maxItems": 4, "items": _SECTION},
        },
        "required": ["id", "title", "objectives", "sections"],
        "additionalProperties": False,
    }


def eqworked_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "equations": {"type": "array", "maxItems": 4, "items": _EQUATION},
            "workedExamples": {"type": "array", "maxItems": 2, "items": _WORKED},
        },
        "required": ["equations", "workedExamples"],
        "additionalProperties": False,
    }


def assessment_schema(section_ids: list[str]) -> dict[str, Any]:
    q = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 1},
            "answer": {"type": "string", "minLength": 1},
            "explanation": {"type": "string", "minLength": 1},
            "sourceRefs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "reviewTarget": {"type": "string", "enum": section_ids or ["section"]},
        },
        "required": ["question", "answer", "explanation", "sourceRefs", "reviewTarget"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "checks": {"type": "array", "maxItems": 3, "items": q},
            "practiceQuestions": {"type": "array", "maxItems": 3, "items": q},
        },
        "required": ["checks", "practiceQuestions"],
        "additionalProperties": False,
    }


# Component keys + the merge that reassembles a full session deterministically.
COMPONENTS = ("lesson", "eqworked", "assessment")


def merge_components(parts: dict[str, Any], default_source_ref: str) -> dict[str, Any]:
    """Deterministically reassemble the three bounded components into one session.
    Raises if a component is missing (-> chapter quarantine). Dedupes section ids
    (keep first); aggregates unique sourceRefs."""
    missing = [k for k in COMPONENTS if not isinstance(parts.get(k), dict)]
    if missing:
        raise ValueError(f"missing generation component(s): {missing}")
    a, b, c = parts["lesson"], parts["eqworked"], parts["assessment"]

    seen: set[str] = set()
    sections = []
    for s in a.get("sections", []):
        sid = s.get("id")
        if sid and sid not in seen:
            seen.add(sid)
            sections.append(s)

    session = {
        "id": a.get("id") or "session",
        "title": a.get("title") or "Tutoring Session",
        "objectives": a.get("objectives", []),
        "sections": sections,
        "equations": b.get("equations", []),
        "workedExamples": b.get("workedExamples", []),
        "checks": c.get("checks", []),
        "practiceQuestions": c.get("practiceQuestions", []),
        "sourceGaps": [],
    }
    refs: list[str] = []
    for coll in ("sections", "equations", "workedExamples", "checks", "practiceQuestions"):
        for item in session[coll]:
            for r in item.get("sourceRefs", []):
                if r not in refs:
                    refs.append(r)
    session["sourceRefs"] = refs or [default_source_ref]
    return session


def patch_schema(section_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "section_updates": {
                "type": "array", "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string", "enum": section_ids},
                        "append_text": {"type": "string", "minLength": 1},
                    },
                    "required": ["section_id", "append_text"],
                    "additionalProperties": False,
                },
            },
            "practice_question_additions": {
                "type": "array", "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "minLength": 1},
                        "answer": {"type": "string", "minLength": 1},
                        "explanation": {"type": "string", "minLength": 1},
                        "sourceRefs": {"type": "array", "minItems": 1,
                                       "items": {"type": "string"}},
                        "reviewTarget": {"type": "string", "enum": section_ids},
                    },
                    "required": ["question", "answer", "explanation",
                                 "sourceRefs", "reviewTarget"],
                    "additionalProperties": False,
                },
            },
            "reason": {"type": "string", "minLength": 1},
        },
        "required": ["section_updates", "practice_question_additions", "reason"],
        "additionalProperties": False,
    }


# --------------------------------------------------------------------------- #
# Grounding + dedup helpers (deterministic; heuristic — see ceilings noted)
# --------------------------------------------------------------------------- #
def _content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9\-]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def is_grounded(text: str, source_text: str, threshold: float = 0.5) -> bool:
    """Heuristic: a fraction >= threshold of the claim's content words must
    appear in the source packet. ponytail: bag-of-words overlap, not semantic
    entailment — upgrade to an embedding/NLI check if false-accepts appear.
    """
    claim = _content_words(text)
    if not claim:
        return False
    src = _content_words(source_text)
    matched = sum(1 for w in claim if w in src)
    return matched / len(claim) >= threshold


def _q_key(text: str) -> frozenset[str]:
    return frozenset(_content_words(text))


def _is_near_duplicate(new_q: str, existing: list[str], jaccard: float = 0.8) -> bool:
    a = _q_key(new_q)
    if not a:
        return True
    for ex in existing:
        b = _q_key(ex)
        if not b:
            continue
        inter = len(a & b)
        union = len(a | b)
        if union and inter / union >= jaccard:
            return True
    return False


# --------------------------------------------------------------------------- #
# Candidate sanitation (deterministic; fixes real failures Gemma exhibited)
# --------------------------------------------------------------------------- #
# Gemma duplicates assessment items into sections[] AND invents worked-example
# numbers. We strip both deterministically (project rule: dedup + grounding are
# code's job, not the model's).
_FAB_HEDGE = re.compile(
    r"(?i)hypothetical|would be provided|let'?s assume|for example,?\s*let|"
    r"suppose that|made[- ]up|placeholder|in a real problem|for illustration")


def _is_assessment_section(sec: dict[str, Any]) -> bool:
    content = sec.get("content", "")
    title = sec.get("title", "")
    if re.search(r"(?i)\breview\s*target\s*:", content):
        return True
    if re.search(r"(?i)\banswer\s*:", content) and \
       re.search(r"(?i)\b(explanation|review\s*target)\s*:", content):
        return True
    if re.match(r"(?i)\s*(assessment|check\b|check\s*\d|practice question|worked example)", title):
        return True
    return False


def _is_fabricated_worked(w: dict[str, Any]) -> bool:
    blob = " ".join([w.get("question", ""), w.get("answer", ""), *w.get("steps", [])])
    return bool(_FAB_HEDGE.search(blob))


def sanitize_candidate(candidate: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list]]:
    """Strip assessment-shaped sections (duplicated in typed arrays) and worked
    examples that hedge with invented data. Returns (clean, report)."""
    c: dict[str, Any] = json.loads(json.dumps(candidate, ensure_ascii=False))
    removed_sections = [s.get("id", "?") for s in c.get("sections", [])
                        if _is_assessment_section(s)]
    c["sections"] = [s for s in c.get("sections", []) if not _is_assessment_section(s)]
    dropped_worked = [w.get("question", "")[:70] for w in c.get("workedExamples", [])
                      if _is_fabricated_worked(w)]
    c["workedExamples"] = [w for w in c.get("workedExamples", [])
                           if not _is_fabricated_worked(w)]
    if dropped_worked:
        c.setdefault("sourceGaps", []).append(
            "SOURCE GAP: removed a worked example that introduced data not present "
            "in the source packet.")
    return c, {"removed_sections": removed_sections, "dropped_worked": dropped_worked}


# --------------------------------------------------------------------------- #
# Educational-quality gate (deterministic; each rule fixes a real Ch-3 failure)
# --------------------------------------------------------------------------- #
# These detect-and-remove; they never invent corrected facts (project rule:
# no outside knowledge). A drop that pushes the session below schema minimums
# surfaces later as a structural-validation failure -> quarantine.
_SIGN_SYMBOLS = {
    "H": re.compile(r"(?:Δ|∆|delta\s*)h\b", re.IGNORECASE),
    "S": re.compile(r"(?:Δ|∆|delta\s*)s\b", re.IGNORECASE),
    "G": re.compile(r"(?:Δ|∆|delta\s*)g\b", re.IGNORECASE),
}
_SIGN_WORDS = re.compile(r"\b(positive|negative)\b", re.IGNORECASE)
_EQUAL = re.compile(r"\bequal\b", re.IGNORECASE)
_CONC = re.compile(r"\bconcentrations?\b", re.IGNORECASE)
# Correct statements ("concentrations are constant but NOT equal") must survive.
_NOT_EQUAL = re.compile(
    r"(?i)not\s+(?:necessarily\s+)?equal|unequal|aren'?t\s+equal|"
    r"are\s+not\s+equal|need\s+not")


def _question_blob(q: dict[str, Any]) -> str:
    return " ".join(str(q.get(k, "")) for k in ("question", "answer", "explanation"))


# Worked examples are the prime fabrication risk: a model invents a reaction with
# real-looking numbers/units/formulas. Broad word overlap waves those through, so
# every "hard" token (number, digit-bearing chemical formula) must literally
# appear in the packet too. ponytail: numbers + digit-formulas; add bare-species
# (CO, NaCl) detection if a fabrication slips past.
_NUM = re.compile(r"\d+(?:\.\d+)?")
_FORMULA = re.compile(r"\b[A-Za-z]*[A-Z][a-z]?\d+[A-Za-z0-9]*\b")


def _worked_blob(w: dict[str, Any]) -> str:
    return " ".join([w.get("question", ""), w.get("answer", ""), *w.get("steps", [])])


def _worked_grounded(w: dict[str, Any], source_text: str) -> bool:
    blob = _worked_blob(w)
    if not is_grounded(blob, source_text):
        return False
    src = source_text.lower()
    hard = set(_NUM.findall(blob)) | {m.lower() for m in _FORMULA.findall(blob)}
    return all(tok.lower() in src for tok in hard)


def _sign_contradiction(text: str) -> bool:
    """A symbol asserted both positive and negative in the same Q is contradictory.
    Each sign word is attributed to its NEAREST symbol so 'ΔS positive and ΔH
    negative' is consistent, not a false hit.
    ponytail: nearest-token regex on ΔH/ΔS/ΔG only; upgrade to parsing if needed."""
    symbols = [(m.start(), name)
               for name, pat in _SIGN_SYMBOLS.items() for m in pat.finditer(text)]
    if not symbols:
        return False
    signs: dict[str, set[str]] = {}
    for sm in _SIGN_WORDS.finditer(text):
        pos, sign = sm.start(), sm.group(1).lower()
        nearest = min(symbols, key=lambda s: abs(s[0] - pos))
        if abs(nearest[0] - pos) <= 25:
            signs.setdefault(nearest[1], set()).add(sign)
    return any(len(v) > 1 for v in signs.values())


def _claims_equal_equilibrium_concentrations(text: str) -> bool:
    """Reject 'at equilibrium concentrations are equal'. Equal RATES is correct;
    equal CONCENTRATIONS is the error. ponytail: equal<->concentration within
    40 chars + 'equilibrium' present + no negation; NLI upgrade if false hits."""
    low = text.lower()
    if "equilibrium" not in low or _NOT_EQUAL.search(low):
        return False
    eqs = [m.start() for m in _EQUAL.finditer(low)]
    concs = [m.start() for m in _CONC.finditer(low)]
    return any(abs(e - c) <= 40 for e in eqs for c in concs)


def quality_filter(
    candidate: dict[str, Any], source_text: str, cap: bool = True
) -> tuple[dict[str, Any], dict[str, list]]:
    """Deterministic educational-quality gate run on the sanitized candidate.
    Drops (never rewrites) items that fail source grounding or internal
    consistency. Returns (clean, report). cap=False keeps the filters but skips
    the per-subsection 4-objective / 5-question caps (used for chapter merges)."""
    c: dict[str, Any] = json.loads(json.dumps(candidate, ensure_ascii=False))
    report: dict[str, list] = {
        "ungrounded_worked": [], "sign_contradictions": [], "equilibrium_equal": [],
        "ungrounded_objectives": [], "duplicate_questions": [],
    }

    # #2 worked examples must be grounded in the packet (confident fabrications
    # the _FAB_HEDGE regex misses).
    kept_worked = []
    for w in c.get("workedExamples", []):
        if _worked_grounded(w, source_text):
            kept_worked.append(w)
        else:
            report["ungrounded_worked"].append(w.get("question", "")[:70])
    c["workedExamples"] = kept_worked

    # #5 objectives must reflect taught (source-grounded) content.
    kept_obj = []
    for o in c.get("objectives", []):
        if is_grounded(str(o), source_text):
            kept_obj.append(o)
        else:
            report["ungrounded_objectives"].append(str(o)[:70])
    c["objectives"] = kept_obj

    # #3 + #4 internal consistency on each question; #6 dedup across both arrays.
    seen: list[str] = []
    for arr_name in ("checks", "practiceQuestions"):
        kept = []
        for q in c.get(arr_name, []):
            if not isinstance(q, dict):
                continue
            blob = _question_blob(q)
            qtext = q.get("question", "")
            if _sign_contradiction(blob):
                report["sign_contradictions"].append(qtext[:70])
                continue
            if _claims_equal_equilibrium_concentrations(blob):
                report["equilibrium_equal"].append(qtext[:70])
                continue
            if _is_near_duplicate(qtext, seen):
                report["duplicate_questions"].append(qtext[:70])
                continue
            seen.append(qtext)
            kept.append(q)
        c[arr_name] = kept

    # Caps (over-quota is not a defect, just trim): <=4 objectives, <=5 questions
    # total (checks first, then practice). Skipped for chapter-wide merges.
    if cap:
        c["objectives"] = c.get("objectives", [])[:4]
        c["checks"] = c.get("checks", [])[:5]
        c["practiceQuestions"] = c.get("practiceQuestions", [])[:max(0, 5 - len(c["checks"]))]

    # If no worked example survives, document the absence honestly (a meta-note,
    # not invented content) instead of silently omitting it -> satisfies the
    # worked-example floor without fabricating a problem.
    if not c.get("workedExamples"):
        gaps = c.setdefault("sourceGaps", [])
        if not any("worked example" in str(g).lower() for g in gaps):
            gaps.append("SOURCE GAP: the source packet for this section does not "
                        "include a fully worked numerical example.")
    if report["ungrounded_worked"]:
        c.setdefault("sourceGaps", []).append(
            "SOURCE GAP: removed a worked example whose content is not grounded in "
            "the source packet.")
    if report["ungrounded_objectives"]:
        c.setdefault("sourceGaps", []).append(
            "SOURCE GAP: removed a learning objective promising a skill the source "
            "packet does not teach.")
    return c, report


def enforce_source_refs(
    candidate: dict[str, Any],
    default_source_ref: str,
    subsection_refs: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]]]:
    """Make deterministic citation authority explicit.

    The generator may omit refs or cite a stale packet slug. This gate never
    changes factual content; it only rewrites item-level sourceRefs to the
    configured packet ref that the orchestrator actually supplied. In chapter
    mode, subsection-tagged items must cite their own subsection packet.
    """
    c: dict[str, Any] = json.loads(json.dumps(candidate, ensure_ascii=False))
    subsection_refs = subsection_refs or {}
    allowed = {default_source_ref, *subsection_refs.values()}
    report: dict[str, list[dict[str, str]]] = {
        "normalized": [], "missing": [], "disallowed": [],
    }

    def canonical(item: dict[str, Any]) -> str:
        sub = item.get("subsection")
        if sub in subsection_refs:
            return subsection_refs[sub]
        return default_source_ref

    def normalize_item_refs(coll: str, item: dict[str, Any]) -> None:
        want = canonical(item)
        refs = item.get("sourceRefs")
        valid_refs = [r for r in refs if isinstance(r, str) and r in allowed] \
            if isinstance(refs, list) else []
        original = refs if isinstance(refs, list) else []
        if not original:
            report["missing"].append({"collection": coll, "item": _item_label(item)})
        bad = [str(r) for r in original if not isinstance(r, str) or r not in allowed]
        if bad:
            report["disallowed"].append({
                "collection": coll, "item": _item_label(item), "refs": ", ".join(bad)
            })
        if valid_refs != [want]:
            item["sourceRefs"] = [want]
            report["normalized"].append({
                "collection": coll, "item": _item_label(item), "sourceRef": want
            })
        else:
            item["sourceRefs"] = valid_refs

    for coll in ("sections", "equations", "workedExamples", "checks", "practiceQuestions"):
        for item in c.get(coll, []):
            if isinstance(item, dict):
                normalize_item_refs(coll, item)

    refs: list[str] = []
    for coll in ("sections", "equations", "workedExamples", "checks", "practiceQuestions"):
        for item in c.get(coll, []):
            for ref in item.get("sourceRefs", []):
                if ref not in refs:
                    refs.append(ref)
    c["sourceRefs"] = refs or [default_source_ref]
    return c, report


def _item_label(item: dict[str, Any]) -> str:
    for key in ("id", "title", "question", "expression"):
        val = item.get(key)
        if val:
            return str(val)[:70]
    return "item"


def meets_minimums(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    """Educational acceptance floor applied after quality_filter. Failing any of
    these quarantines the chapter (the other chapter still proceeds)."""
    reasons: list[str] = []
    nobj = len(candidate.get("objectives", []))
    if not 2 <= nobj <= 4:
        reasons.append(f"objectives={nobj} (need 2-4)")
    nsec = len([s for s in candidate.get("sections", []) if isinstance(s, dict)])
    if nsec < 2:
        reasons.append(f"sections={nsec} (need >=2)")
    nq = len(candidate.get("checks", [])) + len(candidate.get("practiceQuestions", []))
    if not 3 <= nq <= 5:
        reasons.append(f"assessment_questions={nq} (need 3-5)")
    has_worked = len(candidate.get("workedExamples", [])) >= 1
    has_gap = any("SOURCE GAP" in str(g) for g in candidate.get("sourceGaps", []))
    if not (has_worked or has_gap):
        reasons.append("no grounded worked example and no SOURCE GAP")
    return (not reasons), reasons


# --------------------------------------------------------------------------- #
# Merge: additive only. Never deletes/replaces. Rejects ungrounded / dup / bad-id.
# --------------------------------------------------------------------------- #
def apply_patch(
    candidate: dict[str, Any],
    patch: dict[str, Any],
    source_text: str,
) -> dict[str, Any]:
    enriched: dict[str, Any] = json.loads(json.dumps(candidate, ensure_ascii=False))
    sections_by_id = {
        s["id"]: s for s in enriched.get("sections", [])
        if isinstance(s, dict) and s.get("id")
    }
    rejected: list[dict[str, str]] = []
    applied_updates = 0

    for upd in patch.get("section_updates", []):
        sid = upd.get("section_id")
        text = str(upd.get("append_text", "")).strip()
        if sid not in sections_by_id:
            rejected.append({"item": str(sid), "reason": "unknown_section_id"})
            continue
        if not text:
            rejected.append({"item": str(sid), "reason": "empty_append_text"})
            continue
        if not is_grounded(text, source_text):
            rejected.append({"item": text[:60], "reason": "ungrounded_section_update"})
            continue
        sections_by_id[sid]["content"] += "\n\n" + text
        applied_updates += 1

    existing_qs = [
        q.get("question", "") for q in enriched.get("practiceQuestions", [])
        if isinstance(q, dict)
    ]
    added_questions = 0
    for q in patch.get("practice_question_additions", []):
        target = q.get("reviewTarget")
        qtext = q.get("question", "")
        grounding_text = f"{q.get('answer', '')} {q.get('explanation', '')}"
        if target not in sections_by_id:
            rejected.append({"item": str(target), "reason": "unknown_review_target"})
            continue
        if _is_near_duplicate(qtext, existing_qs):
            rejected.append({"item": qtext[:60], "reason": "duplicate_question"})
            continue
        if not is_grounded(grounding_text, source_text):
            rejected.append({"item": qtext[:60], "reason": "ungrounded_question"})
            continue
        enriched.setdefault("practiceQuestions", []).append(q)
        existing_qs.append(qtext)
        added_questions += 1

    safe_no_op = applied_updates == 0 and added_questions == 0
    return {
        "enriched": enriched,
        "applied_updates": applied_updates,
        "added_questions": added_questions,
        "rejected": rejected,
        "safe_no_op": safe_no_op,
    }


# --------------------------------------------------------------------------- #
# Deterministic structural validation (final authority)
# --------------------------------------------------------------------------- #
def run_validator(module_path: Path, report_path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(module_path), "--report", str(report_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()
