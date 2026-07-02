"""Local document extraction for v2 source ingestion."""

from __future__ import annotations

import html
import mimetypes
import os
import re
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".txt"}


@dataclass(frozen=True)
class ExtractionResult:
    media_type: str
    title: str
    raw_text: str
    status: str
    pages: list[dict[str, Any]] = field(default_factory=list)
    sections: list[dict[str, Any]] = field(default_factory=list)
    figures: list[dict[str, Any]] = field(default_factory=list)
    log: list[dict[str, Any]] = field(default_factory=list)


def media_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in {".md", ".markdown"}:
        return "text/markdown"
    if ext == ".txt":
        return "text/plain"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def extract_document(path: Path) -> ExtractionResult:
    path = path.resolve()
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return ExtractionResult(
            media_type=media_type_for(path),
            title=path.stem,
        raw_text="",
        status="failed",
        pages=[],
        log=[{"event": "unsupported-media-type", "extension": suffix}],
        )
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix in {".md", ".markdown"}:
        return _extract_markdown(path)
    return _extract_text(path)


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_text(path: Path) -> ExtractionResult:
    text = _read_text(path).strip()
    return ExtractionResult(
        media_type="text/plain",
        title=path.stem,
        raw_text=text,
        status="success" if text else "failed",
        pages=[],
        sections=[{"id": "section-0001", "label": "Document", "startChar": 0, "endChar": len(text)}] if text else [],
        log=[{"event": "plain-text-extracted", "characters": len(text)}],
    )


def _extract_markdown(path: Path) -> ExtractionResult:
    text = _read_text(path).strip()
    figures = [
        {
            "figureId": f"figure-{index:04d}",
            "kind": "markdown-image",
            "altText": match.group("alt"),
            "target": match.group("target"),
        }
        for index, match in enumerate(
            re.finditer(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+)\)", text),
            start=1,
        )
    ]
    return ExtractionResult(
        media_type="text/markdown",
        title=_markdown_title(text) or path.stem,
        raw_text=text,
        status="success" if text else "failed",
        pages=[],
        sections=_markdown_sections(text),
        figures=figures,
        log=[{"event": "markdown-extracted", "characters": len(text), "figures": len(figures)}],
    )


