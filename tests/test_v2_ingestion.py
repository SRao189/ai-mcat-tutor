from __future__ import annotations

import json
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
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    return (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        f"4 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n"
        "trailer << /Root 1 0 R >>\n%%EOF\n"
    ).encode("latin-1")


if __name__ == "__main__":
    unittest.main()
