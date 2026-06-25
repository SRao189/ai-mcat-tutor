from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]

SOURCE_FILE = PROJECT_ROOT / "wiki" / "oxidation-reduction.md"
CANDIDATE_FILE = ROOT / "output" / "candidate-module.json"
AUDIT_FILE = ROOT / "output" / "phi-audit.json"

PATCH_FILE = ROOT / "output" / "qwen-enrichment-patch.json"
ENRICHED_FILE = ROOT / "output" / "qwen-enriched-module.json"
PERFORMANCE_FILE = ROOT / "logs" / "qwen-enrichment-performance.json"
VALIDATION_FILE = ROOT / "logs" / "qwen-enrichment-validation.json"
RAW_FILE = ROOT / "logs" / "qwen-enrichment-raw-response.txt"

# Preflight scratch artifacts (kept separate so a dry-run never clobbers real outputs).
PREFLIGHT_ENRICHED = ROOT / "logs" / "qwen-enrichment-preflight-enriched.json"
PREFLIGHT_VALIDATION = ROOT / "logs" / "qwen-enrichment-preflight-validation.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS = "http://localhost:11434/api/tags"

MODEL = "qwen3:4b"
GENERATION_TIMEOUT = 1200   # overall cap (seconds)
# Socket read timeout. Must cover cold-load + prompt prefill before the FIRST
# streamed token arrives (no bytes flow during prefill), so it is generous.
# Once tokens flow, gaps are tiny, so this also doubles as a mid-stream stall guard.
STALL_TIMEOUT = 300
HEARTBEAT_INTERVAL = 30     # seconds between liveness messages


def build_patch_schema(section_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "section_updates": {
                "type": "array",
                "maxItems": 2,
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
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "minLength": 1},
                        "answer": {"type": "string", "minLength": 1},
                        "explanation": {"type": "string", "minLength": 1},
                        "sourceRefs": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                        "reviewTarget": {"type": "string", "enum": section_ids},
                    },
                    "required": [
                        "question",
                        "answer",
                        "explanation",
                        "sourceRefs",
                        "reviewTarget",
                    ],
                    "additionalProperties": False,
                },
            },
            "reason": {"type": "string", "minLength": 1},
        },
        "required": ["section_updates", "practice_question_additions", "reason"],
        "additionalProperties": False,
    }


