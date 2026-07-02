"""Operational Karpathy-style wiki compiler for verified concept pages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from council_boundary import CouncilVerificationBoundary


def initialize_wiki(repo_root: Path | str) -> Path:
    root = Path(repo_root).resolve()
    wiki_root = root / "knowledge" / "wiki"
    concepts = wiki_root / "concepts"
    concepts.mkdir(parents=True, exist_ok=True)
    index = wiki_root / "index.md"
    log = wiki_root / "log.md"
    if not index.exists():
        index.write_text("# MCAT Tutor Verified Wiki\n\nNo verified concepts yet.\n", encoding="utf-8")
    if not log.exists():
        log.write_text("# Wiki Compiler Log\n\n", encoding="utf-8")
    return wiki_root


def ingest_concept(repo_root: Path | str, concept_page: dict[str, Any]) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    wiki_root = initialize_wiki(root)
    verified_page, trace = CouncilVerificationBoundary(root).verify_concept_page(concept_page)
    concept_id = verified_page["conceptId"]
    concept_path = wiki_root / "concepts" / f"{concept_id}.json"
    trace_path = wiki_root / "concepts" / f"{concept_id}.verification.json"
    markdown_path = wiki_root / "concepts" / f"{concept_id}.md"
    _write_json(concept_path, verified_page)
    _write_json(trace_path, trace)
    markdown_path.write_text(_concept_markdown(verified_page), encoding="utf-8", newline="\n")
    _rewrite_index(wiki_root)
    _append_log(wiki_root, f"ingest {concept_id} verification={verified_page['learnerEligible']}")
    return verified_page


def query_wiki(repo_root: Path | str, query: str) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    wiki_root = initialize_wiki(root)
    query_tokens = _tokens(query)
    matches: list[dict[str, Any]] = []
    for concept_file in sorted((wiki_root / "concepts").glob("*.json")):
        if concept_file.name.endswith(".verification.json"):
            continue
        page = json.loads(concept_file.read_text(encoding="utf-8"))
        haystack = " ".join(
            [page.get("conceptId", ""), page.get("title", ""), page.get("summary", "")]
            + [claim.get("text", "") for claim in page.get("claims", [])]
        )
        score = len(query_tokens & _tokens(haystack))
        if score:
            matches.append({"conceptId": page["conceptId"], "title": page["title"], "score": score})
    return sorted(matches, key=lambda item: (-item["score"], item["conceptId"]))


def lint_wiki(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    wiki_root = initialize_wiki(root)
    errors: list[str] = []
    concept_count = 0
    for concept_file in sorted((wiki_root / "concepts").glob("*.json")):
        if concept_file.name.endswith(".verification.json"):
            continue
        concept_count += 1
        page = json.loads(concept_file.read_text(encoding="utf-8"))
        if not re.match(r"^[a-z0-9]+(\.[a-z0-9-]+)+$", page.get("conceptId", "")):
            errors.append(f"{concept_file.name}: invalid conceptId")
        for index, claim in enumerate(page.get("claims", [])):
            if claim.get("learnerEligible") and claim.get("verification") != "verified":
                errors.append(f"{concept_file.name}: claim {index} learner eligible without verification")
    return {"conceptCount": concept_count, "ok": not errors, "errors": errors}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _concept_markdown(page: dict[str, Any]) -> str:
    lines = [f"# {page['title']}", "", page.get("summary", ""), "", "## Claims", ""]
    for claim in page.get("claims", []):
        lines.append(
            f"- [{claim['verification']}; {claim['confidence']:.2f}] {claim['text']} "
            f"({claim['sourceId']} -> {claim['sourceSpan']})"
        )
    lines.extend(["", "## Related Concepts", ""])
    for related in page.get("relatedConcepts", []):
        lines.append(f"- {related}")
    return "\n".join(lines).strip() + "\n"


def _rewrite_index(wiki_root: Path) -> None:
    concept_files = [
        path
        for path in sorted((wiki_root / "concepts").glob("*.json"))
        if not path.name.endswith(".verification.json")
    ]
    lines = ["# MCAT Tutor Verified Wiki", ""]
    if not concept_files:
        lines.append("No verified concepts yet.")
    for path in concept_files:
        page = json.loads(path.read_text(encoding="utf-8"))
        marker = "learner-eligible" if page.get("learnerEligible") else "not learner-eligible"
        lines.append(f"- [{page['title']}](concepts/{path.stem}.md) - `{page['conceptId']}` - {marker}")
    (wiki_root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_log(wiki_root: Path, event: str) -> None:
    with (wiki_root / "log.md").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- {event}\n")


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(token) > 2}
