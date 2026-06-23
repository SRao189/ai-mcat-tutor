from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TASK_FILE = ROOT / "classification-tasks.json"
RESULT_FILE = ROOT / "results" / "classification-results-api-v2.jsonl"
OLLAMA_URL = "http://localhost:11434/api/generate"

TASK_TYPE_DEFINITIONS = {
    "source_extraction": (
        "Produce a factual claims list, fact sheet, or extracted source data."
    ),
    "lesson_generation": (
        "Produce a new lesson, teaching module, quiz, or educational JSON artifact."
    ),
    "schema_repair": (
        "Repair existing JSON or structured data so it passes a schema or validator."
    ),
    "code_edit": (
        "Modify executable source code such as Python, JavaScript, HTML, or CSS."
    ),
    "grounding_audit": (
        "Compare generated content with source material and report unsupported claims."
    ),
}

ALLOWED_TYPES = list(TASK_TYPE_DEFINITIONS)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "task_type": {
            "type": "string",
            "enum": ALLOWED_TYPES,
        },
        "reason": {
            "type": "string",
        },
    },
    "required": ["task_type", "reason"],
    "additionalProperties": False,
}


def call_ollama(
    model: str,
    task: str,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    definitions = "\n".join(
        f"- {name}: {description}"
        for name, description in TASK_TYPE_DEFINITIONS.items()
    )

    prompt = f"""
Classify the task below by its primary requested output.

Allowed task types and definitions:
{definitions}

Task:
"{task}"

Rules:
- Classify based on the final artifact requested.
- Do not classify based only on the first verb.
- JSON or structured-data repair is schema_repair.
- Editing Python, JavaScript, HTML, or CSS is code_edit.

Return:
- task_type: exactly one allowed task type
- reason: one short sentence
""".strip()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": OUTPUT_SCHEMA,
        "keep_alive": 0,
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            outer = json.loads(
                response.read().decode("utf-8", errors="replace")
            )

        elapsed = time.perf_counter() - started
        raw_model_output = (outer.get("response") or "").strip()

        parse_success = False
        task_type = None
        reason = None
        parse_error = None

        try:
            parsed = json.loads(raw_model_output)
            task_type = parsed.get("task_type")
            reason = parsed.get("reason")
            parse_success = True
        except (json.JSONDecodeError, AttributeError) as exc:
            parse_error = str(exc)

        return {
            "elapsed_seconds": round(elapsed, 3),
            "raw_output": raw_model_output,
            "parse_success": parse_success,
            "task_type": task_type,
            "reason": reason,
            "parse_error": parse_error,
            "stalled": False,
            "done_reason": outer.get("done_reason"),
            "total_duration_ns": outer.get("total_duration"),
            "load_duration_ns": outer.get("load_duration"),
            "prompt_eval_count": outer.get("prompt_eval_count"),
            "prompt_eval_duration_ns": outer.get("prompt_eval_duration"),
            "eval_count": outer.get("eval_count"),
            "eval_duration_ns": outer.get("eval_duration"),
        }

    except (urllib.error.URLError, TimeoutError) as exc:
        elapsed = time.perf_counter() - started

        return {
            "elapsed_seconds": round(elapsed, 3),
            "raw_output": "",
            "parse_success": False,
            "task_type": None,
            "reason": None,
            "parse_error": str(exc),
            "stalled": isinstance(exc, TimeoutError),
            "done_reason": None,
            "total_duration_ns": None,
            "load_duration_ns": None,
            "prompt_eval_count": None,
            "prompt_eval_duration_ns": None,
            "eval_count": None,
            "eval_duration_ns": None,
        }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python run-classification-benchmark.py MODEL")
        return 2

    model = sys.argv[1]

    with TASK_FILE.open("r", encoding="utf-8-sig") as handle:
        tasks = json.load(handle)

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    correct_count = 0
    parsed_count = 0
    stalled_count = 0
    total_seconds = 0.0

    for item in tasks:
        print(f"Running {model}: {item['id']}")

        result = call_ollama(model, item["task"])

        result.update(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "task_id": item["id"],
                "task": item["task"],
                "expected": item["expected"],
            }
        )

        result["correct"] = (
            result["parse_success"]
            and result["task_type"] == item["expected"]
        )

        correct_count += int(result["correct"])
        parsed_count += int(result["parse_success"])
        stalled_count += int(result["stalled"])
        total_seconds += result["elapsed_seconds"]

        with RESULT_FILE.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(result, ensure_ascii=False) + "\n"
            )

        print(
            f"  expected={item['expected']} "
            f"actual={result['task_type']} "
            f"parsed={result['parse_success']} "
            f"correct={result['correct']} "
            f"time={result['elapsed_seconds']}s"
        )

        if not result["parse_success"]:
            print(f"  raw={result['raw_output']!r}")
            print(f"  error={result['parse_error']}")

    task_count = len(tasks)

    print()
    print(f"Model: {model}")
    print(f"Accuracy: {correct_count}/{task_count}")
    print(f"JSON parse rate: {parsed_count}/{task_count}")
    print(f"Stalls: {stalled_count}/{task_count}")
    print(f"Average runtime: {total_seconds / task_count:.3f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
