#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path

import claim_support


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble validated MCAT modules into the app."
    )
    parser.add_argument(
        "--allow-unverified-citations",
        action="store_true",
        help="Escape hatch: ship modules whose Gate 2 citations are not "
        "verified. By default unverified-citation modules are skipped.",
    )
    parser.add_argument(
        "--require-claim-support",
        action="store_true",
        help="Gate 3 (opt-in): also skip modules with any deterministic claim "
        "failure or whose claimsVerified is not true.",
    )
    args = parser.parse_args()

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

        if not args.allow_unverified_citations and not report.get(
            "citationsVerified"
        ):
            print(f"Skipping module with unverified citations: {path}")
            continue

        module = json.loads(module_bytes.decode("utf-8-sig"))

        if args.require_claim_support:
            if report.get("claimFailCount", 0) > 0 or not report.get(
                "claimsVerified"
            ):
                print(f"Skipping module with unverified claim support: {path}")
                continue
            # source freshness: recompute the dependency hash from current
            # sources; a cited source edited after validation invalidates it.
            current = claim_support.source_dependency_hash(module, Path.cwd())
            if current != report.get("sourceDependencyHash"):
                print(f"Skipping module with changed source (Gate 3): {path}")
                continue

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
