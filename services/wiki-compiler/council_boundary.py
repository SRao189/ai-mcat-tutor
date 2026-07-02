"""Council verification boundary for wiki concept claims."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from council.schema import Claim, SourcePassage, TutorDraft
from council.source_store import passage_hash
from council.verification import CouncilVerifier


MIN_VERIFIED_CONFIDENCE = 0.7


@dataclass(frozen=True)
class CouncilClaimVerdict:
    verification: str
    confidence: float
    reason: str
    status: str
    cited_passage_ids: tuple[str, ...]
    gate_outcomes: tuple[dict[str, Any], ...]


class ClaimVerifier(Protocol):
    def verify_claim(self, claim: dict[str, Any], chunk: dict[str, Any]) -> CouncilClaimVerdict:
        ...


class CouncilPackageClaimVerifier:
    """Production adapter over the existing council/ verification pipeline."""

    def verify_claim(self, claim: dict[str, Any], chunk: dict[str, Any]) -> CouncilClaimVerdict:
        source_id = str(claim.get("sourceId") or "")
        chunk_id = str(chunk.get("chunkId") or "")
        text = str(chunk.get("text") or "")
        if not source_id or not chunk_id or not text:
            return CouncilClaimVerdict(
                verification="source-gap",
                confidence=0.0,
                reason="missing source passage for Council verification",
                status="source-gap",
                cited_passage_ids=(),
                gate_outcomes=(),
            )

        passage = SourcePassage(
            source_id=chunk_id,
            source_hash=passage_hash(text),
            label=f"{source_id} {chunk.get('sourceSpan', chunk_id)}",
            text=text,
            chapter="wiki",
            section=source_id,
        )
        store = _SinglePassageStore(passage)
        draft = TutorDraft(
            answer=str(claim.get("text") or ""),
            claims=(
                Claim(
                    text=str(claim.get("text") or ""),
                    source_ids=(chunk_id,),
                    confidence=_numeric_confidence(claim.get("confidence")),
                ),
            ),
            citation_source_ids=(chunk_id,),
        )

        try:
            gate2_ok, gate3_ok, outcomes = CouncilVerifier(store).verify(draft)
        except Exception as exc:
            return CouncilClaimVerdict(
                verification="unsupported",
                confidence=0.0,
                reason=f"Council verification failed safely: {type(exc).__name__}",
                status="model_error",
                cited_passage_ids=(),
                gate_outcomes=(),
            )

        outcome_dicts = [
            {
                "gate": outcome.gate,
                "ok": outcome.ok,
                "reason": outcome.reason,
                "claim": outcome.claim,
                "sourceId": outcome.source_id,
            }
            for outcome in outcomes
        ]
        gate3_reasons = [outcome.reason for outcome in outcomes if outcome.gate == "gate3" and not outcome.ok]
        confidence = 0.98 if gate2_ok and gate3_ok else 0.1
        if gate2_ok and gate3_ok and confidence >= MIN_VERIFIED_CONFIDENCE:
            return CouncilClaimVerdict(
                verification="verified",
                confidence=confidence,
                reason="Council Gate 2 and Gate 3 passed",
                status="verified",
                cited_passage_ids=(chunk_id,),
                gate_outcomes=tuple(outcome_dicts),
            )
        return CouncilClaimVerdict(
            verification="unsupported",
            confidence=confidence,
            reason="; ".join(gate3_reasons) or "Council gates did not verify claim support",
            status="ambiguous",
            cited_passage_ids=(),
            gate_outcomes=tuple(outcome_dicts),
        )


class _SinglePassageStore:
    def __init__(self, passage: SourcePassage) -> None:
        self._passage = passage

    def load(self) -> tuple[SourcePassage, ...]:
        return (self._passage,)

    def by_id(self) -> dict[str, SourcePassage]:
        return {self._passage.source_id: self._passage}

    def labels_for_response(self, source_ids: list[str] | tuple[str, ...]) -> tuple[dict[str, str], ...]:
        if self._passage.source_id not in source_ids:
            return ()
        return (
            {
                "sourceId": self._passage.source_id,
                "label": self._passage.label,
                "sourceHash": self._passage.source_hash,
            },
        )


class CouncilVerificationBoundary:
    """Production boundary for ingestion-time Council claim gates."""

    def __init__(self, repo_root: Path | str, *, verifier: ClaimVerifier | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.verifier = verifier or CouncilPackageClaimVerifier()

    def verify_concept_page(self, page: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        chunks = self._load_chunks()
        verified_claims: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []

        for claim in page.get("claims", []):
            outcome = self._verify_claim(claim, chunks)
            next_claim = dict(claim)
            next_claim["verification"] = outcome["verification"]
            next_claim["confidence"] = outcome["confidence"]
            next_claim["learnerEligible"] = outcome["verification"] == "verified"
            next_claim["reason"] = outcome["reason"]
            next_claim["councilStatus"] = outcome["councilStatus"]
            next_claim["citedPassageIds"] = outcome["citedPassageIds"]
            next_claim["councilGateOutcomes"] = outcome["councilGateOutcomes"]
            next_claim["sourceLineage"] = outcome.get("sourceLineage", {})
            verified_claims.append(next_claim)
            trace.append(outcome)

        verified_page = dict(page)
        verified_page["claims"] = verified_claims
        verified_page["learnerEligible"] = bool(verified_claims) and all(
            claim["verification"] == "verified" for claim in verified_claims
        )
        verified_page["councilVerification"] = {
            "boundary": "services/wiki-compiler/council_boundary.py",
            "verifiedClaims": sum(1 for claim in verified_claims if claim["verification"] == "verified"),
            "claimCount": len(verified_claims),
        }
        return verified_page, {"conceptId": page.get("conceptId"), "claims": trace}

    def _load_chunks(self) -> dict[str, dict[str, Any]]:
        chunks: dict[str, dict[str, Any]] = {}
        for chunk_file in (self.repo_root / "knowledge" / "sources").glob("source-*/chunks.json"):
            data = json.loads(chunk_file.read_text(encoding="utf-8"))
            for chunk in data.get("chunks", []):
                chunks[chunk["chunkId"]] = chunk
        return chunks

    def _verify_claim(self, claim: dict[str, Any], chunks: dict[str, dict[str, Any]]) -> dict[str, Any]:
        source_id = str(claim.get("sourceId") or "")
        span = str(claim.get("sourceSpan") or "")
        if not source_id or not span:
            return self._outcome(claim, "source-gap", 0.0, "claim missing sourceId or sourceSpan")

        chunk = chunks.get(span)
        if chunk is None:
            for candidate in chunks.values():
                if candidate.get("sourceId") == source_id and span in {
                    candidate.get("sourceSpan"),
                    f"{candidate.get('sourceId')} {candidate.get('sourceSpan')}",
                }:
                    chunk = candidate
                    break
        if chunk is None:
            return self._outcome(claim, "source-gap", 0.0, "source span not found")

        try:
            verdict = self.verifier.verify_claim(claim, chunk)
            if not isinstance(verdict, CouncilClaimVerdict):
                raise TypeError("claim verifier returned malformed verdict")
        except Exception as exc:
            verdict = CouncilClaimVerdict(
                verification="unsupported",
                confidence=0.0,
                reason=f"Council verification failed safely: {type(exc).__name__}",
                status="model_error",
                cited_passage_ids=(),
                gate_outcomes=(),
            )
        if verdict.verification == "verified" and verdict.confidence < MIN_VERIFIED_CONFIDENCE:
            verdict = CouncilClaimVerdict(
                verification="unsupported",
                confidence=verdict.confidence,
                reason="Council confidence below learner eligibility threshold",
                status=verdict.status,
                cited_passage_ids=verdict.cited_passage_ids,
                gate_outcomes=verdict.gate_outcomes,
            )
        return self._outcome(
            claim,
            verdict.verification,
            verdict.confidence,
            verdict.reason,
            status=verdict.status,
            cited_passage_ids=verdict.cited_passage_ids,
            gate_outcomes=verdict.gate_outcomes,
            source_lineage={
                "sourceId": chunk.get("sourceId"),
                "chunkId": chunk.get("chunkId"),
                "sourceSpan": chunk.get("sourceSpan"),
                "pageStart": chunk.get("pageStart"),
                "pageEnd": chunk.get("pageEnd"),
                "textHash": chunk.get("textHash"),
            },
        )

    def _outcome(
        self,
        claim: dict[str, Any],
        verification: str,
        confidence: float,
        reason: str,
        *,
        status: str = "ambiguous",
        cited_passage_ids: tuple[str, ...] = (),
        gate_outcomes: tuple[dict[str, Any], ...] = (),
        source_lineage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "text": claim.get("text"),
            "sourceId": claim.get("sourceId"),
            "sourceSpan": claim.get("sourceSpan"),
            "verification": verification,
            "confidence": confidence,
            "reason": reason,
            "councilStatus": status,
            "citedPassageIds": list(cited_passage_ids),
            "councilGateOutcomes": list(gate_outcomes),
            "sourceLineage": source_lineage or {},
        }


def _numeric_confidence(value: Any) -> float | None:
    return value if isinstance(value, (int, float)) else None
