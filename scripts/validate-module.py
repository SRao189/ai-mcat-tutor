#!/usr/bin/env python3

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = [
    "id",
    "title",
    "objectives",
    "sections",
    "equations",
    "workedExamples",
    "checks",
    "practiceQuestions",
    "sourceRefs",
    "sourceGaps",
]


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_source_refs(
    item: dict[str, Any],
    location: str,
    errors: list[str],
) -> None:
    refs = item.get("sourceRefs")

    if not isinstance(refs, list) or not refs:
        errors.append(
            f"{location}: sourceRefs must be a non-empty list."
        )
        return

    for index, ref in enumerate(refs):
        if not is_nonempty_string(ref):
            errors.append(
                f"{location}.sourceRefs[{index}] must be a non-empty string."
            )


def validate_question(
    item: Any,
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(item, dict):
        errors.append(f"{location} must be an object.")
        return

    required = [
        "question",
        "answer",
        "explanation",
        "sourceRefs",
        "reviewTarget",
    ]

    for key in required:
        if key not in item:
            errors.append(f"{location}: missing `{key}`.")

    for key in [
        "question",
        "answer",
        "explanation",
        "reviewTarget",
    ]:
        if key in item and not is_nonempty_string(item[key]):
            errors.append(
                f"{location}.{key} must be a non-empty string."
            )

    validate_source_refs(item, location, errors)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate one generated MCAT module JSON file."
    )

    parser.add_argument(
        "module",
        help="Path to the module JSON file.",
    )

    parser.add_argument(
        "--report",
        help="Optional output report JSON path.",
    )

    args = parser.parse_args()

    module_path = Path(args.module)

    if not module_path.exists():
        raise SystemExit(f"Module file does not exist: {module_path}")

    errors: list[str] = []
    warnings: list[str] = []

    module_bytes = module_path.read_bytes()
    module_hash = "sha256:" + hashlib.sha256(module_bytes).hexdigest()

    try:
        data = json.loads(
            module_bytes.decode("utf-8-sig")
        )
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON: {exc}")
        data = {}

    if not isinstance(data, dict):
        errors.append("Top-level JSON value must be an object.")
        data = {}

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"Missing top-level field: `{key}`.")

    if "id" in data and not is_nonempty_string(data["id"]):
        errors.append("`id` must be a non-empty string.")

    if "title" in data and not is_nonempty_string(data["title"]):
        errors.append("`title` must be a non-empty string.")

    for field in [
        "objectives",
        "sections",
        "equations",
        "workedExamples",
        "checks",
        "practiceQuestions",
        "sourceRefs",
        "sourceGaps",
    ]:
        if field in data and not isinstance(data[field], list):
            errors.append(f"`{field}` must be a list.")

    for index, section in enumerate(data.get("sections", [])):
        location = f"sections[{index}]"

        if not isinstance(section, dict):
            errors.append(f"{location} must be an object.")
            continue

        for key in ["id", "title", "content"]:
            if not is_nonempty_string(section.get(key)):
                errors.append(
                    f"{location}.{key} must be a non-empty string."
                )

        validate_source_refs(section, location, errors)

    for index, equation in enumerate(data.get("equations", [])):
        location = f"equations[{index}]"

        if not isinstance(equation, dict):
            errors.append(f"{location} must be an object.")
            continue

        for key in ["expression", "meaning"]:
            if not is_nonempty_string(equation.get(key)):
                errors.append(
                    f"{location}.{key} must be a non-empty string."
                )

        validate_source_refs(equation, location, errors)

    for index, example in enumerate(
        data.get("workedExamples", [])
    ):
        location = f"workedExamples[{index}]"

        if not isinstance(example, dict):
            errors.append(f"{location} must be an object.")
            continue

        for key in ["question", "answer"]:
            if not is_nonempty_string(example.get(key)):
                errors.append(
                    f"{location}.{key} must be a non-empty string."
                )

        steps = example.get("steps")

        if not isinstance(steps, list) or not steps:
            errors.append(
                f"{location}.steps must be a non-empty list."
            )

        validate_source_refs(example, location, errors)

    for field in ["checks", "practiceQuestions"]:
        for index, question in enumerate(data.get(field, [])):
            validate_question(
                question,
                f"{field}[{index}]",
                errors,
            )

    top_source_refs = data.get("sourceRefs", [])

    if isinstance(top_source_refs, list):
        if not top_source_refs:
            errors.append(
                "`sourceRefs` must contain at least one source."
            )

        for index, ref in enumerate(top_source_refs):
            if not is_nonempty_string(ref):
                errors.append(
                    f"sourceRefs[{index}] must be a non-empty string."
                )

    serialized = json.dumps(data, ensure_ascii=False).lower()

    suspicious_phrases = [
        "according to research",
        "studies show",
        "evidence-based",
        "the mcat always",
        "the mcat loves",
    ]

    for phrase in suspicious_phrases:
        if phrase in serialized:
            warnings.append(
                f"Potential unsupported generalization detected: `{phrase}`"
            )

    report = {
        "module": str(module_path),
        "moduleHash": module_hash,
        "validatedAt": datetime.now(timezone.utc).isoformat(),
        "valid": not errors,
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }

    report_path = (
        Path(args.report)
        if args.report
        else Path("validation") / f"{module_path.stem}-report.json"
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
