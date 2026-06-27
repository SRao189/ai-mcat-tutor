"""Tests for the Gate 2 migration converter (scripts/migrate-citations.py).

Run: python -m tests.test_migrate_citations   (from repo root)
No network, no models, no subprocess.
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import citations  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "migrate_citations", REPO / "scripts" / "migrate-citations.py")
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

WIKI = """# Thermodynamics

## Gibbs Free Energy

A reaction is spontaneous when delta G is negative.

## Kinetics

Rate depends on activation energy and temperature.
"""


def _setup(tmp: Path):
    (tmp / "wiki").mkdir()
    (tmp / "wiki" / "thermo.md").write_text(WIKI, encoding="utf-8")
    # a "packet" the legacy ref points into; line 5 holds the spontaneity claim
    packet = tmp / "packet.md"
    packet.write_text(
        "line1\nline2\nline3\nline4\n"
        "A reaction is spontaneous when delta G is negative.\n",
        encoding="utf-8")
    return tmp / "wiki"


def test_legacy_ref_resolves_to_unique_passage():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        wiki_dir = _setup(tmp)
        cite, reason = mig.convert_ref(tmp, wiki_dir, "packet.md:5-5")
        assert reason == "ok", reason
        assert cite["sourceId"] == "wiki/thermo.md#gibbs-free-energy"
        # the emitted citation must actually pass Gate 2 verification
        ok, vreason = citations.verify_citation(cite, tmp)
        assert ok and vreason == citations.OK, vreason


def test_no_unique_match_goes_to_review():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        # line 1 ("line1") appears in no wiki passage
        cite, reason = mig.convert_ref(tmp, tmp / "wiki", "packet.md:1-1")
        assert cite is None
        assert reason == "no-unique-wiki-passage", reason


def test_bare_filename_has_no_line_range():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        cite, reason = mig.convert_ref(tmp, tmp / "wiki", "wiki/thermo.md")
        assert cite is None and reason == "no-line-range", reason


def test_migrate_module_keeps_unresolved_and_lists_review():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        wiki_dir = _setup(tmp)
        data = {
            "sourceRefs": ["packet.md:5-5", "packet.md:1-1"],
            "sections": [],
        }
        new, review = mig.migrate_module(data, tmp, wiki_dir)
        # first resolved to an object, second left as legacy string + reviewed
        assert isinstance(new["sourceRefs"][0], dict)
        assert new["sourceRefs"][1] == "packet.md:1-1"
        assert len(review) == 1
        assert review[0]["reason"] == "no-unique-wiki-passage"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
