from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class V2VendorProvenanceTests(unittest.TestCase):
    def test_vendor_provenance_files_exist_and_are_pinned(self):
        expected = {
            "vendor/impeccable.UPSTREAM": "44c27a72af98394c32691ba79358811bff86bde6",
            "vendor/understand-anything.UPSTREAM": "54754a6f97051d1d76c8758353d8ea41afe502a6",
            "vendor/llm-wiki.UPSTREAM": "ac46de1ad27f92b28ac95459c782c07f6b8c964a",
            "vendor/open-notebook.UPSTREAM": "14ba8f51e81f34855cd21c390f2576215d8808dd",
        }
        for rel, commit in expected.items():
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertIn(commit, text)
            self.assertIn("vendored_", text)

    def test_vendor_license_boundaries_are_explicit(self):
        self.assertTrue((REPO / "vendor" / "impeccable" / "LICENSE").exists())
        self.assertTrue((REPO / "vendor" / "understand-anything" / "LICENSE").exists())
        llm_notice = (REPO / "vendor" / "llm-wiki.UPSTREAM").read_text(encoding="utf-8")
        third_party = (REPO / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("license: none stated", llm_notice)
        self.assertIn("must not be described as MIT- or Apache-licensed", third_party)


if __name__ == "__main__":
    unittest.main()
