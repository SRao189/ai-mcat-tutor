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
from tests.fixtures.council_verifiers import (  # noqa: E402
    LowConfidenceVerifier,
    MalformedVerifier,
    RaisingVerifier,
    UnavailableCouncilVerifier,
)


def _wiki_module():
    path = REPO / "services" / "wiki-compiler" / "wiki_compiler.py"
    spec = importlib.util.spec_from_file_location("wiki_compiler", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    assert spec.loader is not None
    sys.modules["wiki_compiler"] = module
    spec.loader.exec_module(module)
    return module


def _boundary_module():
    path = REPO / "services" / "wiki-compiler" / "council_boundary.py"
    spec = importlib.util.spec_from_file_location("council_boundary", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    assert spec.loader is not None
    sys.modules["council_boundary"] = module
    spec.loader.exec_module(module)
    return module


def _ingested_page(root: Path, claim_text: str, source_text: str = "Gibbs free energy determines reaction spontaneity."):
    source = root / "gibbs.md"
    source.write_text(f"# Gibbs\n\n{source_text}", encoding="utf-8")
    manifest = IngestionService(root).ingest(source)
    chunks = json.loads(
        (root / "knowledge" / "sources" / manifest["sourceId"] / "chunks.json").read_text(encoding="utf-8")
    )["chunks"]
    return {
        "conceptId": "chem.thermodynamics.gibbs-free-energy",
        "title": "Gibbs Free Energy",
        "summary": "A source-grounded concept page.",
        "claims": [
            {
                "text": claim_text,
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


class V2WikiCouncilTests(unittest.TestCase):
    def test_verified_claim_becomes_learner_eligible_and_matches_schema(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            page = _ingested_page(root, "Gibbs free energy determines reaction spontaneity.")

            wiki = _wiki_module()
            verified = wiki.ingest_concept(root, page)
            self.assertIs(verified["learnerEligible"], True)
            self.assertEqual(verified["claims"][0]["verification"], "verified")
            self.assertEqual(verified["claims"][0]["citedPassageIds"], [verified["claims"][0]["sourceSpan"]])
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

    def test_false_rate_claim_is_rejected_by_real_council_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            page = _ingested_page(root, "Gibbs free energy determines reaction rate.")

            verified = _wiki_module().ingest_concept(root, page)
            self.assertIs(verified["learnerEligible"], False)
            self.assertEqual(verified["claims"][0]["verification"], "unsupported")
            self.assertIn("not directly supported", verified["claims"][0]["reason"])

    def test_council_exception_malformed_low_confidence_and_unavailable_fail_closed(self):
        boundary_module = _boundary_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            page = _ingested_page(root, "Gibbs free energy determines reaction spontaneity.")
            for fixture in (RaisingVerifier(), MalformedVerifier(), LowConfidenceVerifier(), UnavailableCouncilVerifier()):
                boundary = boundary_module.CouncilVerificationBoundary(root, verifier=fixture)
                verified, trace = boundary.verify_concept_page(page)
                self.assertIs(verified["learnerEligible"], False)
                self.assertNotEqual(verified["claims"][0]["verification"], "verified")
                self.assertFalse(verified["claims"][0]["learnerEligible"])
                self.assertTrue(trace["claims"])

    def test_learner_eligible_requires_verified_claims(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            page = _ingested_page(root, "Gibbs free energy determines reaction rate.")
            verified = _wiki_module().ingest_concept(root, page)
            self.assertTrue(
                all(
                    claim["learnerEligible"] is (claim["verification"] == "verified")
                    for claim in verified["claims"]
                )
            )


if __name__ == "__main__":
    unittest.main()
