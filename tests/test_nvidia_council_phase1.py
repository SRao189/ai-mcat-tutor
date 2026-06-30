"""Phase 1 NVIDIA Council tests.

Run: python -m tests.test_nvidia_council_phase1
No network calls are made; tests use NVIDIA_MOCK_MODE behavior.
"""

from __future__ import annotations

import io
import logging
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from council.config import CouncilConfig  # noqa: E402
from council.nvidia_client import NvidiaClientError  # noqa: E402
from council.phase1 import answer_question  # noqa: E402
from council.roles import TutorReasoner  # noqa: E402
from council.schema import Claim, RetrievalCandidate, ResponseStatus, TutorDraft  # noqa: E402
from council.source_store import Chapter71PassageStore  # noqa: E402
from council.verification import CouncilVerifier  # noqa: E402


MOCK_CONFIG = CouncilConfig(
    base_url="",
    api_key=None,
    tutor_model="mock",
    embed_model=None,
    rerank_model=None,
    safety_model=None,
    mock_mode=True,
)


def test_supported_question_returns_verified_answer():
    response = answer_question(
        "What are the pKas of phosphoric acid at physiological pH?",
        config=MOCK_CONFIG,
    )
    assert response.status == ResponseStatus.VERIFIED, response.to_dict()
    assert response.cited_sources
    assert "2.1" in response.answer


def test_unsupported_question_returns_insufficient_evidence():
    response = answer_question(
        "What does Section 7.1 say about cardiac action potentials?",
        config=MOCK_CONFIG,
    )
    assert response.status == ResponseStatus.INSUFFICIENT_EVIDENCE, response.to_dict()


def test_invalid_citation_fails():
    response = answer_question(
        "invalid-citation ATP",
        config=MOCK_CONFIG,
    )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any(o.reason == "invalid citation" for o in response.gate_outcomes)


def test_stale_source_fails():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "passages.json"
        original = (REPO / "council" / "data" / "chapter_7_1_passages.json").read_text("utf-8")
        path.write_text(original.replace("2.1, 7.2, and 12.4", "2.1, 7.2, and 13.4"), encoding="utf-8")
        verifier = CouncilVerifier(Chapter71PassageStore(path))
        response = answer_question(
            "What are the pKas of phosphoric acid?",
            config=MOCK_CONFIG,
            verifier=verifier,
        )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any(o.gate == "stale-source" for o in response.gate_outcomes)


def test_contradictory_numeric_claim_fails():
    response = answer_question(
        "wrong-number pyrophosphate free energy",
        config=MOCK_CONFIG,
    )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any("numeric" in o.reason for o in response.gate_outcomes)


class TimeoutReasoner(TutorReasoner):
    def answer(
        self,
        *,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        learner_state: dict | None,
        request_id: str,
    ):
        raise NvidiaClientError("NVIDIA request failed safely: timeout")


def test_model_timeout_fails_safely():
    response = answer_question(
        "What is ATP?",
        config=MOCK_CONFIG,
        reasoner=TimeoutReasoner(),
    )
    assert response.status == ResponseStatus.MODEL_ERROR, response.to_dict()
    assert "failed safely" in response.answer


def test_missing_api_key_gives_safe_configuration_error():
    live_config = CouncilConfig(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=None,
        tutor_model="nvidia/example",
        embed_model=None,
        rerank_model=None,
        safety_model=None,
        mock_mode=False,
    )
    response = answer_question("What is ATP?", config=live_config)
    assert response.status == ResponseStatus.MODEL_ERROR, response.to_dict()
    assert response.metadata["missing"] == ["NVIDIA_API_KEY"]


def test_no_secret_appears_in_logs():
    secret = "sk-test-secret-value"
    live_config = CouncilConfig(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=secret,
        tutor_model="nvidia/example",
        embed_model=None,
        rerank_model=None,
        safety_model=None,
        mock_mode=True,
    )
    stream = io.StringIO()
    logger = logging.getLogger("test_nvidia_council")
    logger.handlers = []
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(stream))
    response = answer_question("What is ATP?", config=live_config, logger=logger)
    assert response.status == ResponseStatus.VERIFIED
    assert secret not in stream.getvalue()


def test_raw_source_paths_are_hidden():
    response = answer_question("What is ATP?", config=MOCK_CONFIG)
    payload = str(response.to_dict()).lower()
    assert "raw/" not in payload
    assert "mcat biochemistry review chapter 7.txt" not in payload


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
