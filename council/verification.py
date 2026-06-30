"""Gate 2 and Gate 3-compatible verification for Phase 1 Council output."""

from __future__ import annotations

import re

from .schema import Claim, GateOutcome, SourcePassage, TutorDraft
from .source_store import Chapter71PassageStore, PassageStoreError, normalize_text, passage_hash


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2
    }


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"-?\d+(?:\.\d+)?", text))


def _units(text: str) -> set[str]:
    units = ("kcal/mol", "kj/mol", "m", "mm", "%", "ph", "pka")
    lowered = text.lower()
    return {unit for unit in units if unit in lowered}


def _equation_like(text: str) -> bool:
    return any(symbol in text for symbol in ("=", "->", "⇌", "+", "-"))


class CouncilVerifier:
    def __init__(self, store: Chapter71PassageStore | None = None) -> None:
        self.store = store or Chapter71PassageStore()

    def verify(self, draft: TutorDraft) -> tuple[bool, bool, tuple[GateOutcome, ...]]:
        """Return (gate2_ok, gate3_ok, outcomes)."""
        outcomes: list[GateOutcome] = []
        try:
            by_id = self.store.by_id()
        except PassageStoreError as exc:
            return (
                False,
                False,
                (
                    GateOutcome(
                        gate="stale-source",
                        ok=False,
                        reason=str(exc),
                    ),
                ),
            )

        if draft.insufficient_evidence:
            return True, True, tuple(outcomes)

        if not draft.claims:
            return (
                False,
                False,
                (
                    GateOutcome(
                        gate="gate3",
                        ok=False,
                        reason="empty claims are not verified",
                    ),
                ),
            )

        for claim in draft.claims:
            if not claim.text.strip():
                outcomes.append(
                    GateOutcome(
                        gate="gate3",
                        ok=False,
                        reason="empty claim",
                        claim=claim.text,
                    )
                )
                continue
            if not claim.source_ids:
                outcomes.append(
                    GateOutcome(
                        gate="gate2",
                        ok=False,
                        reason="claim has no citation",
                        claim=claim.text,
                    )
                )
                continue
            for source_id in claim.source_ids:
                passage = by_id.get(source_id)
                if passage is None:
                    outcomes.append(
                        GateOutcome(
                            gate="gate2",
                            ok=False,
                            reason="invalid citation",
                            claim=claim.text,
                            source_id=source_id,
                        )
                    )
                    continue
                if passage_hash(passage.text) != passage.source_hash:
                    outcomes.append(
                        GateOutcome(
                            gate="stale-source",
                            ok=False,
                            reason="source hash mismatch",
                            claim=claim.text,
                            source_id=source_id,
                        )
                    )
                    continue
                outcomes.append(
                    GateOutcome(
                        gate="gate2",
                        ok=True,
                        reason="citation resolved",
                        claim=claim.text,
                        source_id=source_id,
                    )
                )
                supported, reason = self._claim_supported(claim, passage)
                outcomes.append(
                    GateOutcome(
                        gate="gate3",
                        ok=supported,
                        reason=reason,
                        claim=claim.text,
                        source_id=source_id,
                    )
                )

        gate2_ok = all(o.ok for o in outcomes if o.gate in {"gate2", "stale-source"})
        gate3_outcomes = [o for o in outcomes if o.gate == "gate3"]
        gate3_ok = bool(gate3_outcomes) and all(o.ok for o in gate3_outcomes)
        return gate2_ok, gate3_ok, tuple(outcomes)

    def _claim_supported(self, claim: Claim, passage: SourcePassage) -> tuple[bool, str]:
        claim_text = normalize_text(claim.text)
        passage_text = normalize_text(passage.text)
        if claim_text.lower() in passage_text.lower():
            return True, "claim text is directly supported"

        claim_numbers = _numbers(claim_text)
        passage_numbers = _numbers(passage_text)
        if not claim_numbers <= passage_numbers:
            return False, "numeric claim not supported by cited passage"

        claim_units = _units(claim_text)
        passage_units = _units(passage_text)
        if not claim_units <= passage_units:
            return False, "unit claim not supported by cited passage"

        if _equation_like(claim_text) and claim_text.lower() not in passage_text.lower():
            if claim_numbers or claim_units:
                return False, "equation or directional relationship is not directly supported"

        claim_tokens = _tokens(claim_text)
        passage_tokens = _tokens(passage_text)
        if not claim_tokens:
            return False, "empty claim"
        overlap = len(claim_tokens & passage_tokens) / len(claim_tokens)
        if overlap >= 0.72:
            return True, "claim has deterministic lexical support"
        return False, "claim is not sufficiently supported by cited passage"
