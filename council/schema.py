"""Structured request and response types for the tutor Council."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseStatus(str, Enum):
    VERIFIED = "verified"
    AMBIGUOUS = "ambiguous"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MODEL_ERROR = "model_error"


@dataclass(frozen=True)
class SourcePassage:
    source_id: str
    source_hash: str
    label: str
    text: str
    chapter: str = "7"
    section: str = "7.1"


@dataclass(frozen=True)
class RetrievalCandidate:
    passage: SourcePassage
    score: float
    matched_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class Claim:
    text: str
    source_ids: tuple[str, ...]
    confidence: float | None = None


@dataclass(frozen=True)
class TutorDraft:
    answer: str
    claims: tuple[Claim, ...]
    citation_source_ids: tuple[str, ...]
    uncertainty: tuple[str, ...] = ()
    insufficient_evidence: bool = False
    recommended_next_action: str = "review_cited_passages"


@dataclass(frozen=True)
class GateOutcome:
    gate: str
    ok: bool
    reason: str = ""
    claim: str | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class CouncilResponse:
    request_id: str
    status: ResponseStatus
    answer: str
    cited_sources: tuple[dict[str, str], ...]
    claims: tuple[Claim, ...] = ()
    uncertainty: tuple[str, ...] = ()
    recommended_next_action: str = "review_cited_passages"
    gate_outcomes: tuple[GateOutcome, ...] = ()
    model: str | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "status": self.status.value,
            "answer": self.answer,
            "citedSources": list(self.cited_sources),
            "claims": [
                {
                    "text": claim.text,
                    "sourceIds": list(claim.source_ids),
                    "confidence": claim.confidence,
                }
                for claim in self.claims
            ],
            "uncertainty": list(self.uncertainty),
            "recommendedNextAction": self.recommended_next_action,
            "gateOutcomes": [
                {
                    "gate": outcome.gate,
                    "ok": outcome.ok,
                    "reason": outcome.reason,
                    "claim": outcome.claim,
                    "sourceId": outcome.source_id,
                }
                for outcome in self.gate_outcomes
            ],
            "model": self.model,
            "latencyMs": self.latency_ms,
            "metadata": self.metadata,
        }
