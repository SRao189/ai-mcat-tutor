"""Narrow Phase 1 Council flow."""

from __future__ import annotations

import logging
from typing import Any

from .config import CouncilConfig, CouncilConfigError
from .nvidia_client import NvidiaClientError
from .rerank import LexicalReranker, Reranker
from .retrieval import KeywordPassageRetriever, Retriever
from .roles import TutorReasoner, new_request_id, reasoner_for_config
from .schema import CouncilResponse, ResponseStatus
from .source_store import passage_store_for_section
from .verification import CouncilVerifier


def _log(logger: logging.Logger | None, event: str, payload: dict[str, Any]) -> None:
    if logger is not None:
        logger.info("%s %s", event, payload)


def answer_question(
    question: str,
    *,
    section_id: str = "7.1",
    learner_state: dict[str, Any] | None = None,
    config: CouncilConfig | None = None,
    retriever: Retriever | None = None,
    reranker: Reranker | None = None,
    reasoner: TutorReasoner | None = None,
    verifier: CouncilVerifier | None = None,
    logger: logging.Logger | None = None,
) -> CouncilResponse:
    request_id = new_request_id()
    cfg = config or CouncilConfig.from_env()
    store = passage_store_for_section(section_id)
    retrieve = retriever or KeywordPassageRetriever(store)
    rerank = reranker or LexicalReranker()
    verify = verifier or CouncilVerifier(store)
    tutor = reasoner or reasoner_for_config(cfg)

    try:
        if not cfg.mock_mode:
            cfg.require_live_ready()

        candidates = retrieve.retrieve(question, limit=5)
        _log(
            logger,
            "retrieval",
            {
                "requestId": request_id,
                "candidateSourceIds": [c.passage.source_id for c in candidates],
            },
        )
        ranked = rerank.rerank(question, candidates, limit=4)
        _log(
            logger,
            "rerank",
            {
                "requestId": request_id,
                "scores": [
                    {"sourceId": c.passage.source_id, "score": round(c.score, 4)}
                    for c in ranked
                ],
            },
        )
        if not ranked:
            return CouncilResponse(
                request_id=request_id,
                status=ResponseStatus.INSUFFICIENT_EVIDENCE,
                answer="No approved passage in this chapter supports a verified answer to that question.",
                cited_sources=(),
                uncertainty=("retrieval returned no approved passages",),
                recommended_next_action="ask_about_this_chapter",
                metadata={"liveModelCalls": 0},
            )

        draft, latency_ms, model = tutor.answer(
            question=question,
            candidates=ranked,
            learner_state=learner_state,
            request_id=request_id,
        )
        _log(
            logger,
            "model",
            {
                "requestId": request_id,
                "model": model,
                "latencyMs": latency_ms,
            },
        )

        if draft.insufficient_evidence:
            return CouncilResponse(
                request_id=request_id,
                status=ResponseStatus.INSUFFICIENT_EVIDENCE,
                answer=draft.answer,
                cited_sources=(),
                claims=draft.claims,
                uncertainty=draft.uncertainty,
                recommended_next_action=draft.recommended_next_action,
                model=model,
                latency_ms=latency_ms,
                metadata={"liveModelCalls": 0 if cfg.mock_mode else 1},
            )

        gate2_ok, gate3_ok, outcomes = verify.verify(draft)
        _log(
            logger,
            "gates",
            {
                "requestId": request_id,
                "gate2": gate2_ok,
                "gate3": gate3_ok,
                "outcomes": [
                    {"gate": o.gate, "ok": o.ok, "reason": o.reason}
                    for o in outcomes
                ],
            },
        )
        if gate2_ok and gate3_ok:
            source_ids = tuple(
                dict.fromkeys(
                    source_id
                    for claim in draft.claims
                    for source_id in claim.source_ids
                )
            )
            status = ResponseStatus.VERIFIED
            answer = draft.answer
        else:
            source_ids = ()
            status = ResponseStatus.AMBIGUOUS
            answer = (
                "I found relevant chapter material, but the generated answer did not pass citation and claim-support checks."
            )

        response = CouncilResponse(
            request_id=request_id,
            status=status,
            answer=answer,
            cited_sources=verify.store.labels_for_response(source_ids),
            claims=draft.claims,
            uncertainty=draft.uncertainty,
            recommended_next_action=draft.recommended_next_action,
            gate_outcomes=outcomes,
            model=model,
            latency_ms=latency_ms,
            metadata={"liveModelCalls": 0 if cfg.mock_mode else 1},
        )
        _log(
            logger,
            "final",
            {"requestId": request_id, "status": response.status.value},
        )
        return response
    except CouncilConfigError as exc:
        return CouncilResponse(
            request_id=request_id,
            status=ResponseStatus.MODEL_ERROR,
            answer="The NVIDIA Council is not configured for live tutoring.",
            cited_sources=(),
            uncertainty=(str(exc),),
            recommended_next_action="configure_missing_environment_variables",
            metadata={"missing": exc.missing, "liveModelCalls": 0},
        )
    except NvidiaClientError as exc:
        return CouncilResponse(
            request_id=request_id,
            status=ResponseStatus.MODEL_ERROR,
            answer="The NVIDIA tutor call failed safely before a verified answer could be returned.",
            cited_sources=(),
            uncertainty=(str(exc),),
            recommended_next_action="retry_or_use_mock_mode",
            metadata={"liveModelCalls": 1},
        )
