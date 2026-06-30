"""OpenAI-compatible NVIDIA Build client with safe logging."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

from .config import CouncilConfig


class NvidiaClientError(RuntimeError):
    def __init__(self, message: str, *, request_id: str | None = None) -> None:
        self.request_id = request_id
        super().__init__(message)


@dataclass(frozen=True)
class NvidiaChatResult:
    request_id: str
    content: str
    latency_ms: int
    model: str
    status_code: int


class NvidiaClient:
    def __init__(self, config: CouncilConfig, logger: Any | None = None) -> None:
        self.config = config
        self.logger = logger

    def chat_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        request_id: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> NvidiaChatResult:
        self.config.require_live_ready()
        rid = request_id or uuid.uuid4().hex
        url = f"{self.config.base_url}/chat/completions"
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        last_error: str | None = None
        for attempt in range(self.config.max_retries + 1):
            started = time.perf_counter()
            try:
                payload = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(
                    req, timeout=self.config.timeout_seconds
                ) as response:
                    raw = response.read().decode("utf-8")
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    data = json.loads(raw)
                    content = data["choices"][0]["message"]["content"]
                    self._log(
                        "nvidia_call",
                        {
                            "requestId": rid,
                            "model": model,
                            "latencyMs": latency_ms,
                            "statusCode": response.status,
                            "attempt": attempt,
                        },
                    )
                    return NvidiaChatResult(
                        request_id=rid,
                        content=content,
                        latency_ms=latency_ms,
                        model=model,
                        status_code=response.status,
                    )
            except TimeoutError:
                last_error = "timeout"
            except urllib.error.URLError as exc:
                last_error = exc.reason.__class__.__name__
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
                last_error = "malformed-response"

            self._log(
                "nvidia_call_error",
                {
                    "requestId": rid,
                    "model": model,
                    "attempt": attempt,
                    "error": last_error,
                },
            )

        raise NvidiaClientError(
            f"NVIDIA request failed safely: {last_error or 'unknown'}",
            request_id=rid,
        )

    def _log(self, event: str, data: dict[str, Any]) -> None:
        if self.logger is None:
            return
        safe = {
            key: value
            for key, value in data.items()
            if "key" not in key.lower() and "secret" not in key.lower()
        }
        self.logger.info(event, extra=safe)
