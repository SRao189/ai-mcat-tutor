"""Deterministic source normalization and compact context-packet construction.

No facts are invented or "corrected" here. We strip publisher boilerplate and
normalize whitespace only. Residual OCR intra-word spacing from the PDF
extraction (e.g. "t he") is passed through verbatim, because repairing it would
require outside knowledge the pipeline is forbidden from using.
"""
from __future__ import annotations

import re

# Full-line publisher boilerplate / running headers / footers to drop.
_BOILERPLATE = re.compile(
    r"""^\s*(
        MCAT\s+BIOCHEMISTRY\s+REVIEW
        | (\d+\s*\|\s*)?For\s+More\s+Free\s+Content.*
        | \d+\s*\|\s*$                 # bare "40 |" page markers
        | \|\s*\d+\s*$                 # bare "| 61" page markers
    )\s*$""",
    re.IGNORECASE | re.VERBOSE,
)


def normalize_raw(text: str) -> str:
    """Strip boilerplate lines and normalize whitespace. Preserves headings."""
    out: list[str] = []
    for line in text.splitlines():
        if _BOILERPLATE.match(line):
            continue
        line = re.sub(r"[ \t]+", " ", line).strip()
        out.append(line)
    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # collapse blank runs
    return cleaned.strip() + "\n"


def extract_section(normalized: str, start_pat: str, stop_pat: str | None) -> str:
    """Return text from the line matching start_pat up to (excluding) stop_pat.

    If stop_pat is None or not found, returns through end of document.
    """
    lines = normalized.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(start_pat, ln)), None)
    if start is None:
        raise ValueError(f"section start not found: {start_pat!r}")
    if stop_pat:
        stop = next(
            (i for i, ln in enumerate(lines) if i > start and re.match(stop_pat, ln)),
            len(lines),
        )
    else:
        stop = len(lines)
    return "\n".join(lines[start:stop]).strip() + "\n"


def split_subsections(normalized: str, chapter_num: int) -> list[tuple[str, str, str]]:
    """Split a normalized chapter into its numbered content subsections.

    A content heading is "<chapter>.<n> ALLCAPS TITLE" (>=2 leading capitals),
    which distinguishes real subsections (THERMODYNAMICS) from end-of-chapter
    "<chapter>.<n> Drill" blocks. Content stops at the first Drill heading.
    Returns [(subid, title, body_including_heading), ...] in source order.
    """
    lines = normalized.splitlines()
    head = re.compile(rf"^{chapter_num}\.(\d+) ([A-Z][A-Z].*)$")
    drill = re.compile(rf"^{chapter_num}\.\d+ \w+\b")  # any other numbered block
    heads = [(i, m) for i, ln in enumerate(lines) for m in [head.match(ln)] if m]
    if not heads:
        raise ValueError(f"no content subsections found for chapter {chapter_num}")
    content_end = next(
        (i for i, ln in enumerate(lines)
         if drill.match(ln) and not head.match(ln)), len(lines))
    subs: list[tuple[str, str, str]] = []
    for idx, (start, m) in enumerate(heads):
        nxt = heads[idx + 1][0] if idx + 1 < len(heads) else content_end
        nxt = min(nxt, content_end)
        if start >= content_end:
            continue
        subid = f"{chapter_num}.{m.group(1)}"
        title = m.group(2).strip().title()
        body = "\n".join(lines[start:nxt]).strip() + "\n"
        subs.append((subid, title, body))
    return subs


def build_context_packet(
    section_text: str,
    packet_title: str,
    source_ref: str,
    raw_source_path: str,
) -> str:
    """Wrap an extracted section in the canonical context-packet format."""
    return (
        f"# Context Packet: {packet_title}\n\n"
        "## Allowed Sources\n\n"
        f"- `{raw_source_path}`\n\n"
        "## Usage Rules\n\n"
        "- Use only the material contained in this packet.\n"
        "- Do not add outside factual knowledge.\n"
        "- Mark unsupported claims as `SOURCE GAP`.\n"
        "- Every factual section must include a source reference.\n"
        f"- Cite source material as `{source_ref}`.\n\n"
        "## Source Material\n\n"
        f"{section_text}"
    )
