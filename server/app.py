#!/usr/bin/env python3
"""Local Section 7.1 tutor website and API.

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

ANSWER_QUESTION = answer_question

HOST = "127.0.0.1"
PORT = 8765
MAX_BODY_BYTES = 4096
MAX_QUESTION_CHARS = 500
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 8

_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}
_inflight_lock = threading.Lock()
_inflight_sessions: set[str] = set()
_global_model_slots = threading.BoundedSemaphore(value=2)

LOGGER = logging.getLogger("section71_server")


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _error(status: int, code: str, message: str) -> dict[str, str]:
    return {"status": "error", "code": code, "message": message}


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
        if path in {"/", "/section-7-1", "/section-7-1.html"}:
            self._serve_static("section-7-1.html")
            return
        if path == "/section-7-1.js":
            self._serve_static("section-7-1.js")
            return
        if path == "/section-7-1.css":
            self._serve_static("section-7-1.css")
            return
        _json_response(self, HTTPStatus.NOT_FOUND, _error(404, "not_found", "Not found."))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
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
        if section_id != "7.1":
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                _error(400, "invalid_section", "Only sectionId 7.1 is supported in this phase."),
            )
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
            response = ANSWER_QUESTION(
                question,
                learner_state=payload.get("learnerState") if isinstance(payload.get("learnerState"), dict) else None,
                config=config,
                logger=LOGGER,
            )
            _json_response(self, HTTPStatus.OK, response.to_dict())
        finally:
            _global_model_slots.release()
            with _inflight_lock:
                _inflight_sessions.discard(client_id)

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
    parser = argparse.ArgumentParser(description="Run the local Section 7.1 tutor website.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    server = make_server(args.host, args.port)
    print(f"Section 7.1 tutor running at http://{args.host}:{args.port}/section-7-1.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
