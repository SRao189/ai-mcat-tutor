"""Tests for the local Section 7.1 tutor website/API.

Run: python -m tests.test_section71_server
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from council.schema import CouncilResponse, ResponseStatus  # noqa: E402
from server import app as server_app  # noqa: E402


def _start_server():
    httpd = server_app.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def _get(base: str, path: str):
    try:
        with urllib.request.urlopen(base + path, timeout=20) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _post(base: str, path: str, payload, *, session: str = "test-session"):
    data = json.dumps(payload).encode("utf-8") if not isinstance(payload, bytes) else payload
    req = urllib.request.Request(
        base + path,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Session-ID": session,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _with_server(test_fn):
    os.environ["NVIDIA_MOCK_MODE"] = "true"
    httpd, base = _start_server()
    try:
        test_fn(base)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_health_endpoint():
    def run(base):
        status, body = _get(base, "/api/health")
        assert status == 200
        assert json.loads(body)["ok"] is True

    _with_server(run)


def test_verified_response():
    def run(base):
        status, payload = _post(
            base,
            "/api/tutor",
            {"question": "What are the pKa values of phosphoric acid?", "sectionId": "7.1"},
            session="verified",
        )
        assert status == 200
        assert payload["status"] == "verified", payload
        assert payload["citedSources"][0]["sourceId"] == "chapter-7-1-passage-01"

    _with_server(run)


def test_chapter_endpoint_returns_section_71():
    def run(base):
        status, body = _get(base, "/api/chapter/7.1")
        assert status == 200
        payload = json.loads(body)
        assert payload["sectionId"] == "7.1"
        assert payload["title"] == "Phosphorus-Containing Compounds"
        assert payload["finalQuiz"]["questions"][0]["id"] == "quiz-triprotic"

    _with_server(run)


def test_chapters_endpoint_lists_section_71():
    def run(base):
        status, body = _get(base, "/api/chapters")
        assert status == 200
        payload = json.loads(body)
        assert {"id": "7.1", "title": "Phosphorus-Containing Compounds"} in payload

    _with_server(run)


def test_unknown_chapter_rejected():
    def run(base):
        status, body = _get(base, "/api/chapter/9.9")
        assert status == 404
        payload = json.loads(body)
        assert payload["code"] == "invalid_section"

    _with_server(run)


def test_index_lists_chapters():
    def run(base):
        status, body = _get(base, "/")
        assert status == 200
        assert "Interactive Chapters" in body
        assert "/learn?chapter=7.1" in body
        assert "Phosphorus-Containing Compounds" in body

    _with_server(run)


def test_ambiguous_response():
    def run(base):
        status, payload = _post(
            base,
            "/api/tutor",
            {"question": "invalid-citation ATP", "sectionId": "7.1"},
            session="ambiguous",
        )
        assert status == 200
        assert payload["status"] == "ambiguous", payload

    _with_server(run)


def test_insufficient_evidence_response():
    def run(base):
        status, payload = _post(
            base,
            "/api/tutor",
            {"question": "What does this say about cardiac action potentials?", "sectionId": "7.1"},
            session="insufficient",
        )
        assert status == 200
        assert payload["status"] == "insufficient_evidence", payload

    _with_server(run)


def test_model_error_response():
    original = server_app.ANSWER_QUESTION

    def fake_answer(*args, **kwargs):
        return CouncilResponse(
            request_id="test",
            status=ResponseStatus.MODEL_ERROR,
            answer="technical failure",
            cited_sources=(),
            metadata={"liveModelCalls": 0},
        )

    server_app.ANSWER_QUESTION = fake_answer
    try:
        def run(base):
            status, payload = _post(
                base,
                "/api/tutor",
                {"question": "What is ATP?", "sectionId": "7.1"},
                session="model-error",
            )
            assert status == 200
            assert payload["status"] == "model_error", payload

        _with_server(run)
    finally:
        server_app.ANSWER_QUESTION = original


def test_empty_question_rejection():
    def run(base):
        status, payload = _post(base, "/api/tutor", {"question": " ", "sectionId": "7.1"})
        assert status == 400
        assert payload["code"] == "empty_question"

    _with_server(run)


def test_invalid_section_rejection():
    def run(base):
        status, payload = _post(base, "/api/tutor", {"question": "What is ATP?", "sectionId": "7.2"})
        assert status == 400
        assert payload["code"] == "invalid_section"

    _with_server(run)


def test_malformed_json_rejection():
    def run(base):
        status, payload = _post(base, "/api/tutor", b"{not json")
        assert status == 400
        assert payload["code"] == "malformed_json"

    _with_server(run)


def test_api_key_not_exposed():
    def run(base):
        status, payload = _post(
            base,
            "/api/tutor",
            {"question": "What are the pKa values of phosphoric acid?", "sectionId": "7.1"},
            session="secret-check",
        )
        assert status == 200
        body = json.dumps(payload)
        assert "NVIDIA_API_KEY" not in body
        assert "Bearer" not in body
        assert "nvapi-" not in body.lower()

    _with_server(run)


def test_checkpoint_and_final_quiz_grade_section_71():
    def run(base):
        status, checkpoint = _post(
            base,
            "/api/checkpoint",
            {"sectionId": "7.1", "checkpointId": "cp-pka-order", "answer": "2.1, 7.2, 12.4"},
        )
        assert status == 200
        assert checkpoint["evaluation"]["result"] == "correct"
        assert checkpoint["learnerState"]["chapter"] == "7.1"
        assert "cp-pka-order" in checkpoint["learnerState"]["completedCheckpoints"]

        status, quiz = _post(
            base,
            "/api/final-quiz",
            {
                "sectionId": "7.1",
                "answers": {
                    "quiz-triprotic": "a",
                    "quiz-pyro-dg": "a",
                    "quiz-atp": "a",
                },
                "learnerState": checkpoint["learnerState"],
            },
        )
        assert status == 200
        assert quiz["score"] == {"correct": 3, "total": 3}
        assert all(result["result"] == "correct" for result in quiz["results"])

    _with_server(run)


def test_raw_path_not_exposed():
    def run(base):
        status, payload = _post(
            base,
            "/api/tutor",
            {"question": "What are the pKa values of phosphoric acid?", "sectionId": "7.1"},
            session="raw-path",
        )
        assert status == 200
        body = json.dumps(payload).lower()
        assert "raw/" not in body
        assert "mcat biochemistry review chapter 7.txt" not in body

    _with_server(run)


def test_frontend_renders_citations():
    html = (REPO / "server" / "static" / "chapter.html").read_text("utf-8")
    js = (REPO / "server" / "static" / "chapter.js").read_text("utf-8")
    assert "messages" in html
    assert "citedSources" in js
    assert "source.sourceId" in js
    assert "source.label" in js


def test_frontend_handles_loading_and_error_states():
    html = (REPO / "server" / "static" / "chapter.html").read_text("utf-8")
    js = (REPO / "server" / "static" / "chapter.js").read_text("utf-8")
    assert "loadingIndicator" in html
    assert "errorState" in html
    assert "setBusy(true)" in js
    assert "model_error" in js
    assert "Retry" in js


def test_frontend_uses_url_chapter_and_per_chapter_state():
    js = (REPO / "server" / "static" / "chapter.js").read_text("utf-8")
    assert 'params.get("chapter") || "7.1"' in js
    assert '"chapter-" + chapterId + "-state"' in js
    assert "sectionId: chapterId" in js


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