def apply_patch(
    candidate: dict[str, Any],
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Pure additive merge. Never deletes or replaces existing content.

    Returns a dict with the enriched module plus accounting of what was
    applied and what was rejected. No I/O — so preflight can exercise the
    exact same code path with a synthetic patch.
    """
    enriched: dict[str, Any] = json.loads(json.dumps(candidate, ensure_ascii=False))

    sections_by_id = {
        section["id"]: section
        for section in enriched.get("sections", [])
        if isinstance(section, dict) and section.get("id")
    }

    applied_updates = 0
    rejected_updates: list[str] = []

    for update in patch.get("section_updates", []):
        section_id = update.get("section_id")
        addition = str(update.get("append_text", "")).strip()

        if section_id not in sections_by_id:
            rejected_updates.append(f"unknown_section_id:{section_id}")
            continue

        if addition:
            sections_by_id[section_id]["content"] += "\n\n" + addition
            applied_updates += 1

    existing_questions = {
        item.get("question")
        for item in enriched.get("practiceQuestions", [])
        if isinstance(item, dict)
    }

    added_questions = 0
    rejected_questions: list[str] = []

    for question in patch.get("practice_question_additions", []):
        review_target = question.get("reviewTarget")
        question_text = question.get("question")

        if review_target not in sections_by_id:
            rejected_questions.append(f"unknown_review_target:{review_target}")
            continue

        if question_text in existing_questions:
            rejected_questions.append(f"duplicate_question:{question_text}")
            continue

        enriched.setdefault("practiceQuestions", []).append(question)
        existing_questions.add(question_text)
        added_questions += 1

    return {
        "enriched": enriched,
        "applied_updates": applied_updates,
        "added_questions": added_questions,
        "rejected_updates": rejected_updates,
        "rejected_questions": rejected_questions,
    }


def run_validator(path: Path, report: Path = VALIDATION_FILE) -> subprocess.CompletedProcess[str]:
    validator = PROJECT_ROOT / "scripts" / "validate-module.py"
    return subprocess.run(
        [sys.executable, str(validator), str(path), "--report", str(report)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def model_available(model: str) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=15) as response:
            tags = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  Could not query Ollama tags: {exc}")
        return False

    names = {entry.get("name") for entry in tags.get("models", [])}
    return model in names


def canary(model: str) -> bool:
    """Tiny generation to confirm the model loads and responds before the long call."""
    payload = {
        "model": model,
        "prompt": 'Reply with the JSON object {"ok": true} and nothing else.',
        "stream": False,
        "think": False,
        "format": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
        "keep_alive": "5m",  # keep warm for the real call that immediately follows
        "options": {"temperature": 0, "seed": 42, "num_predict": 16},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            outer = json.loads(response.read().decode("utf-8", errors="replace"))
        parsed = json.loads(outer.get("response", "{}"))
        return parsed.get("ok") is True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  Canary failed: {exc}")
        return False


def unload_model(model: str) -> None:
    try:
        subprocess.run(
            ["ollama", "stop", model],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        print(f"Unloaded model: {model}")
    except Exception as exc:  # noqa: BLE001 - cleanup must never raise
        print(f"Model unload skipped: {exc}")


def preflight(
    candidate: dict[str, Any],
    section_ids: list[str],
    schema: dict[str, Any],
) -> bool:
    print("=== PREFLIGHT ===")

    # 1. Paths.
    missing = [str(p) for p in (SOURCE_FILE, CANDIDATE_FILE, AUDIT_FILE) if not p.exists()]
    if missing:
        print("  [1] FAIL paths missing: " + ", ".join(missing))
        return False
    if not (PROJECT_ROOT / "scripts" / "validate-module.py").exists():
        print("  [1] FAIL validator script not found")
        return False
    print("  [1] OK   all input paths and validator present")

    # 2. Generated-output schema is well-formed.
    try:
        json.dumps(schema)
        try:
            import jsonschema  # type: ignore

            jsonschema.Draft202012Validator.check_schema(schema)
            print("  [2] OK   patch schema valid (jsonschema)")
        except ImportError:
            print("  [2] OK   patch schema serializes (jsonschema not installed; deep check skipped)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [2] FAIL patch schema invalid: {exc}")
        return False

    # 3. Allowed section IDs.
    if not section_ids:
        print("  [3] FAIL no section IDs")
        return False
    print(f"  [3] OK   allowed section IDs: {section_ids}")

    # 4. Merge logic against a synthetic patch.
    synthetic = {
        "section_updates": [
            {"section_id": section_ids[0], "append_text": "Synthetic preflight clarification."}
        ],
        "practice_question_additions": [
            {
                "question": "Synthetic preflight question?",
                "answer": "Synthetic answer.",
                "explanation": "Synthetic explanation.",
                "sourceRefs": ["wiki/oxidation-reduction"],
                "reviewTarget": section_ids[0],
            }
        ],
        "reason": "Preflight test",
    }
    # Also confirm the merger rejects bad IDs and cannot delete content.
    bad = apply_patch(candidate, {"section_updates": [{"section_id": "practiceQuestions", "append_text": "x"}], "practice_question_additions": [], "reason": "x"})
    if bad["applied_updates"] != 0 or not bad["rejected_updates"]:
        print("  [4] FAIL merger accepted an invalid section ID")
        return False
    merged = apply_patch(candidate, synthetic)
    orig_sections = len(candidate.get("sections", []))
    orig_questions = len(candidate.get("practiceQuestions", []))
    if (
        merged["applied_updates"] != 1
        or merged["added_questions"] != 1
        or merged["rejected_updates"]
        or merged["rejected_questions"]
        or len(merged["enriched"].get("sections", [])) != orig_sections
        or len(merged["enriched"].get("practiceQuestions", [])) != orig_questions + 1
    ):
        print(f"  [4] FAIL synthetic merge unexpected: {merged}")
        return False
    print("  [4] OK   synthetic patch merges additively; bad IDs rejected; no deletions")

    # 5. Validator path works on the merged synthetic module.
    PREFLIGHT_ENRICHED.write_text(
        json.dumps(merged["enriched"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    result = run_validator(PREFLIGHT_ENRICHED, report=PREFLIGHT_VALIDATION)
    if result.returncode != 0:
        print(f"  [5] FAIL validator rejected synthetic module:\n{result.stdout}\n{result.stderr}")
        return False
    print("  [5] OK   validator accepts synthetic enriched module")

    # 6. Model present + responsive.
    if not model_available(MODEL):
        print(f"  [6] FAIL model {MODEL} not installed")
        return False
    print(f"  [6] ..   {MODEL} installed; running canary (loads model)...")
    if not canary(MODEL):
        print(f"  [6] FAIL {MODEL} canary did not return valid JSON")
        return False
    print(f"  [6] OK   {MODEL} canary responded")

    # 7. Stage + timeout.
    print(
        f"  [7] OK   next stage: GENERATE enrichment patch with {MODEL} "
        f"(stall timeout {STALL_TIMEOUT}s/token, overall cap {GENERATION_TIMEOUT}s)"
    )
    print("=== PREFLIGHT PASSED ===\n")
    return True


def stream_generate(payload: dict[str, Any]) -> tuple[str, dict[str, Any], float]:
    """Stream tokens from Ollama, emitting a heartbeat at least every 30s.

    Raises on stall (no token for STALL_TIMEOUT) or overall timeout.
    """
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    state = {"tokens": 0, "last_token": time.perf_counter(), "stage": "LOADING_MODEL"}
    lock = threading.Lock()
    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(HEARTBEAT_INTERVAL):
            with lock:
                toks, last, stage = state["tokens"], state["last_token"], state["stage"]
            idle = time.perf_counter() - last
            if toks == 0:
                status = "loading/prefill, no tokens yet (normal)"
            elif idle < HEARTBEAT_INTERVAL:
                status = "running"
            else:
                status = f"STALLED (no token {idle:.0f}s)"
            print(f"[{time.strftime('%H:%M:%S')}] {MODEL} {stage} - {toks} tokens received, {status}")

    raw_parts: list[str] = []
    meta: dict[str, Any] = {}
    started = time.perf_counter()
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()

    try:
        with urllib.request.urlopen(request, timeout=STALL_TIMEOUT) as response:
            with lock:
                state["stage"] = "GENERATING"
            for line in response:
                if not line.strip():
                    continue
                chunk = json.loads(line.decode("utf-8", errors="replace"))
                piece = chunk.get("response", "")
                if piece:
                    raw_parts.append(piece)
                    with lock:
                        state["tokens"] += 1
                        state["last_token"] = time.perf_counter()
                if chunk.get("done"):
                    meta = chunk
                    break
                if time.perf_counter() - started > GENERATION_TIMEOUT:
                    raise TimeoutError(f"exceeded overall generation timeout ({GENERATION_TIMEOUT}s)")
    finally:
        stop.set()
        thread.join(timeout=1)

    elapsed = time.perf_counter() - started
    return "".join(raw_parts).strip(), meta, elapsed


def write_failure_report(stage: str, message: str, elapsed: float) -> None:
    report = {
        "model": MODEL,
        "stage": stage,
        "status": "failed",
        "error": message,
        "elapsed_seconds": round(elapsed, 3),
    }
    PERFORMANCE_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Failure report saved: {PERFORMANCE_FILE}")


def main() -> int:
    required = [SOURCE_FILE, CANDIDATE_FILE, AUDIT_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("Missing required files:")
        for path in missing:
            print(f"- {path}")
        return 2

    source = SOURCE_FILE.read_text(encoding="utf-8-sig")
    candidate = json.loads(CANDIDATE_FILE.read_text(encoding="utf-8-sig"))
    audit = json.loads(AUDIT_FILE.read_text(encoding="utf-8-sig"))

    section_ids = [
        section["id"]
        for section in candidate.get("sections", [])
        if isinstance(section, dict) and section.get("id")
    ]
    if not section_ids:
        print("Candidate contains no usable section IDs.")
        return 2

    schema = build_patch_schema(section_ids)

    if not preflight(candidate, section_ids, schema):
        print("Preflight failed — long model call NOT started.")
        return 2

    prompt = f"""
Create a small additive enrichment patch for an MCAT lesson.

Use only the supplied source article as factual authority.

Your allowed actions:
- Append one short clarification to an existing section.
- Add one or two application-level practice questions.

Your forbidden actions:
- Do not rewrite the complete lesson.
- Do not delete or replace existing content.
- Do not create new section IDs.
- Do not use "practiceQuestions" as a section ID.
- Do not introduce outside facts.
- Do not add generic filler.
- Do not place SOURCE GAP in lesson prose.

Useful audit goals:
- Clarify why oxidation and reduction form a coupled redox pair,
  but only when the source supports that clarification.
- Add application-level assessment depth using examples already
  present in the source.

Valid section IDs:
{json.dumps(section_ids, indent=2)}

SOURCE ARTICLE START
{source}
SOURCE ARTICLE END

CURRENT MODULE START
{json.dumps(candidate, ensure_ascii=False)}
CURRENT MODULE END

AUDIT START
{json.dumps(audit, ensure_ascii=False)}
AUDIT END
""".strip()

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "think": False,
        "format": schema,
        "keep_alive": 0,
        "options": {"temperature": 0, "seed": 42, "num_ctx": 8192},
    }

    print(f"Source characters: {len(source)}")
    print(f"Valid section IDs: {section_ids}")
    print("STAGE: GENERATE - Qwen surgical enrichment started.\n")

    elapsed = 0.0
    try:
        raw, meta, elapsed = stream_generate(payload)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        write_failure_report("generate", str(exc), elapsed)
        unload_model(MODEL)
        return 1

    RAW_FILE.write_text(raw, encoding="utf-8")
    print(f"\nGeneration complete in {elapsed:.3f}s ({meta.get('eval_count')} eval tokens).")

    try:
        patch = json.loads(raw)
    except json.JSONDecodeError as exc:
        write_failure_report("parse", f"patch not valid JSON: {exc}", elapsed)
        unload_model(MODEL)
        print(f"Raw response: {RAW_FILE}")
        return 1

    PATCH_FILE.write_text(json.dumps(patch, indent=2, ensure_ascii=False), encoding="utf-8")

    merged = apply_patch(candidate, patch)
    enriched = merged["enriched"]
    applied_updates = merged["applied_updates"]
    added_questions = merged["added_questions"]
    rejected_updates = merged["rejected_updates"]
    rejected_questions = merged["rejected_questions"]

    ENRICHED_FILE.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")

    validation = run_validator(ENRICHED_FILE)
    schema_valid = validation.returncode == 0
    improvement_detected = applied_updates > 0 or added_questions > 0
    accepted = (
        schema_valid
        and improvement_detected
        and not rejected_updates
        and not rejected_questions
    )

    report = {
        "model": MODEL,
        "stage": "complete",
        "status": "ok",
        "elapsed_seconds": round(elapsed, 3),
        "schema_valid": schema_valid,
        "improvement_detected": improvement_detected,
        "accepted": accepted,
        "section_updates_applied": applied_updates,
        "practice_questions_added": added_questions,
        "rejected_updates": rejected_updates,
        "rejected_questions": rejected_questions,
        "original_practice_questions": len(candidate.get("practiceQuestions", [])),
        "enriched_practice_questions": len(enriched.get("practiceQuestions", [])),
        "prompt_eval_count": meta.get("prompt_eval_count"),
        "eval_count": meta.get("eval_count"),
        "validator_stdout": validation.stdout.strip(),
        "validator_stderr": validation.stderr.strip(),
    }
    PERFORMANCE_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    unload_model(MODEL)

    print()
    print(f"Elapsed seconds: {elapsed:.3f}")
    print(f"Section updates applied: {applied_updates}")
    print(f"Practice questions added: {added_questions}")
    print(f"Rejected updates: {rejected_updates}")
    print(f"Rejected questions: {rejected_questions}")
    print(f"Schema valid: {schema_valid}")
    print(f"Improvement detected: {improvement_detected}")
    print(f"Accepted: {accepted}")
    print(f"Patch: {PATCH_FILE}")
    print(f"Enriched module: {ENRICHED_FILE}")
    print(f"Performance report: {PERFORMANCE_FILE}")

    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
