"""Tests for the Thermodynamics interactive chapter.

Run: python -m tests.test_thermodynamics_chapter
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

from council.config import CouncilConfig  # noqa: E402
from council.phase1 import answer_question  # noqa: E402
from council.schema import ResponseStatus  # noqa: E402
from council.source_store import ThermodynamicsPassageStore, passage_hash  # noqa: E402
from server import app as server_app  # noqa: E402
from server.interactive_chapter import get_chapter, validate_chapter_schema  # noqa: E402


MOCK_CONFIG = CouncilConfig(
    base_url="",
    api_key=None,
    tutor_model="mock",
    embed_model=None,
    rerank_model=None,
    safety_model=None,
    mock_mode=True,
)


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


def _post(base: str, path: str, payload, *, session: str = "thermo-test"):
    data = json.dumps(payload).encode("utf-8")
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


def test_thermodynamics_chapter_registered_and_served():
    chapter = get_chapter("thermo")
    assert chapter["sectionId"] == "thermo"
    assert chapter["title"] == "Thermodynamics"
    assert len(chapter["learningObjectives"]) >= 3
    assert len(chapter["sections"]) >= 3
    assert len(chapter["workedExamples"]) >= 1
    assert len(chapter["finalQuiz"]["questions"]) >= 3
    assert validate_chapter_schema(chapter) == []

    def run(base):
        status, body = _get(base, "/api/chapter/thermo")
        assert status == 200
        payload = json.loads(body)
        assert payload["sectionId"] == "thermo"
        assert payload["sections"][0]["explanationBlocks"]
        assert payload["sections"][0]["keyIdeaCards"]
        assert payload["sections"][0]["checkpoints"][0]["sourceIds"] == ["thermo-passage-01"]

    _with_server(run)


def test_thermodynamics_checkpoint_grades_correct_and_wrong_answers():
    def run(base):
        status, correct = _post(
            base,
            "/api/checkpoint",
            {
                "sectionId": "thermo",
                "checkpointId": "cp-thermo-dg-sign",
                "answer": "a",
            },
            session="thermo-cp-correct",
        )
        assert status == 200
        assert correct["evaluation"]["result"] == "correct"
        assert correct["evaluation"]["completed"] is True
        assert correct["learnerState"]["chapter"] == "thermo"

        status, wrong = _post(
            base,
            "/api/checkpoint",
            {
                "sectionId": "thermo",
                "checkpointId": "cp-thermo-dg-sign",
                "answer": "b",
            },
            session="thermo-cp-wrong",
        )
        assert status == 200
        assert wrong["evaluation"]["result"] == "incorrect"
        assert wrong["evaluation"]["detectedMisconception"] == "delta_g_sign_reversal"
        assert "spontaneous and exergonic" in wrong["evaluation"]["explanation"]

    _with_server(run)


def test_thermodynamics_final_quiz_grades():
    def run(base):
        status, quiz = _post(
            base,
            "/api/final-quiz",
            {
                "sectionId": "thermo",
                "answers": {
                    "quiz-thermo-dg-sign": "a",
                    "quiz-thermo-standard-equilibrium": "a",
                    "quiz-thermo-q-direction": "a",
                    "quiz-thermo-keq-rate": "a",
                },
            },
            session="thermo-quiz",
        )
        assert status == 200
        assert quiz["score"] == {"correct": 4, "total": 4}
        assert all(result["result"] == "correct" for result in quiz["results"])
        assert quiz["learnerState"]["chapter"] == "thermo"

    _with_server(run)


def test_thermodynamics_passage_store_hashes_match():
    store = ThermodynamicsPassageStore()
    passages = store.load()
    assert len(passages) == 6
    assert {passage.section for passage in passages} == {"thermo"}
    for passage in passages:
        assert passage.source_hash == passage_hash(passage.text)


def test_thermodynamics_tutor_uses_thermo_passage_store():
    response = answer_question(
        "What is Gibbs free energy?",
        section_id="thermo",
        config=MOCK_CONFIG,
    )
    assert response.status == ResponseStatus.VERIFIED, response.to_dict()
    assert response.cited_sources
    assert response.cited_sources[0]["sourceId"] == "thermo-passage-03"
    assert "Gibbs free energy" in response.answer


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
