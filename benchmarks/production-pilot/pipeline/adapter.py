"""Model provider adapter.

This is the ONLY module that knows about Ollama. To move from local Ollama to a
hosted/containerized endpoint, reimplement these four functions against the new
provider; nothing else in the pipeline changes. See README.md "Portability".
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from typing import Any

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS = "http://localhost:11434/api/tags"

# Socket read timeout must cover cold load + prompt prefill before the FIRST
# streamed token (no bytes flow during prefill). Once tokens flow, gaps are tiny,
# so this doubles as a mid-stream stall guard.
STALL_TIMEOUT = 300
OVERALL_TIMEOUT = 1500
HEARTBEAT_INTERVAL = 30


def model_available(model: str) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=15) as response:
            tags = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False
    return model in {entry.get("name") for entry in tags.get("models", [])}


def canary(model: str) -> bool:
    """Tiny structured generation to confirm the model loads and responds."""
    payload = {
        "model": model,
        "prompt": 'Reply with the JSON object {"ok": true} and nothing else.',
        "stream": False,
        "think": False,
        "format": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
        "keep_alive": "5m",
        "options": {"temperature": 0, "seed": 42, "num_predict": 16},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            outer = json.loads(response.read().decode("utf-8", errors="replace"))
        return json.loads(outer.get("response", "{}")).get("ok") is True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def unload(model: str) -> None:
    try:
        subprocess.run(
            ["ollama", "stop", model],
            capture_output=True, text=True, timeout=30, check=False,
        )
        print(f"  Unloaded model: {model}")
    except Exception as exc:  # noqa: BLE001 - cleanup must never raise
        print(f"  Model unload skipped: {exc}")


def generate_structured(
    model: str,
    prompt: str,
    schema: dict[str, Any],
    num_ctx: int,
    label: str,
    num_predict: int | None = None,
    read_timeout: int | None = None,
) -> dict[str, Any]:
    """Stream a schema-constrained generation, emitting a heartbeat >= every 30s.

    Returns {"raw": str, "meta": dict, "elapsed": float}. Raises on stall/timeout.
    Deterministic: temperature 0, seed 42. num_predict hard-caps output tokens so
    a single call cannot run away (bounded-component generation).
    """
    options: dict[str, Any] = {"temperature": 0, "seed": 42, "num_ctx": num_ctx}
    if num_predict is not None:
        options["num_predict"] = num_predict
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "think": False,
        "format": schema,
        "keep_alive": 0,
        "options": options,
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    state = {"tokens": 0, "last_token": time.perf_counter(), "stage": "LOADING_MODEL"}
    lock = threading.Lock()
    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(HEARTBEAT_INTERVAL):
            with lock:
                toks, last, stage = state["tokens"], state["last_token"], state["stage"]
            idle = time.perf_counter() - last
            if toks == 0:
                status = "loading/prefill, no tokens yet (normal)"
            elif idle < HEARTBEAT_INTERVAL:
                status = "running"
            else:
                status = f"STALLED (no token {idle:.0f}s)"
            print(f"[{time.strftime('%H:%M:%S')}] {label} {stage} - {toks} tokens, {status}")

    raw_parts: list[str] = []
    meta: dict[str, Any] = {}
    started = time.perf_counter()
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(request, timeout=read_timeout or STALL_TIMEOUT) as response:
            with lock:
                state["stage"] = "GENERATING"
            for line in response:
                if not line.strip():
                    continue
                chunk = json.loads(line.decode("utf-8", errors="replace"))
                piece = chunk.get("response", "")
                if piece:
                    raw_parts.append(piece)
                    with lock:
                        state["tokens"] += 1
                        state["last_token"] = time.perf_counter()
                if chunk.get("done"):
                    meta = chunk
                    break
                if time.perf_counter() - started > OVERALL_TIMEOUT:
                    raise TimeoutError(f"exceeded overall timeout ({OVERALL_TIMEOUT}s)")
    finally:
        stop.set()
        thread.join(timeout=1)

    return {
        "raw": "".join(raw_parts).strip(),
        "meta": meta,
        "elapsed": round(time.perf_counter() - started, 3),
    }
