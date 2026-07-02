"""Deterministic chunking with source-span lineage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    index: int
    text: str
    start_char: int
    end_char: int
    source_span: str


def chunk_text(source_id: str, text: str, *, max_chars: int = 1200) -> list[TextChunk]:
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
                source_span=f"chars {current_start}-{current_end}",
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
