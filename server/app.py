#!/usr/bin/env python3
"""Local interactive chapter tutor website and API.

This server is intentionally local-only by default. It serves the learner page
and `/api/tutor` from the same origin so the NVIDIA API key never reaches the
browser.
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).resolve().parent / "static"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from council.config import CouncilConfig  # noqa: E402
from council.phase1 import answer_question  # noqa: E402
from council.router import route_message  # noqa: E402
from server.interactive_chapter import (  # noqa: E402
    build_tutor_context,
    evaluate_checkpoint,
    get_chapter,
    grade_final_quiz,
    list_chapters,
    update_progress,
)

ANSWER_QUESTION = answer_question

HOST = "127.0.0.1"
PORT = 8765
MAX_BODY_BYTES = 12000
MAX_QUESTION_CHARS = 500
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 8

_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}
_inflight_lock = threading.Lock()
_inflight_sessions: set[str] = set()
_global_model_slots = threading.BoundedSemaphore(value=2)

LOGGER = logging.getLogger("section71_server")


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _error(status: int, code: str, message: str) -> dict[str, str]:
    return {"status": "error", "code": code, "message": message}


def _invalid_section(section_id: Any) -> dict[str, str]:
    return _error(400, "invalid_section", f"Unknown sectionId {section_id!r}.")


def _client_id(handler: BaseHTTPRequestHandler) -> str:
    session = handler.headers.get("X-Session-ID", "").strip()
    if session:
        return f"session:{session[:80]}"
    return f"ip:{handler.client_address[0]}"


def _rate_limited(client_id: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        bucket = [
            at
            for at in _rate_buckets.get(client_id, [])
            if now - at <= RATE_LIMIT_WINDOW_SECONDS
        ]
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            _rate_buckets[client_id] = bucket
            return True
        bucket.append(now)
        _rate_buckets[client_id] = bucket
        return False


class Section71Handler(BaseHTTPRequestHandler):
    server_version = "MCATTutorLocal/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.info("request %s", {"client": self.client_address[0], "path": self.path})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            _json_response(self, HTTPStatus.OK, {"ok": True, "section": "7.1"})
            return
        if path == "/api/chapters":
            _json_response(self, HTTPStatus.OK, list_chapters())
            return
        if path.startswith("/api/chapter/"):
            section_id = path.removeprefix("/api/chapter/").strip()
            try:
                chapter = get_chapter(section_id)
            except KeyError:
                _json_response(self, HTTPStatus.NOT_FOUND, _invalid_section(section_id))
                return
            _json_response(self, HTTPStatus.OK, chapter)
            return
        if path == "/":
            self._serve_repo_file(REPO / "app" / "index.html")
            return
        if path == "/app/index.html":
            self._serve_repo_file(REPO / "app" / "index.html")
            return
        if path.startswith("/course-data/") and path.endswith(".json"):
            requested = path.removeprefix("/course-data/").strip("/")
            self._serve_repo_file(REPO / "course-data" / requested, root=REPO / "course-data")
            return
        if path in {"/learn", "/learn/", "/section-7-1", "/section-7-1.html"}:
            self._serve_static("chapter.html")
            return
        if path in {"/chapter.js", "/section-7-1.js"}:
            self._serve_static("chapter.js")
            return
        if path in {"/chapter.css", "/section-7-1.css"}:
            self._serve_static("chapter.css")
            return
        _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "not_found", "Not found."))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/checkpoint":
            self._handle_checkpoint()
            return
        if path == "/api/final-quiz":
            self._handle_final_quiz()
            return
        if path != "/api/tutor":
            _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "not_found", "Not found."))
            return

        client_id = _client_id(self)
        if _rate_limited(client_id):
            _json_response(
                self,
                HTTPStatus.TOO_MANY_REQUESTS,
                _error(429, "rate_limited", "Please wait before asking another question."),
            )
            return

        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _error(400, "invalid_content_type", "Request body must be JSON."),
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _error(400, "invalid_body", "Request body is missing or too large."),
            )
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _error(400, "malformed_json", "Request body must be valid JSON."),
            )
            return

        if not isinstance(payload, dict):
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _error(400, "malformed_json", "Request body must be a JSON object."),
            )
            return

        question = payload.get("question")
        section_id = payload.get("sectionId")
        if not isinstance(section_id, str):
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _invalid_section(section_id),
            )
            return
        try:
            get_chapter(section_id)
        except KeyError:
            _json_response(self, HTTPStatus.BAD_REQUEST, _invalid_section(section_id))
            return
        if not isinstance(question, str) or not question.strip():
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _error(400, "empty_question", "Question is required."),
            )
            return
        question = question.strip()
        if len(question) > MAX_QUESTION_CHARS:
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _error(400, "question_too_long", "Question is too long."),
            )
            return

        acquired_session = False
        with _inflight_lock:
            if client_id in _inflight_sessions:
                _json_response(
                    self,
                    HTTPStatus.CONFLICT,
                    _error(409, "request_in_flight", "A tutor request is already running."),
                )
                return
            _inflight_sessions.add(client_id)
            acquired_session = True

        acquired_global = _global_model_slots.acquire(blocking=False)
        if not acquired_global:
            if acquired_session:
                with _inflight_lock:
                    _inflight_sessions.discard(client_id)
            _json_response(
                self,
                HTTPStatus.TOO_MANY_REQUESTS,
                _error(429, "server_busy", "The local tutor is busy. Try again shortly."),
            )
            return

        try:
            config = CouncilConfig.from_env(REPO)
            # Route first: greetings/chit-chat/navigation return a conversational
            # reply with no model call. Factual messages delegate to the gated
            # pipeline (ANSWER_QUESTION) unchanged — read at call time so tests
            # that monkeypatch it still take effect.
            learner_state = payload.get("learnerState") if isinstance(payload.get("learnerState"), dict) else None
            response_dict = route_message(
                question,
                answer_fn=ANSWER_QUESTION,
                learner_state=build_tutor_context(learner_state, section_id),
                section_id=section_id,
                config=config,
                logger=LOGGER,
            )
            _json_response(self, HTTPStatus.OK, response_dict)
        finally:
            _global_model_slots.release()
            with _inflight_lock:
                _inflight_sessions.discard(client_id)

    def _read_json_body(self) -> tuple[dict[str, Any] | None, tuple[int, dict[str, str]] | None]:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            return None, (HTTPStatus.BAD_REQUEST, _error(400, "invalid_content_type", "Request body must be JSON."))
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            return None, (HTTPStatus.BAD_REQUEST, _error(400, "invalid_body", "Request body is missing or too large."))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, (HTTPStatus.BAD_REQUEST, _error(400, "malformed_json", "Request body must be valid JSON."))
        if not isinstance(payload, dict):
            return None, (HTTPStatus.BAD_REQUEST, _error(400, "malformed_json", "Request body must be a JSON object."))
        return payload, None

    def _handle_checkpoint(self) -> None:
        payload, error = self._read_json_body()
        if error is not None:
            _json_response(self, error[0], error[1])
            return
        assert payload is not None
        chapter_id = payload.get("sectionId")
        if not isinstance(chapter_id, str):
            _json_response(self, HTTPStatus.BAD_REQUEST, _invalid_section(chapter_id))
            return
        try:
            get_chapter(chapter_id)
        except KeyError:
            _json_response(self, HTTPStatus.BAD_REQUEST, _invalid_section(chapter_id))
            return
        checkpoint_id = payload.get("checkpointId")
        if not isinstance(checkpoint_id, str) or not checkpoint_id:
            _json_response(self, HTTPStatus.BAD_REQUEST, _error(400, "invalid_checkpoint", "checkpointId is required."))
            return
        try:
            evaluation = evaluate_checkpoint(checkpoint_id, payload.get("answer"), section_id=chapter_id)
        except KeyError:
            _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "checkpoint_not_found", "Checkpoint not found."))
            return
        learner_state = payload.get("learnerState") if isinstance(payload.get("learnerState"), dict) else None
        next_state = update_progress(learner_state, evaluation["sectionId"], checkpoint_id, evaluation, chapter_id)
        _json_response(self, HTTPStatus.OK, {"evaluation": evaluation, "learnerState": next_state})

    def _handle_final_quiz(self) -> None:
        payload, error = self._read_json_body()
        if error is not None:
            _json_response(self, error[0], error[1])
            return
        assert payload is not None
        chapter_id = payload.get("sectionId")
        if not isinstance(chapter_id, str):
            _json_response(self, HTTPStatus.BAD_REQUEST, _invalid_section(chapter_id))
            return
        try:
            get_chapter(chapter_id)
        except KeyError:
            _json_response(self, HTTPStatus.BAD_REQUEST, _invalid_section(chapter_id))
            return
        answers = payload.get("answers")
        if not isinstance(answers, dict):
            _json_response(self, HTTPStatus.BAD_REQUEST, _error(400, "invalid_answers", "answers must be an object."))
            return
        learner_state = payload.get("learnerState") if isinstance(payload.get("learnerState"), dict) else None
        _json_response(self, HTTPStatus.OK, grade_final_quiz(answers, learner_state, chapter_id))

    def _serve_index(self) -> None:
        links = "\n".join(
            f'          <li><a href="/learn?chapter={chapter["id"]}">Section {chapter["id"]}: {chapter["title"]}</a></li>'
            for chapter in list_chapters()
        )
        body = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MCAT Tutor Chapters</title>
    <link rel="stylesheet" href="/chapter.css">
  </head>
  <body>
    <main class="index-shell">
      <section class="lesson-panel" aria-labelledby="chapters-title">
        <p class="eyebrow">MCAT Biochemistry Review</p>
        <h1 id="chapters-title">Interactive Chapters</h1>
        <ul class="chapter-list">
{links}
        </ul>
      </section>
    </main>
  </body>
</html>
"""
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _serve_repo_file(self, path: Path, root: Path | None = None) -> None:
        root = (root or REPO).resolve()
        path = path.resolve()
        if root not in path.parents and path != root:
            _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "not_found", "Not found."))
            return
        if not path.exists() or not path.is_file():
            _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "not_found", "Not found."))
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, filename: str) -> None:
        path = (STATIC_ROOT / filename).resolve()
        if STATIC_ROOT.resolve() not in path.parents and path != STATIC_ROOT.resolve():
            _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "not_found", "Not found."))
            return
        if not path.exists() or not path.is_file():
            _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "not_found", "Not found."))
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Section71Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local interactive chapter tutor website.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    server = make_server(args.host, args.port)
    print(f"MCAT tutor running at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
