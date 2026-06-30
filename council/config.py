"""Safe environment handling for the NVIDIA Council foundation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ALLOWED_ENV_KEYS = {
    "NVIDIA_API_KEY",
    "NVIDIA_BASE_URL",
    "NVIDIA_TUTOR_MODEL",
    "NVIDIA_EMBED_MODEL",
    "NVIDIA_RERANK_MODEL",
    "NVIDIA_SAFETY_MODEL",
    "NVIDIA_MOCK_MODE",
}

REQUIRED_LIVE_KEYS = (
    "NVIDIA_API_KEY",
    "NVIDIA_BASE_URL",
    "NVIDIA_TUTOR_MODEL",
)


class CouncilConfigError(RuntimeError):
    """Raised when required configuration is missing."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            "Missing required NVIDIA Council environment variables: "
            + ", ".join(missing)
        )


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_ENV_KEYS:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def load_allowed_environment(repo_root: Path | None = None) -> dict[str, str]:
    """Load only explicitly allowed keys from process env and local .env."""
    root = repo_root or Path.cwd()
    values = _parse_env_file(root / ".env")
    for key in ALLOWED_ENV_KEYS:
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CouncilConfig:
    base_url: str
    api_key: str | None
    tutor_model: str | None
    embed_model: str | None
    rerank_model: str | None
    safety_model: str | None
    mock_mode: bool
    timeout_seconds: float = 30.0
    max_retries: int = 1
    max_concurrency: int = 2
    max_tokens: int = 900

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "CouncilConfig":
        env = load_allowed_environment(repo_root)
        mock_mode = _truthy(env.get("NVIDIA_MOCK_MODE"))
        base_url = env.get("NVIDIA_BASE_URL", "").rstrip("/")
        return cls(
            base_url=base_url,
            api_key=env.get("NVIDIA_API_KEY"),
            tutor_model=env.get("NVIDIA_TUTOR_MODEL"),
            embed_model=env.get("NVIDIA_EMBED_MODEL"),
            rerank_model=env.get("NVIDIA_RERANK_MODEL"),
            safety_model=env.get("NVIDIA_SAFETY_MODEL"),
            mock_mode=mock_mode,
        )

    def missing_live_keys(self) -> list[str]:
        if self.mock_mode:
            return []
        values = {
            "NVIDIA_API_KEY": self.api_key,
            "NVIDIA_BASE_URL": self.base_url,
            "NVIDIA_TUTOR_MODEL": self.tutor_model,
        }
        return [key for key in REQUIRED_LIVE_KEYS if not values.get(key)]

    def require_live_ready(self) -> None:
        missing = self.missing_live_keys()
        if missing:
            raise CouncilConfigError(missing)

    def startup_status(self) -> dict[str, object]:
        """Report names only. Never include values."""
        return {
            "mockMode": self.mock_mode,
            "missing": self.missing_live_keys(),
            "configured": [
                key
                for key, value in {
                    "NVIDIA_BASE_URL": self.base_url,
                    "NVIDIA_TUTOR_MODEL": self.tutor_model,
                    "NVIDIA_EMBED_MODEL": self.embed_model,
                    "NVIDIA_RERANK_MODEL": self.rerank_model,
                    "NVIDIA_SAFETY_MODEL": self.safety_model,
                }.items()
                if value
            ],
        }
