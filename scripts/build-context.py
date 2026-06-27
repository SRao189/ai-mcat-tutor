#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path
from typing import Any


def normalize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).lower()


def extract_headings(markdown: str) -> list[str]:
    return [
        line.strip()
        for line in markdown.splitlines()
        if re.match(r"^#{1,6}\s+", line)
    ]


def extract_equation_lines(markdown: str) -> list[str]:
    equation_markers = (
        "Δ",
        "=",
        "ln",
        "log",
        "pH",
        "pKa",
        "Ka",
        "K'",
        "Q",
    )

    results: list[str] = []

    for line in markdown.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if any(marker in stripped for marker in equation_markers):
            if len(stripped) <= 240:
                results.append(stripped)

    return list(dict.fromkeys(results))


def get_node_id(node: dict[str, Any]) -> Any:
    return (
        node.get("id")
        or node.get("node_id")
        or node.get("key")
        or node.get("name")
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a compact source packet for one MCAT module."
    )

    parser.add_argument(
        "--topic",
        required=True,
        help="Topic name used to filter graph content.",
    )

    parser.add_argument(
        "--wiki-file",
        required=True,
        help="Primary wiki Markdown file.",
    )

    parser.add_argument(
        "--graph",
        default="wiki/.understand-anything/knowledge-graph.json",
        help="Knowledge graph JSON path.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output context Markdown path.",
    )

    parser.add_argument(
        "--keywords",
        nargs="*",
        default=[],
        help="Additional graph-filtering keywords.",
    )

    args = parser.parse_args()

    wiki_path = Path(args.wiki_file)
    graph_path = Path(args.graph)
    output_path = Path(args.output)

    if not wiki_path.exists():
        raise SystemExit(f"Wiki file does not exist: {wiki_path}")

    if not graph_path.exists():
        raise SystemExit(f"Graph file does not exist: {graph_path}")

    wiki_text = wiki_path.read_text(encoding="utf-8-sig")
    graph = json.loads(graph_path.read_text(encoding="utf-8-sig"))

    keywords = {
        args.topic.lower(),
        *(keyword.lower() for keyword in args.keywords),
    }

    relevant_nodes: list[dict[str, Any]] = []

    for node in graph.get("nodes", []):
        if any(keyword in normalize(node) for keyword in keywords):
            relevant_nodes.append(node)

    relevant_ids = {
        get_node_id(node)
        for node in relevant_nodes
        if get_node_id(node) is not None
    }

    relevant_edges: list[dict[str, Any]] = []

    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")

        if (
            source in relevant_ids
            or target in relevant_ids
            or any(keyword in normalize(edge) for keyword in keywords)
        ):
            relevant_edges.append(edge)

    headings = extract_headings(wiki_text)
    equations = extract_equation_lines(wiki_text)

    lines: list[str] = [
        f"# Context Packet: {args.topic}",
        "",
        "## Allowed Sources",
        "",
        f"- `{wiki_path.as_posix()}`",
        f"- `{graph_path.as_posix()}`",
        "",
        "## Usage Rules",
        "",
        "- Use only the material contained in this packet.",
        "- Do not add outside factual knowledge.",
        "- Mark unsupported claims as `SOURCE GAP`.",
        "- Every factual section must include a structured source reference:",
        "  `{ \"sourceId\": \"<wiki-file>#<heading-slug>\", \"quote\": \"<verbatim text>\" }`.",
        "- Slug = lowercased heading, punctuation removed, spaces to hyphens.",
        "- Copy `quote` verbatim from the cited section; do not author a hash.",
        "",
        "## Source Article",
        "",
        wiki_text.strip(),
        "",
        "## Extracted Headings",
        "",
    ]

    if headings:
        lines.extend(f"- {heading}" for heading in headings)
    else:
        lines.append("- No headings detected.")

    lines.extend(
        [
            "",
            "## Candidate Equation Lines",
            "",
        ]
    )

    if equations:
        lines.extend(f"- {equation}" for equation in equations)
    else:
        lines.append("- No candidate equation lines detected.")

    lines.extend(
        [
            "",
            "## Relevant Knowledge-Graph Nodes",
            "",
            "```json",
            json.dumps(relevant_nodes, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Relevant Knowledge-Graph Edges",
            "",
            "```json",
            json.dumps(relevant_edges, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Explicit Source Gaps",
            "",
            "- Add source gaps during generation when the packet lacks support.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(f"Wrote: {output_path}")
    print(f"Wiki characters: {len(wiki_text)}")
    print(f"Relevant nodes: {len(relevant_nodes)}")
    print(f"Relevant edges: {len(relevant_edges)}")


if __name__ == "__main__":
    main()
