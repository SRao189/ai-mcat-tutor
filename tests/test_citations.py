"""Unit tests for the Gate 2 deterministic citation resolver (scripts/citations.py).

Run: python -m tests.test_citations   (from repo root)
No network, no models, no subprocess. Each case builds a tiny markdown source in
a temp dir and asserts the verify_citation verdict.
"""
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import citations  # noqa: E402

SOURCE = """# Thermodynamics

## Gibbs Free Energy (delta G)

A reaction is spontaneous when delta G is negative. Gibbs free energy is
defined as delta G equals delta H minus T delta S.

## Kinetics

Rate depends on activation energy.
"""

ANCHOR = "gibbs-free-energy-delta-g"
QUOTE = "A reaction is spontaneous when delta G is negative."


def _src(tmp: Path, text: str = SOURCE) -> Path:
    p = tmp / "src.md"
    p.write_text(text, encoding="utf-8")
    return p


def _cite(tmp: Path, **overrides) -> dict:
    sid = f"{_src(tmp).relative_to(tmp).as_posix()}#{ANCHOR}"
    cite = citations.make_citation(tmp, sid, QUOTE)
    cite.update(overrides)
    return cite


def test_valid_citation_passes():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ok, reason = citations.verify_citation(_cite(tmp), tmp)
        assert ok and reason == citations.OK, reason


def test_source_missing_fails():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _cite(tmp)
        cite["sourceId"] = f"nope.md#{ANCHOR}"
        ok, reason = citations.verify_citation(cite, tmp)
        assert not ok and reason == citations.SOURCE_MISSING, reason


def test_anchor_not_found_fails():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _cite(tmp)
        cite["sourceId"] = "src.md#does-not-exist"
        ok, reason = citations.verify_citation(cite, tmp)
        assert not ok and reason == citations.ANCHOR_UNRESOLVED, reason


def test_anchor_ambiguous_fails():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        # two headings slugify to the same anchor
        dup = SOURCE + "\n## Gibbs Free Energy (delta G)\n\nDuplicate.\n"
        _src(tmp, dup)
        sid = f"src.md#{ANCHOR}"
        # build hash off the first occurrence so only ambiguity is under test
        cite = {"sourceId": sid, "quote": QUOTE,
                "passageHash": "sha256:deadbeef"}
        ok, reason = citations.verify_citation(cite, tmp)
        assert not ok and reason == citations.ANCHOR_AMBIGUOUS, reason


def test_hash_mismatch_when_source_edited():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _cite(tmp)
        # edit the cited passage after the citation was built
        edited = SOURCE.replace("is negative", "is positive")
        _src(tmp, edited)
        ok, reason = citations.verify_citation(cite, tmp)
        assert not ok and reason == citations.HASH_MISMATCH, reason


def test_quote_not_substring_fails():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _cite(tmp, quote="entropy always increases in the universe")
        ok, reason = citations.verify_citation(cite, tmp)
        assert not ok and reason == citations.QUOTE_NOT_FOUND, reason


def test_malformed_citations_fail():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        good = _cite(tmp)
        # missing '#'
        bad_id = dict(good, sourceId="src.md")
        # missing field
        missing = {k: v for k, v in good.items() if k != "passageHash"}
        # not an object
        for bad in (bad_id, missing, "src.md:22-24"):
            ok, reason = citations.verify_citation(bad, tmp)
            assert not ok and reason == citations.MALFORMED, (bad, reason)


def test_reformatted_source_still_matches():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cite = _cite(tmp)
        # same words, re-wrapped with extra blank lines / spacing
        reformatted = SOURCE.replace(
            "A reaction is spontaneous when delta G is negative. Gibbs free\n"
            "energy is",
            "A reaction is spontaneous when delta G is    negative.\n\n"
            "Gibbs free energy   is",
        )
        _src(tmp, reformatted)
        ok, reason = citations.verify_citation(cite, tmp)
        assert ok and reason == citations.OK, reason


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
