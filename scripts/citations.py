#!/usr/bin/env python3
"""Deterministic citation resolver for Gate 2 (citation integrity).

No LLM. A structured citation points at a specific passage in a canonical
markdown source and carries a hash of that passage, so a changed source
invalidates the citation. Importable (validate-module.py / build-course.py have
hyphens and cannot be imported); the unit tests live in tests/test_citations.py.

Citation shape:
    {
      "sourceId": "wiki/thermodynamics.md#gibbs-free-energy-g",
      "quote": "A reaction is spontaneous when delta G is negative.",
      "passageHash": "sha256:<hex>"
    }
"""
import hashlib
import re
from pathlib import Path
from typing import Any

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

# Failure reason constants (kept stable so reports/tests can assert on them).
OK = ""
MALFORMED = "malformed"
SOURCE_MISSING = "source-missing"
ANCHOR_UNRESOLVED = "anchor-unresolved"
ANCHOR_AMBIGUOUS = "anchor-ambiguous"
HASH_MISMATCH = "hash-mismatch"
QUOTE_NOT_FOUND = "quote-not-found"


def slugify(heading_text: str) -> str:
    """Our slug rule (GitHub-like, applied identically everywhere so the model,
    the migrator, and the validator always agree): lowercase, drop anything that
    is not a word char / space / hyphen, spaces -> hyphens."""
    s = heading_text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s


def normalize(text: str) -> str:
    """Collapse all whitespace so reformatting a source (re-wrapping, extra
    blank lines) does not change the hash, but real edits do."""
    return re.sub(r"\s+", " ", text).strip()


def parse_headings(md_text: str) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for i, line in enumerate(md_text.splitlines()):
        m = HEADING_RE.match(line)
        if m:
            headings.append(
                {
                    "slug": slugify(m.group(2)),
                    "depth": len(m.group(1)),
                    "line": i,
                }
            )
    return headings


def extract_passage(md_text: str, heading: dict[str, Any]) -> str:
    """Heading line through (but not including) the next heading of
    equal-or-higher level (depth <= this heading's depth)."""
    lines = md_text.splitlines()
    start = heading["line"]
    end = len(lines)
    for h in parse_headings(md_text):
        if h["line"] > start and h["depth"] <= heading["depth"]:
            end = h["line"]
            break
    return "\n".join(lines[start:end])


def passage_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def make_citation(repo_root: Path, source_id: str, quote: str) -> dict[str, str]:
    """Build a fully-formed citation (computes passageHash). Used by the
    migrator and by tests. Raises ValueError if the anchor does not resolve."""
    ok, reason, passage = _resolve(repo_root, source_id)
    if not ok:
        raise ValueError(f"cannot build citation for {source_id!r}: {reason}")
    return {
        "sourceId": source_id,
        "quote": quote,
        "passageHash": passage_hash(passage),
    }


def _resolve(repo_root: Path, source_id: str) -> tuple[bool, str, str]:
    """Resolve a sourceId to its passage text. Returns (ok, reason, passage)."""
    if "#" not in source_id:
        return False, MALFORMED, ""
    source_rel, anchor = source_id.split("#", 1)
    if not source_rel or not anchor:
        return False, MALFORMED, ""

    source_path = repo_root / source_rel
    if not source_path.exists():
        return False, SOURCE_MISSING, ""

    md_text = source_path.read_text(encoding="utf-8-sig")
    matches = [h for h in parse_headings(md_text) if h["slug"] == anchor]
    if not matches:
        return False, ANCHOR_UNRESOLVED, ""
    if len(matches) > 1:
        return False, ANCHOR_AMBIGUOUS, ""

    return True, OK, extract_passage(md_text, matches[0])


def verify_citation(citation: Any, repo_root: Path) -> tuple[bool, str]:
    """Deterministic Gate 2 check. Returns (ok, reason). reason is OK ("") on
    success or one of the constants above."""
    if not isinstance(citation, dict):
        return False, MALFORMED
    for key in ("sourceId", "quote", "passageHash"):
        value = citation.get(key)
        if not isinstance(value, str) or not value.strip():
            return False, MALFORMED

    ok, reason, passage = _resolve(repo_root, citation["sourceId"])
    if not ok:
        return False, reason

    if passage_hash(passage) != citation["passageHash"]:
        return False, HASH_MISMATCH

    if normalize(citation["quote"]) not in normalize(passage):
        return False, QUOTE_NOT_FOUND

    return True, OK


def is_structured(citation: Any) -> bool:
    """True for an object citation, False for a legacy string citation."""
    return isinstance(citation, dict)
