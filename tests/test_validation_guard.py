"""Regression tests for the SHA-256 stale-validation guard.

Run: python -m tests.test_validation_guard   (from repo root)
No network, no models. Drives the real scripts as subprocesses in a temp
workspace so the relative paths they hardcode (course-data/, validation/,
app/) behave exactly as in production.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VALIDATE = REPO / "scripts" / "validate-module.py"
BUILD = REPO / "scripts" / "build-course.py"

sys.path.insert(0, str(REPO / "scripts"))
import citations  # noqa: E402

WIKI = """# Thermodynamics

## Gibbs Free Energy

A reaction is spontaneous when delta G is negative.
"""
WIKI_REL = "wiki/thermodynamics.md"
WIKI_ANCHOR = "gibbs-free-energy"
WIKI_QUOTE = "A reaction is spontaneous when delta G is negative."

VALID_MODULE = {
    "id": "module-1",
    "title": "Thermodynamics",
    "objectives": [],
    "sections": [],
    "equations": [],
    "workedExamples": [],
    "checks": [],
    "practiceQuestions": [],
    "sourceRefs": ["wiki/thermodynamics.md"],
    "sourceGaps": [],
}


def _workspace(tmp: Path) -> Path:
    (tmp / "course-data").mkdir()
    (tmp / "validation").mkdir()
    (tmp / "app").mkdir()
    return tmp


def _write_module(tmp: Path, data: dict) -> Path:
    path = tmp / "course-data" / "module-1.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _validate(tmp: Path, module: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATE), str(module.relative_to(tmp))],
        cwd=tmp, capture_output=True, text=True,
    )


def _build(tmp: Path, *extra: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(BUILD), *extra],
        cwd=tmp, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _write_wiki(tmp: Path) -> None:
    path = tmp / WIKI_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(WIKI, encoding="utf-8")


def _claim_citation(tmp: Path) -> dict:
    return citations.make_citation(
        tmp, f"{WIKI_REL}#{WIKI_ANCHOR}", WIKI_QUOTE)


def _module_with_claim(ref) -> dict:
    """A module with a claim-scope (section) citation. Top-level sourceRefs stays
    legacy file-provenance, which is intentionally excluded from the gate."""
    section = {"id": "s1", "title": "Section", "content": "body",
               "sourceRefs": [ref]}
    return dict(VALID_MODULE, sections=[section])


def _report(tmp: Path) -> dict:
    return json.loads(
        (tmp / "validation" / "module-1-report.json").read_text("utf-8"))


def _shipped_ids(tmp: Path) -> list[str]:
    js = (tmp / "app" / "course-data.js").read_text(encoding="utf-8")
    payload = js[js.index("=") + 1: js.rindex(";")]
    return [m["id"] for m in json.loads(payload)]


def test_unchanged_module_ships():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        module = _write_module(tmp, VALID_MODULE)
        assert _validate(tmp, module).returncode == 0
        out = _build(tmp)
        assert "Skipping" not in out
        assert "module-1" in _shipped_ids(tmp)


def test_edited_after_validation_skipped():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        module = _write_module(tmp, VALID_MODULE)
        assert _validate(tmp, module).returncode == 0
        # tamper after validation: same shape, different bytes
        edited = dict(VALID_MODULE, title="Tampered")
        _write_module(tmp, edited)
        out = _build(tmp)
        assert "hash mismatch" in out
        assert _shipped_ids(tmp) == []


def test_missing_hash_skipped():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        _write_module(tmp, VALID_MODULE)
        # hand-rolled report from before the guard existed: valid, no hash
        report = {"module": "course-data/module-1.json", "valid": True,
                  "errors": [], "warnings": []}
        (tmp / "validation" / "module-1-report.json").write_text(
            json.dumps(report), encoding="utf-8")
        out = _build(tmp)
        assert "no validated hash" in out
        assert _shipped_ids(tmp) == []


def test_malformed_report_skipped():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        _write_module(tmp, VALID_MODULE)
        (tmp / "validation" / "module-1-report.json").write_text(
            "{not valid json", encoding="utf-8")
        out = _build(tmp)
        assert "malformed report" in out
        assert _shipped_ids(tmp) == []


def test_revalidated_module_ships():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        module = _write_module(tmp, VALID_MODULE)
        assert _validate(tmp, module).returncode == 0
        # legitimate edit, then re-validate to refresh the hash
        edited = dict(VALID_MODULE, title="Revised Thermodynamics")
        _write_module(tmp, edited)
        assert _validate(tmp, module).returncode == 0
        out = _build(tmp)
        assert "Skipping" not in out
        assert "module-1" in _shipped_ids(tmp)


def test_structured_claim_citation_verified():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        _write_wiki(tmp)
        module = _write_module(tmp, _module_with_claim(_claim_citation(tmp)))
        assert _validate(tmp, module).returncode == 0
        assert _report(tmp)["citationsVerified"] is True


def test_file_provenance_alone_still_verifies():
    # top-level legacy file provenance only (no claim citations) is excluded
    # from the gate, so the module counts as citation-verified.
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        module = _write_module(tmp, VALID_MODULE)
        assert _validate(tmp, module).returncode == 0
        report = _report(tmp)
        assert report["citationsVerified"] is True
        assert report["legacyCitationCount"] >= 1  # still recorded


def test_legacy_claim_citation_not_verified():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        module = _write_module(tmp, _module_with_claim("wiki/thermo.md"))
        assert _validate(tmp, module).returncode == 0  # valid (warning)
        assert _report(tmp)["citationsVerified"] is False


def test_legacy_citation_fails_under_strict():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        module = _write_module(tmp, VALID_MODULE)
        proc = subprocess.run(
            [sys.executable, str(VALIDATE), str(module.relative_to(tmp)),
             "--strict"],
            cwd=tmp, capture_output=True, text=True,
        )
        assert proc.returncode == 1
        assert _report(tmp)["valid"] is False


def test_changed_source_fails_revalidation():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        _write_wiki(tmp)
        module = _write_module(tmp, _module_with_claim(_claim_citation(tmp)))
        assert _validate(tmp, module).returncode == 0
        # edit the cited source after the citation was built
        (tmp / WIKI_REL).write_text(
            WIKI.replace("is negative", "is positive"), encoding="utf-8")
        assert _validate(tmp, module).returncode == 1
        assert _report(tmp)["citationsVerified"] is False


def test_require_citations_skips_unverified():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        module = _write_module(tmp, _module_with_claim("wiki/thermo.md"))
        assert _validate(tmp, module).returncode == 0
        out = _build(tmp, "--require-citations")
        assert "unverified citations" in out
        assert _shipped_ids(tmp) == []


def test_require_citations_ships_verified():
    with tempfile.TemporaryDirectory() as d:
        tmp = _workspace(Path(d))
        _write_wiki(tmp)
        module = _write_module(tmp, _module_with_claim(_claim_citation(tmp)))
        assert _validate(tmp, module).returncode == 0
        out = _build(tmp, "--require-citations")
        assert "Skipping" not in out
        assert "module-1" in _shipped_ids(tmp)


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
