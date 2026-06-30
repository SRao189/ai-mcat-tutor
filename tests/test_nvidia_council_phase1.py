"""Phase 1 NVIDIA Council tests.

Run: python -m tests.test_nvidia_council_phase1
No network calls are made; tests use NVIDIA_MOCK_MODE behavior.
"""

from __future__ import annotations

import io
import json
import logging
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from council.config import CouncilConfig  # noqa: E402
from council.nvidia_client import NvidiaClientError  # noqa: E402
from council.phase1 import answer_question  # noqa: E402
from council.roles import NvidiaTutorReasoner, TutorReasoner  # noqa: E402
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


def _parse_payload(payload):
    return NvidiaTutorReasoner(MOCK_CONFIG)._parse(json.dumps(payload))


def test_parse_uncertainty_false():
    draft = _parse_payload({"answer": "x", "claims": [], "uncertainty": False})
    assert draft.uncertainty == ()


def test_parse_uncertainty_true():
    draft = _parse_payload({"answer": "x", "claims": [], "uncertainty": True})
    assert draft.uncertainty == ("model_reported_unspecified_uncertainty",)


def test_parse_uncertainty_string():
    draft = _parse_payload(
        {"answer": "x", "claims": [], "uncertainty": "low confidence"}
    )
    assert draft.uncertainty == ("low confidence",)


def test_parse_uncertainty_empty_list():
    draft = _parse_payload({"answer": "x", "claims": [], "uncertainty": []})
    assert draft.uncertainty == ()


def test_parse_uncertainty_null():
    draft = _parse_payload({"answer": "x", "claims": [], "uncertainty": None})
    assert draft.uncertainty == ()


def test_parse_claims_string_instead_of_list_is_not_verified_shape():
    draft = _parse_payload(
        {
            "answer": "ATP stores energy.",
            "claims": "ATP stores energy.",
            "citationSourceIds": "chapter-7-1-passage-05",
        }
    )
    assert len(draft.claims) == 1
    assert draft.claims[0].text == "ATP stores energy."
    assert draft.claims[0].source_ids == ()


def test_parse_missing_fields_recover_to_empty_safe_defaults():
    draft = _parse_payload({})
    assert draft.answer == ""
    assert draft.claims == ()
    assert draft.citation_source_ids == ()
    assert draft.uncertainty == ()
    assert draft.insufficient_evidence is False
    assert draft.recommended_next_action == "review_cited_passages"


def test_parse_malformed_but_recoverable_payload():
    draft = _parse_payload(
        {
            "answer": 12,
            "claims": {
                "text": True,
                "sourceIds": "chapter-7-1-passage-01",
                "confidence": "high",
            },
            "citationSourceIds": False,
            "uncertainty": 7,
            "insufficientEvidence": "true",
            "recommendedNextAction": None,
        }
    )
    assert draft.answer == "12"
    assert draft.claims[0].text == "true"
    assert draft.claims[0].source_ids == ("chapter-7-1-passage-01",)
    assert draft.claims[0].confidence is None
    assert draft.citation_source_ids == ()
    assert draft.uncertainty == ("7",)
    assert draft.insufficient_evidence is True
    assert draft.recommended_next_action == "review_cited_passages"


def test_unrecoverable_payload_raises_model_error():
    try:
        NvidiaTutorReasoner(MOCK_CONFIG)._parse("[]")
    except NvidiaClientError as exc:
        assert "non-object" in str(exc)
    else:
        raise AssertionError("non-object payload should fail")


class StringClaimReasoner(TutorReasoner):
    def answer(
        self,
        *,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        learner_state: dict | None,
        request_id: str,
    ):
        return (
            TutorDraft(
                answer="ATP stores energy.",
                claims=(Claim(text="ATP stores energy.", source_ids=()),),
                citation_source_ids=("chapter-7-1-passage-05",),
                uncertainty=(),
                insufficient_evidence=False,
                recommended_next_action="review",
            ),
            0,
            "test",
        )


