from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from services.ingestion import IngestionService  # noqa: E402


class V2IngestionTests(unittest.TestCase):
    def test_markdown_ingestion_is_deterministic_and_keeps_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "gibbs.md"
            source.write_text(
                "# Gibbs Free Energy\n\n"
                "Gibbs free energy determines reaction spontaneity.\n\n"
                "![plot](figure.png)\n",
                encoding="utf-8",
            )
            service = IngestionService(root)
            first = service.ingest(source)
            second = service.ingest(source)

            self.assertEqual(first, second)
            source_dir = root / "knowledge" / "sources" / first["sourceId"]
            self.assertTrue((source_dir / "manifest.json").exists())
            self.assertTrue((source_dir / "chunks.json").exists())
            self.assertTrue((source_dir / "extraction-log.json").exists())
            self.assertTrue(
                (source_dir / "original-file.sha256")
                .read_text(encoding="utf-8")
                .startswith(first["fileHash"].removeprefix("sha256:"))
            )

            chunks = json.loads((source_dir / "chunks.json").read_text(encoding="utf-8"))["chunks"]
            self.assertTrue(chunks[0]["chunkId"].startswith(first["sourceId"]))
            self.assertTrue(chunks[0]["sourceSpan"].startswith("chars "))
            self.assertEqual(first["figureCount"], 1)

    def test_plain_text_pdf_and_docx_ingestion_supported(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            txt = root / "source.txt"
            txt.write_text("Amino acids can act as zwitterions.", encoding="utf-8")
            pdf = root / "source.pdf"
            pdf.write_bytes(_minimal_pdf("Delta G less than 0 means spontaneous."))
            docx = root / "source.docx"
            _minimal_docx(docx, ["The isoelectric point is the pH with zero net charge."])

            service = IngestionService(root)
            manifests = [service.ingest(path) for path in (txt, pdf, docx)]

            self.assertEqual([item["extractionStatus"] for item in manifests], ["success", "success", "success"])
            self.assertEqual(
                {item["mediaType"] for item in manifests},
                {
                    "text/plain",
                    "application/pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                },
            )

    def test_one_page_pdf_has_page_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "one.pdf"
            pdf.write_bytes(_minimal_pdf_pages(["Delta G less than 0 means spontaneous."]))
            manifest = _ingest_with_forced_pdf_fallback(root, pdf)
            chunks = _chunks(root, manifest)

            self.assertEqual(manifest["pages"][0]["pageNumber"], 1)
            self.assertEqual(chunks[0]["pageStart"], 1)
            self.assertEqual(chunks[0]["pageEnd"], 1)
            self.assertTrue(chunks[0]["sourceSpan"].startswith("page 1, chars "))

    def test_multi_page_pdf_chunk_can_span_two_pages(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "two.pdf"
            pdf.write_bytes(_minimal_pdf_pages(["Repeated phrase on page one.", "Repeated phrase on page two."]))
            service = IngestionService(root)
            old = os.environ.get("MCAT_FORCE_PDF_FALLBACK")
            os.environ["MCAT_FORCE_PDF_FALLBACK"] = "1"
            try:
                manifest = service.ingest(pdf)
            finally:
                _restore_env("MCAT_FORCE_PDF_FALLBACK", old)
            chunks = _chunks(root, manifest)

            self.assertEqual([page["pageNumber"] for page in manifest["pages"]], [1, 2])
            self.assertEqual(chunks[0]["pageStart"], 1)
            self.assertEqual(chunks[0]["pageEnd"], 2)
            self.assertIn("pages 1-2", chunks[0]["sourceSpan"])

    def test_repeated_pdf_text_keeps_distinct_page_segments(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "repeat.pdf"
            pdf.write_bytes(_minimal_pdf_pages(["Same sentence.", "Same sentence."]))
            manifest = _ingest_with_forced_pdf_fallback(root, pdf)
            pages = manifest["pages"]
            self.assertEqual(pages[0]["text"], pages[1]["text"])
            self.assertNotEqual(pages[0]["pageStartChar"], pages[1]["pageStartChar"])

    def test_blank_page_is_recorded_without_fabricating_text(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "blank.pdf"
            pdf.write_bytes(_minimal_pdf_pages(["First page text.", ""]))
            manifest = _ingest_with_forced_pdf_fallback(root, pdf)
            self.assertEqual(len(manifest["pages"]), 2)
            self.assertEqual(manifest["pages"][1]["text"], "")

    def test_malformed_pdf_fails_with_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "bad.pdf"
            pdf.write_bytes(b"%PDF-1.4\nnot a usable pdf\n")
            manifest = _ingest_with_forced_pdf_fallback(root, pdf)
            log = json.loads(
                (root / "knowledge" / "sources" / manifest["sourceId"] / "extraction-log.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["extractionStatus"], "failed")
            self.assertEqual(manifest["pages"], [])
            self.assertEqual(log["events"][0]["event"], "pdf-fallback-extracted")

    def test_pdf_page_lineage_stable_across_reingestion(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pdf = root / "stable.pdf"
            pdf.write_bytes(_minimal_pdf_pages(["Page one.", "Page two."]))
            old = os.environ.get("MCAT_FORCE_PDF_FALLBACK")
            os.environ["MCAT_FORCE_PDF_FALLBACK"] = "1"
            try:
                service = IngestionService(root)
                first = service.ingest(pdf)
                first_chunks = _chunks(root, first)
                second = service.ingest(pdf)
                second_chunks = _chunks(root, second)
            finally:
                _restore_env("MCAT_FORCE_PDF_FALLBACK", old)
            self.assertEqual(first, second)
            self.assertEqual(first_chunks, second_chunks)


def _minimal_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def _minimal_pdf(text: str) -> bytes:
    return _minimal_pdf_pages([text])


def _minimal_pdf_pages(pages: list[str]) -> bytes:
    objects: list[str] = ["1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj"]
    page_refs = []
    next_obj = 3
    for page_text in pages:
        page_obj = next_obj
        content_obj = next_obj + 1
        page_refs.append(f"{page_obj} 0 R")
        stream = f"BT /F1 12 Tf 72 720 Td ({page_text}) Tj ET" if page_text else ""
        objects.append(f"{page_obj} 0 obj << /Type /Page /Parent 2 0 R /Contents {content_obj} 0 R >> endobj")
        objects.append(f"{content_obj} 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj")
        next_obj += 2
    objects.insert(1, f"2 0 obj << /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(pages)} >> endobj")
    return (
        "%PDF-1.4\n"
        + "\n".join(objects)
        + "\n"
        "trailer << /Root 1 0 R >>\n%%EOF\n"
    ).encode("latin-1")


def _ingest_with_forced_pdf_fallback(root: Path, pdf: Path) -> dict:
    old = os.environ.get("MCAT_FORCE_PDF_FALLBACK")
    os.environ["MCAT_FORCE_PDF_FALLBACK"] = "1"
    try:
        return IngestionService(root).ingest(pdf)
    finally:
        _restore_env("MCAT_FORCE_PDF_FALLBACK", old)


def _restore_env(name: str, old: str | None) -> None:
    if old is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = old


def _chunks(root: Path, manifest: dict) -> list[dict]:
    return json.loads(
        (root / "knowledge" / "sources" / manifest["sourceId"] / "chunks.json").read_text(encoding="utf-8")
    )["chunks"]


if __name__ == "__main__":
    unittest.main()