def _markdown_title(text: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _markdown_sections(text: str) -> list[dict[str, Any]]:
    headings = list(re.finditer(r"^(#{1,6})\s+(.+)$", text, flags=re.MULTILINE))
    if not headings and text:
        return [{"id": "section-0001", "label": "Document", "level": 1, "startChar": 0, "endChar": len(text)}]
    sections: list[dict[str, Any]] = []
    for index, match in enumerate(headings, start=1):
        end = headings[index].start() if index < len(headings) else len(text)
        sections.append(
            {
                "id": f"section-{index:04d}",
                "label": match.group(2).strip(),
                "level": len(match.group(1)),
                "startChar": match.start(),
                "endChar": end,
            }
        )
    return sections


def _extract_docx(path: Path) -> ExtractionResult:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
            media_files = sorted(name for name in archive.namelist() if name.startswith("word/media/"))
    except (KeyError, zipfile.BadZipFile) as exc:
        return ExtractionResult(media_type=media_type_for(path), title=path.stem, raw_text="", status="failed", pages=[], log=[{"event": "docx-extraction-failed", "reason": str(exc)}])

    root = ElementTree.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        runs = [node.text or "" for node in paragraph.findall(".//w:t", ns)]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    raw_text = "\n\n".join(paragraphs)
    figures = [{"figureId": f"figure-{index:04d}", "kind": "docx-media", "path": name} for index, name in enumerate(media_files, start=1)]
    return ExtractionResult(media_type=media_type_for(path), title=path.stem, raw_text=raw_text, status="success" if raw_text else "failed", pages=[], sections=_paragraph_sections(paragraphs, raw_text), figures=figures, log=[{"event": "docx-extracted", "paragraphs": len(paragraphs), "figures": len(figures)}])


def _paragraph_sections(paragraphs: list[str], raw_text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    cursor = 0
    for index, paragraph in enumerate(paragraphs, start=1):
        start = raw_text.find(paragraph, cursor)
        end = start + len(paragraph)
        sections.append({"id": f"section-{index:04d}", "label": paragraph[:80], "startChar": start, "endChar": end})
        cursor = end
    return sections


def _extract_pdf(path: Path) -> ExtractionResult:
    if os.environ.get("MCAT_FORCE_PDF_FALLBACK") != "1":
        pypdf_result = _extract_pdf_with_optional_library(path)
    else:
        pypdf_result = None
    if pypdf_result is not None:
        return pypdf_result

    data = path.read_bytes()
    page_texts = _extract_pdf_pages_from_objects(data)
    raw_text, pages = _build_pdf_page_segments(page_texts)
    figures = [{"figureId": f"figure-{index:04d}", "kind": "pdf-image-xobject"} for index, _ in enumerate(re.finditer(rb"/Subtype\s*/Image\b", data), start=1)]
    status = "success" if raw_text.strip() else "failed"
    return ExtractionResult(
        media_type="application/pdf",
        title=path.stem,
        raw_text=raw_text,
        status=status,
        pages=pages,
        sections=[_page_section(page) for page in pages],
        figures=figures,
        log=[{"event": "pdf-fallback-extracted", "pages": len(pages), "characters": len(raw_text), "figures": len(figures), "status": status}],
    )


def _extract_pdf_with_optional_library(path: Path) -> ExtractionResult | None:
    reader_cls = None
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader_cls = getattr(module, "PdfReader")
            break
        except (ImportError, AttributeError):
            continue
    if reader_cls is None:
        return None
    try:
        reader = reader_cls(str(path))
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception:
        return None
    raw_text, pages = _build_pdf_page_segments(page_texts)
    return ExtractionResult(
        media_type="application/pdf",
        title=path.stem,
        raw_text=raw_text,
        status="success" if raw_text.strip() else "failed",
        pages=pages,
        sections=[_page_section(page) for page in pages],
        log=[{"event": "pdf-library-extracted", "pages": len(page_texts), "characters": len(raw_text)}],
    )


def _build_pdf_page_segments(page_texts: list[str]) -> tuple[str, list[dict[str, Any]]]:
    raw_parts: list[str] = []
    pages: list[dict[str, Any]] = []
    cursor = 0
    for index, text in enumerate(page_texts, start=1):
        if index > 1:
            raw_parts.append("\n\n")
            cursor += 2
        normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        start = cursor
        raw_parts.append(normalized)
        cursor += len(normalized)
        pages.append(
            {
                "pageNumber": index,
                "pageStartChar": start,
                "pageEndChar": cursor,
                "text": normalized,
            }
        )
    return "".join(raw_parts), pages


def _page_section(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"page-{page['pageNumber']:04d}",
        "label": f"Page {page['pageNumber']}",
        "page": page["pageNumber"],
        "pageNumber": page["pageNumber"],
        "startChar": page["pageStartChar"],
        "endChar": page["pageEndChar"],
        "pageStartChar": page["pageStartChar"],
        "pageEndChar": page["pageEndChar"],
    }


def _extract_pdf_pages_from_objects(data: bytes) -> list[str]:
    objects = {
        int(match.group("id")): match.group("body")
        for match in re.finditer(
            rb"(?P<id>\d+)\s+\d+\s+obj(?P<body>.*?)endobj",
            data,
            flags=re.DOTALL,
        )
    }
    pages: list[str] = []
    for _object_id, body in sorted(objects.items()):
        if not re.search(rb"/Type\s*/Page\b", body) or re.search(rb"/Type\s*/Pages\b", body):
            continue
        content_ids = _content_object_ids(body)
        page_text = " ".join(
            _decode_pdf_text_operators(_maybe_inflate(stream))
            for content_id in content_ids
            for stream in _object_streams(objects.get(content_id, b""))
        ).strip()
        pages.append(page_text)
    if pages:
        return pages
    stream_text = " ".join(part for part in _pdf_stream_text(data) if part).strip()
    return [stream_text] if stream_text else []


def _content_object_ids(page_object: bytes) -> list[int]:
    array_match = re.search(rb"/Contents\s*\[(?P<ids>.*?)\]", page_object, flags=re.DOTALL)
    if array_match:
        return [int(item) for item in re.findall(rb"(\d+)\s+\d+\s+R", array_match.group("ids"))]
    single_match = re.search(rb"/Contents\s+(?P<id>\d+)\s+\d+\s+R", page_object)
    return [int(single_match.group("id"))] if single_match else []


def _object_streams(object_body: bytes) -> list[bytes]:
    return [
        match.group("body").strip()
        for match in re.finditer(rb"stream\r?\n(?P<body>.*?)\r?\nendstream", object_body, flags=re.DOTALL)
    ]


def _pdf_stream_text(data: bytes) -> list[str]:
    texts: list[str] = []
    for match in re.finditer(rb"stream\r?\n(?P<body>.*?)\r?\nendstream", data, flags=re.DOTALL):
        body = match.group("body").strip()
        texts.append(_decode_pdf_text_operators(_maybe_inflate(body)))
    if not texts:
        texts.append(_decode_pdf_text_operators(data))
    return texts


def _maybe_inflate(body: bytes) -> bytes:
    try:
        return zlib.decompress(body)
    except zlib.error:
        return body


def _decode_pdf_text_operators(data: bytes) -> str:
    raw = data.decode("latin-1", errors="ignore")
    pieces: list[str] = []
    for literal in re.findall(r"\((?:\\.|[^\\)])*\)\s*Tj", raw):
        pieces.append(_decode_pdf_literal(literal.rsplit(")", 1)[0][1:]))
    for array in re.findall(r"\[(.*?)\]\s*TJ", raw, flags=re.DOTALL):
        parts = re.findall(r"\((?:\\.|[^\\)])*\)", array)
        if parts:
            pieces.append("".join(_decode_pdf_literal(part[1:-1]) for part in parts))
    return html.unescape(" ".join(part.strip() for part in pieces if part.strip()))


def _decode_pdf_literal(value: str) -> str:
    for source, target in {r"\(": "(", r"\)": ")", r"\\": "\\", r"\n": "\n", r"\r": "\r", r"\t": "\t"}.items():
        value = value.replace(source, target)
    return value