def test_malformed_recoverable_claim_never_verified_without_citation():
    response = answer_question(
        "What is ATP?",
        config=MOCK_CONFIG,
        reasoner=StringClaimReasoner(),
    )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any(o.reason == "claim has no citation" for o in response.gate_outcomes)


class FixedDraftReasoner(TutorReasoner):
    def __init__(self, draft: TutorDraft) -> None:
        self.draft = draft

    def answer(
        self,
        *,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        learner_state: dict | None,
        request_id: str,
    ):
        return self.draft, 0, "test"


def _answer_with_draft(draft: TutorDraft):
    return answer_question(
        "What are the pKa values of phosphoric acid?",
        config=MOCK_CONFIG,
        reasoner=FixedDraftReasoner(draft),
    )


def test_valid_cited_claim_verifies():
    response = _answer_with_draft(
        TutorDraft(
            answer="The pKas for phosphoric acid dissociation are 2.1, 7.2, and 12.4.",
            claims=(
                Claim(
                    text="The pKas for the three acid dissociation equilibria are 2.1, 7.2, and 12.4.",
                    source_ids=("chapter-7-1-passage-01",),
                ),
            ),
            citation_source_ids=("chapter-7-1-passage-01",),
        )
    )
    assert response.status == ResponseStatus.VERIFIED, response.to_dict()


def test_uncited_claim_remains_ambiguous():
    response = _answer_with_draft(
        TutorDraft(
            answer="Phosphoric acid has three pKa values.",
            claims=(Claim(text="Phosphoric acid has three pKa values.", source_ids=()),),
            citation_source_ids=(),
        )
    )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any(o.reason == "claim has no citation" for o in response.gate_outcomes)


def test_invented_source_id_fails():
    response = _answer_with_draft(
        TutorDraft(
            answer="Phosphoric acid has three pKa values.",
            claims=(
                Claim(
                    text="Phosphoric acid has three pKa values.",
                    source_ids=("chapter-7-1-passage-99",),
                ),
            ),
            citation_source_ids=("chapter-7-1-passage-99",),
        )
    )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any(o.reason == "invalid citation" for o in response.gate_outcomes)


def test_mixed_cited_and_uncited_claims_fail_safely():
    response = _answer_with_draft(
        TutorDraft(
            answer="Phosphoric acid pKas are listed. It is always the strongest biological buffer.",
            claims=(
                Claim(
                    text="The pKas for the three acid dissociation equilibria are 2.1, 7.2, and 12.4.",
                    source_ids=("chapter-7-1-passage-01",),
                ),
                Claim(
                    text="It is always the strongest biological buffer.",
                    source_ids=(),
                ),
            ),
            citation_source_ids=("chapter-7-1-passage-01",),
        )
    )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any(o.reason == "claim has no citation" for o in response.gate_outcomes)


def test_insufficient_evidence_path_with_model_draft():
    response = _answer_with_draft(
        TutorDraft(
            answer="The approved Chapter 7.1 passages do not provide enough evidence to answer that.",
            claims=(),
            citation_source_ids=(),
            uncertainty=("No provided source supports the requested claim.",),
            insufficient_evidence=True,
            recommended_next_action="ask_about_chapter_7_1",
        )
    )
    assert response.status == ResponseStatus.INSUFFICIENT_EVIDENCE, response.to_dict()
    assert response.gate_outcomes == ()


def test_numeric_claim_without_citation_fails():
    response = _answer_with_draft(
        TutorDraft(
            answer="The pKa values are 2.1, 7.2, and 12.4.",
            claims=(
                Claim(
                    text="The pKa values are 2.1, 7.2, and 12.4.",
                    source_ids=(),
                ),
            ),
            citation_source_ids=(),
        )
    )
    assert response.status == ResponseStatus.AMBIGUOUS, response.to_dict()
    assert any(o.reason == "claim has no citation" for o in response.gate_outcomes)


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
