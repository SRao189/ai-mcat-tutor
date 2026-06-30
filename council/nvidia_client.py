"""OpenAI-compatible NVIDIA Build client with safe logging."""

from __future__ import annotations

import json
import ssl
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
                    req,
                    timeout=self.config.timeout_seconds,
                    context=self._ssl_context(),
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
            except urllib.error.HTTPError as exc:
                last_error = self._safe_http_error(exc)
            except urllib.error.URLError as exc:
                last_error = self._safe_url_error(exc)
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

    def _safe_http_error(self, exc: urllib.error.HTTPError) -> str:
        reason = f"http-{exc.code}"
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return reason

        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            provider_type = str(error.get("type") or "").strip()
            provider_code = str(error.get("code") or "").strip()
            details = [
                item
                for item in (provider_type, provider_code)
                if item and "key" not in item.lower() and "token" not in item.lower()
            ]
            if details:
                return reason + ":" + ":".join(details)
        return reason

    def _safe_url_error(self, exc: urllib.error.URLError) -> str:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, BaseException):
            verify_message = getattr(reason, "verify_message", None)
            if verify_message:
                return f"{reason.__class__.__name__}:{verify_message}"
            return reason.__class__.__name__
        if isinstance(reason, str) and reason.strip():
            text = reason.strip()
            red_flags = ("key", "token", "secret", "bearer")
            if any(flag in text.lower() for flag in red_flags):
                return "url-error"
            return text[:80]
        return exc.__class__.__name__

    def _ssl_context(self) -> ssl.SSLContext | None:
        try:
            import truststore  # type: ignore
        except ImportError:
            return None
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
