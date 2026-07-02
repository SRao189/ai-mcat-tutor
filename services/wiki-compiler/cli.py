"""CLI wrapper for wiki compiler ingest, query, and lint operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wiki_compiler import ingest_concept, initialize_wiki, lint_wiki, query_wiki  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operate the v2 verified wiki.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    ingest = sub.add_parser("ingest")
    ingest.add_argument("concept_json", type=Path)
    query = sub.add_parser("query")
    query.add_argument("text")
    sub.add_parser("lint")
    args = parser.parse_args(argv)

    if args.command == "init":
        print(initialize_wiki(args.repo_root))
    elif args.command == "ingest":
        payload = json.loads(args.concept_json.read_text(encoding="utf-8"))
        print(json.dumps(ingest_concept(args.repo_root, payload), indent=2, sort_keys=True))
    elif args.command == "query":
        print(json.dumps(query_wiki(args.repo_root, args.text), indent=2, sort_keys=True))
    elif args.command == "lint":
        print(json.dumps(lint_wiki(args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
