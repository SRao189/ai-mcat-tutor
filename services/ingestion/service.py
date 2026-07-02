"""Source ingestion service for the knowledge-first v2 pipeline."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .chunking import chunk_text
from .extractors import extract_document


DEFAULT_ACCESS_CLASSIFICATION = "private-user-provided"
DEFAULT_COPYRIGHT_CLASSIFICATION = "user-provided-unknown"


class IngestionService:
    def __init__(self, repo_root: Path | str) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.sources_root = self.repo_root / "knowledge" / "sources"

    def ingest(
        self,
        source_path: Path | str,
        *,
        provenance: dict[str, Any] | None = None,
        access_classification: str = DEFAULT_ACCESS_CLASSIFICATION,
        copyright_classification: str = DEFAULT_COPYRIGHT_CLASSIFICATION,
    ) -> dict[str, Any]:
        path = Path(source_path).resolve()
        file_bytes = path.read_bytes()
        digest = hashlib.sha256(file_bytes).hexdigest()
        source_id = f"source-{digest[:16]}"
        result = extract_document(path)
        chunks = chunk_text(source_id, result.raw_text, pages=result.pages)

        source_dir = self.sources_root / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        original_dir = source_dir / "original"
        original_dir.mkdir(exist_ok=True)
        original_name = f"{digest}{path.suffix.lower()}"
        original_target = original_dir / original_name
        if not original_target.exists():
            shutil.copy2(path, original_target)

        (source_dir / "raw.txt").write_text(result.raw_text, encoding="utf-8", newline="\n")
        chunk_manifest = {
            "sourceId": source_id,
            "fileHash": f"sha256:{digest}",
            "chunks": [
                {
                    "chunkId": chunk.chunk_id,
                    "index": chunk.index,
                    "sourceId": source_id,
                    "sourceSpan": chunk.source_span,
                    "startChar": chunk.start_char,
                    "endChar": chunk.end_char,
                    "absoluteStartChar": chunk.start_char,
                    "absoluteEndChar": chunk.end_char,
                    "pageStart": chunk.page_start,
                    "pageEnd": chunk.page_end,
                    "pageRelativeStart": chunk.page_relative_start,
                    "pageRelativeEnd": chunk.page_relative_end,
                    "text": chunk.text,
                    "textHash": f"sha256:{hashlib.sha256(chunk.text.encode('utf-8')).hexdigest()}",
                }
                for chunk in chunks
            ],
        }
        manifest = {
            "sourceId": source_id,
            "fileHash": f"sha256:{digest}",
            "title": result.title,
            "mediaType": result.media_type,
            "originalFilename": path.name,
            "provenance": provenance or {"kind": "local-file", "path": str(path)},
            "accessClassification": access_classification,
            "copyrightClassification": copyright_classification,
            "extractionStatus": result.status,
            "pages": result.pages,
            "pageOrSectionMetadata": result.sections,
            "rawTextPath": "raw.txt",
            "chunkManifestPath": "chunks.json",
            "figureManifestPath": "figures.json",
            "extractionLogPath": "extraction-log.json",
            "originalFile": {"path": f"original/{original_name}", "hash": f"sha256:{digest}", "immutable": True},
            "chunkCount": len(chunks),
            "figureCount": len(result.figures),
        }
        extraction_log = {
            "sourceId": source_id,
            "fileHash": f"sha256:{digest}",
            "events": result.log + [{"event": "manifests-written", "chunks": len(chunks), "figures": len(result.figures), "deterministic": True}],
        }

        _write_json(source_dir / "manifest.json", manifest)
        _write_json(source_dir / "chunks.json", chunk_manifest)
        _write_json(source_dir / "figures.json", {"sourceId": source_id, "figures": result.figures})
        _write_json(source_dir / "extraction-log.json", extraction_log)
        (source_dir / "original-file.sha256").write_text(f"{digest}  original/{original_name}\n", encoding="utf-8")
        return manifest


def ingest_source(repo_root: Path | str, source_path: Path | str, **kwargs: Any) -> dict[str, Any]:
    return IngestionService(repo_root).ingest(source_path, **kwargs)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
