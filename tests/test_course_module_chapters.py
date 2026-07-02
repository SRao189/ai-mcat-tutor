"""Tests for course-data-backed interactive chapters.

Run: python -m tests.test_course_module_chapters
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

from council.course_modules import MODULE_BY_SECTION  # noqa: E402
from council.source_store import passage_hash, passage_store_for_section  # noqa: E402
from server import app as server_app  # noqa: E402
from server.interactive_chapter import get_chapter, validate_chapter_schema  # noqa: E402


EXPECTED_TITLES = {
    "kinetics": "Kinetics and Activation Energy",
    "redox": "Oxidation and Reduction (Redox)",
    "acids-bases": "Acids and Bases",
    "chapter-3-summary": "Chapter 3: Biochemistry Basics — Summary",
}


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


def _post(base: str, path: str, payload, *, session: str = "course-module-test"):
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


def test_course_modules_registered_with_valid_schema():
    assert set(MODULE_BY_SECTION) == set(EXPECTED_TITLES)
    for section_id, title in EXPECTED_TITLES.items():
        chapter = get_chapter(section_id)
        assert chapter["sectionId"] == section_id
        assert chapter["title"] == title
        assert chapter["learningObjectives"]
        assert chapter["sections"]
        assert chapter["workedExamples"]
        assert chapter["finalQuiz"]["questions"]
        assert validate_chapter_schema(chapter) == []


def test_course_module_passage_hashes_match():
    for section_id in EXPECTED_TITLES:
        passages = passage_store_for_section(section_id).load()
        assert passages
        assert {passage.section for passage in passages} == {section_id}
        for passage in passages:
            assert passage.source_hash == passage_hash(passage.text)


def test_course_modules_are_served_and_listed():
    def run(base):
        status, body = _get(base, "/api/chapters")
        assert status == 200
        listed = json.loads(body)
        for section_id, title in EXPECTED_TITLES.items():
            assert {"id": section_id, "title": title} in listed
            status, body = _get(base, f"/api/chapter/{section_id}")
            assert status == 200
            payload = json.loads(body)
            assert payload["sectionId"] == section_id
            assert payload["sections"][0]["checkpoints"]

    _with_server(run)


def test_course_module_checkpoint_and_quiz_grade():
    def run(base):
        for section_id in EXPECTED_TITLES:
            chapter = get_chapter(section_id)
            checkpoint = chapter["sections"][0]["checkpoints"][0]
            if checkpoint["type"] == "multiple_choice":
                answer = checkpoint["answer"]
            else:
                answer = " ".join(group[0] for group in checkpoint["acceptedTerms"])
            status, checkpoint_result = _post(
                base,
                "/api/checkpoint",
                {
                    "sectionId": section_id,
                    "checkpointId": checkpoint["id"],
                    "answer": answer,
                },
                session=f"{section_id}-checkpoint",
            )
            assert status == 200
            assert checkpoint_result["evaluation"]["result"] == "correct"
            assert checkpoint_result["learnerState"]["chapter"] == section_id

            answers = {
                question["id"]: question["answer"]
                for question in chapter["finalQuiz"]["questions"]
            }
            status, quiz = _post(
                base,
                "/api/final-quiz",
                {"sectionId": section_id, "answers": answers},
                session=f"{section_id}-quiz",
            )
            assert status == 200
            assert quiz["score"]["correct"] == quiz["score"]["total"]
            assert quiz["learnerState"]["chapter"] == section_id

    _with_server(run)


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
