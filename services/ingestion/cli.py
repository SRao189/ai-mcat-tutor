"""CLI for deterministic v2 source ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .service import IngestionService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a source into knowledge/sources/<sourceId>.")
    parser.add_argument("source", type=Path, help="PDF, DOCX, Markdown, or text source file.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--provenance-kind", default="local-file")
    args = parser.parse_args(argv)
    manifest = IngestionService(args.repo_root).ingest(args.source, provenance={"kind": args.provenance_kind, "path": str(args.source.resolve())})
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
