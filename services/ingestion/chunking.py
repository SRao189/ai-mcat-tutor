"""Deterministic chunking with source-span lineage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    index: int
    text: str
    start_char: int
    end_char: int
    source_span: str
    page_start: int | None = None
    page_end: int | None = None
    page_relative_start: int | None = None
    page_relative_end: int | None = None


def chunk_text(
    source_id: str,
    text: str,
    *,
    pages: list[dict[str, Any]] | None = None,
    max_chars: int = 1200,
) -> list[TextChunk]:
    """Split text into stable paragraph chunks without model-dependent logic."""
    paragraphs = _paragraph_ranges(text)
    if not paragraphs:
        return []

    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_start = paragraphs[0][0]
    current_end = paragraphs[0][0]

    def flush() -> None:
        nonlocal current_parts, current_start, current_end
        if not current_parts:
            return
        chunk_index = len(chunks) + 1
        body = "\n\n".join(current_parts).strip()
        chunks.append(
            TextChunk(
                chunk_id=f"{source_id}:chunk:{chunk_index:04d}",
                index=chunk_index,
                text=body,
                start_char=current_start,
                end_char=current_end,
                source_span=_source_span(current_start, current_end, pages or []),
                **_page_lineage(current_start, current_end, pages or []),
            )
        )
        current_parts = []

    for start, end, paragraph in paragraphs:
        proposed_len = sum(len(part) for part in current_parts) + len(paragraph)
        if current_parts and proposed_len > max_chars:
            flush()
            current_start = start
        current_parts.append(paragraph)
        current_end = end

    flush()
    return chunks


def _page_lineage(start: int, end: int, pages: list[dict[str, Any]]) -> dict[str, int | None]:
    start_page = _page_for_offset(start, pages)
    end_page = _page_for_offset(max(start, end - 1), pages)
    if start_page is None or end_page is None:
        return {
            "page_start": None,
            "page_end": None,
            "page_relative_start": None,
            "page_relative_end": None,
        }
    return {
        "page_start": int(start_page["pageNumber"]),
        "page_end": int(end_page["pageNumber"]),
        "page_relative_start": start - int(start_page["pageStartChar"]),
        "page_relative_end": end - int(end_page["pageStartChar"]),
    }


def _source_span(start: int, end: int, pages: list[dict[str, Any]]) -> str:
    lineage = _page_lineage(start, end, pages)
    if lineage["page_start"] is None:
        return f"chars {start}-{end}"
    if lineage["page_start"] == lineage["page_end"]:
        return f"page {lineage['page_start']}, chars {lineage['page_relative_start']}-{lineage['page_relative_end']}"
    return (
        f"pages {lineage['page_start']}-{lineage['page_end']}, "
        f"chars {lineage['page_relative_start']}-{lineage['page_relative_end']}"
    )


def _page_for_offset(offset: int, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
    for page in pages:
        start = int(page["pageStartChar"])
        end = int(page["pageEndChar"])
        if start <= offset < end:
            return page
        if start == end == offset:
            return page
    return None


def _paragraph_ranges(text: str) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    cursor = 0
    for block in text.split("\n\n"):
        start = text.find(block, cursor)
        if start < 0:
            start = cursor
        end = start + len(block)
        stripped = block.strip()
        if stripped:
            leading = len(block) - len(block.lstrip())
            trailing = len(block.rstrip())
            ranges.append((start + leading, start + trailing, stripped))
        cursor = end + 2
    return ranges
