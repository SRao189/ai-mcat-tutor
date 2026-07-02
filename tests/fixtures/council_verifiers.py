from __future__ import annotations

from typing import Any


class RaisingVerifier:
    def verify_claim(self, claim: dict[str, Any], chunk: dict[str, Any]):
        raise RuntimeError("synthetic Council failure")


class MalformedVerifier:
    def verify_claim(self, claim: dict[str, Any], chunk: dict[str, Any]):
        return {"verification": "verified"}


class LowConfidenceVerifier:
    def verify_claim(self, claim: dict[str, Any], chunk: dict[str, Any]):
        from council_boundary import CouncilClaimVerdict

        return CouncilClaimVerdict(
            verification="verified",
            confidence=0.2,
            reason="synthetic low confidence",
            status="verified",
            cited_passage_ids=(chunk["chunkId"],),
            gate_outcomes=({"gate": "gate3", "ok": True, "reason": "synthetic"},),
        )


class UnavailableCouncilVerifier:
    def verify_claim(self, claim: dict[str, Any], chunk: dict[str, Any]):
        from council_boundary import CouncilClaimVerdict

        return CouncilClaimVerdict(
            verification="unsupported",
            confidence=0.0,
            reason="NVIDIA Council unavailable or credentials missing",
            status="model_error",
            cited_passage_ids=(),
            gate_outcomes=(),
        )
