from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.schemas import validate_wiki_concept_page  # noqa: E402
from services.ingestion import IngestionService  # noqa: E402


def _wiki_module():
    path = REPO / "services" / "wiki-compiler" / "wiki_compiler.py"
    spec = importlib.util.spec_from_file_location("wiki_compiler", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class V2WikiCouncilTests(unittest.TestCase):
    def test_verified_claim_becomes_learner_eligible_and_matches_schema(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "gibbs.md"
            source.write_text("# Gibbs\n\nGibbs free energy determines reaction spontaneity.", encoding="utf-8")
            manifest = IngestionService(root).ingest(source)
            chunks = json.loads(
                (root / "knowledge" / "sources" / manifest["sourceId"] / "chunks.json").read_text(encoding="utf-8")
            )["chunks"]
            page = {
                "conceptId": "chem.thermodynamics.gibbs-free-energy",
                "title": "Gibbs Free Energy",
                "summary": "A source-grounded concept page.",
                "claims": [
                    {
                        "text": "Gibbs free energy determines reaction spontaneity.",
                        "sourceId": manifest["sourceId"],
                        "sourceSpan": chunks[0]["chunkId"],
                        "verification": "source-gap",
                        "confidence": 0,
                    }
                ],
                "equations": [],
                "examples": [],
                "figures": [],
                "relatedConcepts": [],
            }

            wiki = _wiki_module()
            verified = wiki.ingest_concept(root, page)
            self.assertIs(verified["learnerEligible"], True)
            self.assertEqual(verified["claims"][0]["verification"], "verified")
            self.assertEqual(validate_wiki_concept_page(verified), [])
            self.assertTrue((root / "knowledge" / "wiki" / "concepts" / f"{page['conceptId']}.verification.json").exists())
            self.assertEqual(wiki.query_wiki(root, "reaction spontaneity")[0]["conceptId"], page["conceptId"])
            self.assertIs(wiki.lint_wiki(root)["ok"], True)

    def test_unsupported_and_source_gap_claims_are_not_learner_eligible(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source.txt"
            source.write_text("Amino acids can act as zwitterions.", encoding="utf-8")
            manifest = IngestionService(root).ingest(source)
            chunks = json.loads(
                (root / "knowledge" / "sources" / manifest["sourceId"] / "chunks.json").read_text(encoding="utf-8")
            )["chunks"]
            page = {
                "conceptId": "biochem.amino-acid.zwitterion",
                "title": "Zwitterions",
                "summary": "A source-grounded concept page.",
                "claims": [
                    {
                        "text": "Every amino acid has exactly seven pKa values.",
                        "sourceId": manifest["sourceId"],
                        "sourceSpan": chunks[0]["chunkId"],
                        "verification": "source-gap",
                        "confidence": 0,
                    },
                    {
                        "text": "A missing source claim.",
                        "sourceId": "source-missing",
                        "sourceSpan": "source-missing:chunk:0001",
                        "verification": "source-gap",
                        "confidence": 0,
                    },
                ],
                "equations": [],
                "examples": [],
                "figures": [],
                "relatedConcepts": [],
            }

            verified = _wiki_module().ingest_concept(root, page)
            self.assertIs(verified["learnerEligible"], False)
            self.assertEqual([claim["verification"] for claim in verified["claims"]], ["unsupported", "source-gap"])
            self.assertFalse(any(claim["learnerEligible"] for claim in verified["claims"]))


if __name__ == "__main__":
    unittest.main()
