from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"

CONTEXT_FILE = INPUT_DIR / "context.md"
SCHEMA_FILE = INPUT_DIR / "module.schema.json"
CANDIDATE_FILE = OUTPUT_DIR / "candidate-module.json"
RAW_RESPONSE_FILE = LOG_DIR / "raw-model-response.txt"
RUN_REPORT_FILE = LOG_DIR / "generation-report.json"
VALIDATION_REPORT_FILE = LOG_DIR / "candidate-validation.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:4b"


def call_ollama(
    model: str,
    context_text: str,
    schema: dict[str, Any],
    timeout_seconds: int = 600,
) -> tuple[dict[str, Any], float]:
    prompt = f"""
You are generating one complete MCAT tutoring lesson module.

Your output will be validated against the supplied JSON schema.

Grounding rules:
- Use only information present in the context packet.
- Do not add outside factual knowledge.
- Preserve uncertainty.
- Where support is missing, write SOURCE GAP rather than inventing information.
- Follow all source-reference requirements described in the packet.

Pedagogy rules:
- Explain concepts progressively and clearly.
- Use an approachable Khan Academy-style teaching voice.
- Connect equations to conceptual meaning.
- Include worked reasoning where the schema permits it.
- Make assessment questions test concepts actually taught in the lesson.
- Avoid unnecessary repetition.

Output rules:
- Return only one JSON object.
- Match the supplied schema exactly.
- Include every required field.
- Do not use Markdown code fences.
- Do not include commentary outside the JSON.

CONTEXT PACKET START
{context_text}
CONTEXT PACKET END
""".strip()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": schema,
        "keep_alive": 0,
        "options": {
            "temperature": 0,
            "seed": 42,
            "num_ctx": 16384,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()

    with urllib.request.urlopen(
        request,
        timeout=timeout_seconds,
    ) as response:
        outer = json.loads(
            response.read().decode("utf-8", errors="replace")
        )

    elapsed = time.perf_counter() - started
    return outer, elapsed


def run_validator(candidate: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT.parents[2] / "scripts" / "validate-module.py"),
            str(candidate),
            "--report",
            str(VALIDATION_REPORT_FILE),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONTEXT_FILE.exists():
        print(f"Missing context file: {CONTEXT_FILE}")
        return 2

    if not SCHEMA_FILE.exists():
        print(f"Missing schema file: {SCHEMA_FILE}")
        return 2

    context_text = CONTEXT_FILE.read_text(encoding="utf-8-sig")
    schema = json.loads(
        SCHEMA_FILE.read_text(encoding="utf-8-sig")
    )

    print(f"Model: {model}")
    print(f"Context characters: {len(context_text)}")
    print("Generation started. This may take several minutes.")

    try:
        outer, elapsed = call_ollama(
            model=model,
            context_text=context_text,
            schema=schema,
        )
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Generation failed: {exc}")
        return 1

    raw_output = (outer.get("response") or "").strip()
    RAW_RESPONSE_FILE.write_text(raw_output, encoding="utf-8")

    parse_success = False
    parse_error = None
    candidate: dict[str, Any] | None = None

    try:
        candidate = json.loads(raw_output)
        parse_success = isinstance(candidate, dict)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)

    if not parse_success or candidate is None:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "elapsed_seconds": round(elapsed, 3),
            "parse_success": False,
            "parse_error": parse_error,
            "validation_exit_code": None,
            "validation_success": False,
            "done_reason": outer.get("done_reason"),
            "total_duration_ns": outer.get("total_duration"),
            "load_duration_ns": outer.get("load_duration"),
            "prompt_eval_count": outer.get("prompt_eval_count"),
            "eval_count": outer.get("eval_count"),
        }

        RUN_REPORT_FILE.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        print("Model output was not valid JSON.")
        print(f"Raw response saved to: {RAW_RESPONSE_FILE}")
        return 1

    CANDIDATE_FILE.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Candidate written: {CANDIDATE_FILE}")

    validation = run_validator(CANDIDATE_FILE)
    validation_success = validation.returncode == 0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "elapsed_seconds": round(elapsed, 3),
        "parse_success": True,
        "parse_error": None,
        "validation_exit_code": validation.returncode,
        "validation_success": validation_success,
        "validator_stdout": validation.stdout.strip(),
        "validator_stderr": validation.stderr.strip(),
        "done_reason": outer.get("done_reason"),
        "total_duration_ns": outer.get("total_duration"),
        "load_duration_ns": outer.get("load_duration"),
        "prompt_eval_count": outer.get("prompt_eval_count"),
        "prompt_eval_duration_ns": outer.get("prompt_eval_duration"),
        "eval_count": outer.get("eval_count"),
        "eval_duration_ns": outer.get("eval_duration"),
    }

    RUN_REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Elapsed seconds: {elapsed:.3f}")
    print(f"JSON parse success: {parse_success}")
    print(f"Validation success: {validation_success}")
    print(f"Validation exit code: {validation.returncode}")

    if validation.stdout.strip():
        print()
        print("Validator output:")
        print(validation.stdout.strip())

    if validation.stderr.strip():
        print()
        print("Validator errors:")
        print(validation.stderr.strip())

    print()
    print(f"Generation report: {RUN_REPORT_FILE}")
    print(f"Validation report: {VALIDATION_REPORT_FILE}")

    return 0 if validation_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
