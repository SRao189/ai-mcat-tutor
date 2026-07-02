"""Council verification boundary for wiki concept claims."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(token) > 2}


class CouncilVerificationBoundary:
    """Deterministic local boundary for ingestion-time Council claim gates.

    The live NVIDIA Council can replace this adapter later; the interface already
    records the same evidence outcomes the wiki compiler needs.
    """

    def __init__(self, repo_root: Path | str) -> None:
        self.repo_root = Path(repo_root).resolve()

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

        supported, reason = _claim_supported(str(claim.get("text") or ""), str(chunk.get("text") or ""))
        return self._outcome(
            claim,
            "verified" if supported else "unsupported",
            0.98 if supported else 0.1,
            reason,
            source_lineage={
                "sourceId": chunk.get("sourceId"),
                "chunkId": chunk.get("chunkId"),
                "sourceSpan": chunk.get("sourceSpan"),
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
        source_lineage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "text": claim.get("text"),
            "sourceId": claim.get("sourceId"),
            "sourceSpan": claim.get("sourceSpan"),
            "verification": verification,
            "confidence": confidence,
            "reason": reason,
            "sourceLineage": source_lineage or {},
        }


def _claim_supported(claim_text: str, source_text: str) -> tuple[bool, str]:
    normalized_claim = " ".join(claim_text.split()).lower()
    normalized_source = " ".join(source_text.split()).lower()
    if not normalized_claim:
        return False, "empty claim"
    if normalized_claim in normalized_source:
        return True, "claim text directly appears in source span"
    claim_tokens = _tokens(normalized_claim)
    source_tokens = _tokens(normalized_source)
    if not claim_tokens:
        return False, "empty claim"
    overlap = len(claim_tokens & source_tokens) / len(claim_tokens)
    if overlap >= 0.8:
        return True, "claim has deterministic lexical support"
    return False, "claim is not supported by the cited source span"
