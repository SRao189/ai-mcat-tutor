#!/usr/bin/env python3
"""Deterministic migration of legacy string citations to Gate 2 structured form.

A legacy ref looks like "wiki/course/context/module-1-context.md:22-24" (line
range) or a bare filename. We read the referenced lines, take the text as a
candidate quote, then locate it in canonical wiki/*.md by normalized substring
search. If exactly one wiki passage contains it, we emit a structured citation
{sourceId, quote, passageHash}. Anything that does not resolve uniquely goes to a
review list and is NEVER auto-verified.

No LLM. Non-destructive by default (writes <stem>.migrated.json); --in-place to
overwrite. Run: python scripts/migrate-citations.py course-data/module-1.json
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citations  # noqa: E402

LINESPEC_RE = re.compile(r"^(\d+)(?:-(\d+))?$")

CITED_COLLECTIONS = [
    "sections",
    "equations",
    "workedExamples",
    "checks",
    "practiceQuestions",
]


def parse_ref(ref: str) -> tuple[str, int | None, int | None]:
    """('path:start-end' | 'path:line' | 'path') -> (path, start, end)."""
    if ":" in ref:
        head, tail = ref.rsplit(":", 1)
        m = LINESPEC_RE.match(tail)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else start
            return head, start, end
    return ref, None, None


def extract_quote(repo_root: Path, path: str, start: int, end: int) -> str | None:
    source = repo_root / path
    if not source.exists():
        return None
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    # legacy refs are 1-indexed line numbers
    span = lines[start - 1:end]
    text = "\n".join(span).strip()
    return text or None


def find_unique_passage(
    quote: str, wiki_dir: Path, repo_root: Path
) -> tuple[str, dict[str, Any]] | None:
    nq = citations.normalize(quote)
    if not nq:
        return None
    matches: list[tuple[str, dict[str, Any]]] = []
    for md in sorted(wiki_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8-sig")
        for heading in citations.parse_headings(text):
            passage = citations.extract_passage(text, heading)
            if nq in citations.normalize(passage):
                rel = md.relative_to(repo_root).as_posix()
                matches.append((rel, heading))
    if not matches:
        return None
    # An ancestor heading's passage contains all its children, so prefer the
    # deepest (most specific) match. Unique only if one deepest match.
    max_depth = max(h["depth"] for _, h in matches)
    deepest = [m for m in matches if m[1]["depth"] == max_depth]
    return deepest[0] if len(deepest) == 1 else None


def convert_ref(
    repo_root: Path, wiki_dir: Path, ref: Any
) -> tuple[dict[str, str] | None, str]:
    """Returns (citation, reason). citation is None when it cannot be resolved
    uniquely; reason explains why (for the review list)."""
    if citations.is_structured(ref):
        # Fresh generation emits {sourceId, quote} without a hash; stamp it
        # deterministically (the model cannot compute a sha256).
        has_hash = isinstance(ref.get("passageHash"), str) and ref["passageHash"]
        if has_hash:
            return ref, "already-structured"
        source_id, quote = ref.get("sourceId"), ref.get("quote")
        if not (isinstance(source_id, str) and isinstance(quote, str)):
            return None, "incomplete-citation"
        ok, _, _ = citations._resolve(repo_root, source_id)
        if not ok:
            return None, "anchor-unresolved"
        return citations.make_citation(repo_root, source_id, quote), "stamped"
    if not isinstance(ref, str):
        return None, "not-a-string"

    path, start, end = parse_ref(ref)
    if start is None:
        return None, "no-line-range"

    quote = extract_quote(repo_root, path, start, end)
    if quote is None:
        return None, "lines-unreadable"

    found = find_unique_passage(quote, wiki_dir, repo_root)
    if found is None:
        return None, "no-unique-wiki-passage"

    source_rel, heading = found
    source_id = f"{source_rel}#{heading['slug']}"
    return citations.make_citation(repo_root, source_id, quote), "ok"


def _convert_list(repo_root, wiki_dir, refs, location, review):
    out = []
    for index, ref in enumerate(refs or []):
        cite, reason = convert_ref(repo_root, wiki_dir, ref)
        if cite is None:
            review.append({"location": f"{location}[{index}]",
                           "ref": ref, "reason": reason})
            out.append(ref)  # leave legacy ref in place for human fixup
        else:
            out.append(cite)
    return out


def migrate_module(
    data: dict[str, Any], repo_root: Path, wiki_dir: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    review: list[dict[str, Any]] = []
    new = dict(data)
    new["sourceRefs"] = _convert_list(
        repo_root, wiki_dir, data.get("sourceRefs"), "sourceRefs", review)
    for collection in CITED_COLLECTIONS:
        items = data.get(collection)
        if not isinstance(items, list):
            continue
        new_items = []
        for i, item in enumerate(items):
            if isinstance(item, dict) and "sourceRefs" in item:
                item = dict(item)
                item["sourceRefs"] = _convert_list(
                    repo_root, wiki_dir, item.get("sourceRefs"),
                    f"{collection}[{i}].sourceRefs", review)
            new_items.append(item)
        new[collection] = new_items
    return new, review


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="Module JSON to migrate.")
    parser.add_argument("--wiki-dir", default="wiki",
                        help="Canonical source dir (default: wiki).")
    parser.add_argument("--in-place", action="store_true",
                        help="Overwrite the module instead of writing alongside.")
    args = parser.parse_args()

    repo_root = Path.cwd()
    module_path = Path(args.module)
    data = json.loads(module_path.read_text(encoding="utf-8-sig"))

    new, review = migrate_module(data, repo_root, repo_root / args.wiki_dir)

    if args.in_place:
        out_path = module_path
        review_path = module_path.with_name(
            f"{module_path.stem}-migration-review.json")
    else:
        # Stage under migrated/ so build-course's module-*.json glob ignores it.
        out_dir = module_path.parent / "migrated"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / module_path.name
        review_path = out_dir / f"{module_path.stem}-migration-review.json"

    out_path.write_text(
        json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote: {out_path}")
    print(f"Citations needing review: {len(review)}")
    for entry in review:
        print(f"  REVIEW {entry['location']}: {entry['reason']} -> {entry['ref']}")

    if review:
        review_path.write_text(
            json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Review list: {review_path}")


if __name__ == "__main__":
    main()
