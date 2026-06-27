#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path


def main() -> None:
    source_dir = Path("course-data")
    output_path = Path("app/course-data.js")

    modules = []

    for path in sorted(source_dir.glob("module-*.json")):
        report_path = Path("validation") / f"{path.stem}-report.json"

        if not report_path.exists():
            print(f"Skipping unvalidated module: {path}")
            continue

        try:
            report = json.loads(
                report_path.read_text(encoding="utf-8-sig")
            )
        except json.JSONDecodeError:
            print(f"Skipping module with malformed report: {path}")
            continue

        if not isinstance(report, dict) or not report.get("valid"):
            print(f"Skipping invalid module: {path}")
            continue

        module_bytes = path.read_bytes()
        actual_hash = "sha256:" + hashlib.sha256(module_bytes).hexdigest()
        recorded_hash = report.get("moduleHash")

        if not recorded_hash:
            print(f"Skipping module with no validated hash: {path}")
            continue

        if recorded_hash != actual_hash:
            print(f"Skipping stale module (hash mismatch): {path}")
            continue

        module = json.loads(module_bytes.decode("utf-8-sig"))

        modules.append(module)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        "window.MCAT_COURSE_DATA = "
        + json.dumps(modules, indent=2, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )

    print(f"Wrote: {output_path}")
    print(f"Validated modules included: {len(modules)}")


if __name__ == "__main__":
    main()
