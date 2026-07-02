"""Tests for the conversational intent router above the verified pipeline.

Run: python -m tests.test_router
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

from council import router  # noqa: E402
from council.router import (  # noqa: E402
    CASUAL,
    CLARIFICATION,
    FACTUAL,
    GREETING,
    NAVIGATION,
    classify,
    route_message,
)
from council.schema import CouncilResponse, ResponseStatus  # noqa: E402
from server import app as server_app  # noqa: E402


# ---------------- classifier ----------------

def test_classify_greetings():
    for text in ["hi", "Hello!", "hey", "good morning", "yo", "what's up"]:
        assert classify(text) == GREETING, text


def test_classify_casual():
    for text in ["thanks", "thank you", "ok", "cool", "bye"]:
        assert classify(text) == CASUAL, text


def test_classify_navigation():
    for text in ["go to ATP", "open section 7.2", "next section"]:
        assert classify(text) == NAVIGATION, text


def test_classify_clarification():
    for text in ["why?", "explain that more simply", "I don't understand", "huh"]:
        assert classify(text) == CLARIFICATION, text


def test_classify_factual_default():
    # Real questions — including a "why" question with real content — stay factual.
    for text in [
        "What are the pKa values of phosphoric acid?",
        "Why is the second pKa near physiological pH?",
        "what do you mean by the second pKa?",
        "Tell me about ATP",
        "",
    ]:
        assert classify(text) == FACTUAL, text


# ---------------- router delegation ----------------

def test_route_greeting_does_not_call_factual_pipeline():
    calls = []

    def boom(*_a, **_k):
        calls.append("called")
        raise AssertionError("factual pipeline must not run for a greeting")

    out = route_message("hi", answer_fn=boom)
    assert out["status"] == "conversational"
    assert not calls
    assert out["metadata"]["suggestions"]
    assert out["citedSources"] == []
    assert out["gateOutcomes"] == []


def test_route_factual_delegates():
    seen = {}

    def fake(question, **kwargs):
        seen["question"] = question
        return CouncilResponse(
            request_id="t", status=ResponseStatus.VERIFIED, answer="ok",
            cited_sources=(), metadata={"liveModelCalls": 1},
        )

    out = route_message("What are the pKa values of phosphoric acid?", answer_fn=fake)
    assert out["status"] == "verified"
    assert seen["question"].startswith("What are the pKa")


# ---------------- server behavior ----------------

def _start_server():
    httpd = server_app.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def _post(base, payload, *, session="router-test"):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/tutor", data=data, method="POST",
        headers={"Content-Type": "application/json", "X-Session-ID": session},
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


def test_server_greeting_is_conversational_and_skips_model():
    # Record any factual-pipeline call; a greeting must not trigger one.
    original = server_app.ANSWER_QUESTION
    calls = []

    def recorder(*a, **k):
        calls.append(1)
        return original(*a, **k)

    server_app.ANSWER_QUESTION = recorder
    try:
        def run(base):
            status, payload = _post(base, {"question": "hi", "sectionId": "7.1"}, session="greet")
            assert status == 200
            assert payload["status"] == "conversational", payload
            assert payload["status"] != "insufficient_evidence"
            assert payload["metadata"]["suggestions"]
            assert payload["metadata"]["liveModelCalls"] == 0
            assert not calls, "greeting reached the factual pipeline"

        _with_server(run)
    finally:
        server_app.ANSWER_QUESTION = original


def test_server_factual_still_verified_with_citation():
    def run(base):
        status, payload = _post(
            base, {"question": "What are the pKa values of phosphoric acid?", "sectionId": "7.1"},
            session="fact",
        )
        assert status == 200
        assert payload["status"] == "verified", payload
        assert payload["citedSources"][0]["sourceId"] == "chapter-7-1-passage-01"

    _with_server(run)


def test_server_greeting_hides_gate_internals():
    def run(base):
        status, payload = _post(base, {"question": "hello", "sectionId": "7.1"}, session="greet2")
        assert status == 200
        body = json.dumps(payload).lower()
        assert "gate2" not in body
        assert "gate3" not in body

    _with_server(run)


# ---------------- frontend relabeling ----------------

def test_frontend_relabels_and_gates_developer_details():
    js = (REPO / "server" / "static" / "chapter.js").read_text("utf-8")
    html = (REPO / "server" / "static" / "chapter.html").read_text("utf-8")
    # conversational handled + suggestions
    assert "conversational" in js
    assert "addSuggestions" in js
    # learner-friendly next action, not raw snake_case
    assert "humanizeAction" in js
    assert "NEXT_ACTION_LABELS" in js
    assert '"Next: " + response.recommendedNextAction' not in js
    # gate details only behind the debug toggle
    assert "debugToggle" in html
    assert "debugOn" in js
    assert "addDebugDetails" in js


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
