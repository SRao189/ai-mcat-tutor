"""Council role interfaces and Phase 1 tutor reasoner."""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from typing import Any

from .config import CouncilConfig
from .nvidia_client import NvidiaClient, NvidiaClientError
from .schema import Claim, RetrievalCandidate, TutorDraft


class TutorReasoner(ABC):
    @abstractmethod
    def answer(
        self,
        *,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        learner_state: dict[str, Any] | None,
        request_id: str,
    ) -> tuple[TutorDraft, int | None, str | None]:
        raise NotImplementedError


class SafetyRole(ABC):
    """Future safety interface."""


class ChairRole(ABC):
    """Future synthesis interface."""


class MockTutorReasoner(TutorReasoner):
    def answer(
        self,
        *,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        learner_state: dict[str, Any] | None,
        request_id: str,
    ) -> tuple[TutorDraft, int | None, str | None]:
        if not candidates:
            return (
                TutorDraft(
                    answer="I do not have enough approved Chapter 7.1 evidence to answer that as a verified textbook-grounded response.",
                    claims=(),
                    citation_source_ids=(),
                    uncertainty=("No approved Chapter 7.1 passage was retrieved.",),
                    insufficient_evidence=True,
                    recommended_next_action="try_a_question_about_chapter_7_1",
                ),
                0,
                "mock",
            )

        top = candidates[0].passage
        q = question.lower()
        if "wrong-number" in q:
            claim = Claim(
                text="The standard free energy change for hydrolysis of pyrophosphate is about -5 kcal/mol.",
                source_ids=(top.source_id,),
                confidence=0.9,
            )
            answer = claim.text
        elif "invalid-citation" in q:
            claim = Claim(
                text="ATP is the universal short-term energy storage molecule.",
                source_ids=("chapter-7-1-missing",),
                confidence=0.9,
            )
            answer = claim.text
        elif "pka" in q or "physiological" in q or "phosphoric" in q:
            source_id = "chapter-7-1-passage-01"
            claim = Claim(
                text="The pKas for phosphoric acid dissociation are 2.1, 7.2, and 12.4.",
                source_ids=(source_id,),
                confidence=0.95,
            )
            answer = (
                "Phosphoric acid can donate three protons. In the approved Chapter 7.1 passage, "
                "its three dissociation pKas are 2.1, 7.2, and 12.4, and at physiological pH it exists largely in anionic form."
            )
        elif "atp" in q:
            source_id = "chapter-7-1-passage-05"
            claim = Claim(
                text="ATP is the universal short-term energy storage molecule and is a ribonucleotide.",
                source_ids=(source_id,),
                confidence=0.95,
            )
            answer = (
                "ATP is described as the universal short-term energy storage molecule and a ribonucleotide. "
                "Its extracted food energy is stored in phosphoanhydride bonds and used to power cellular processes."
            )
        else:
            claim = Claim(
                text=top.text.split(".")[0] + ".",
                source_ids=(top.source_id,),
                confidence=0.75,
            )
            answer = claim.text

        return (
            TutorDraft(
                answer=answer,
                claims=(claim,),
                citation_source_ids=claim.source_ids,
                uncertainty=(),
                insufficient_evidence=False,
                recommended_next_action="review_chapter_7_1_passage",
            ),
            0,
            "mock",
        )


class NvidiaTutorReasoner(TutorReasoner):
    def __init__(
        self,
        config: CouncilConfig,
        client: NvidiaClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or NvidiaClient(config)

    def answer(
        self,
        *,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        learner_state: dict[str, Any] | None,
        request_id: str,
    ) -> tuple[TutorDraft, int | None, str | None]:
        if not candidates:
            return (
                TutorDraft(
                    answer="Insufficient approved evidence was retrieved.",
                    claims=(),
                    citation_source_ids=(),
                    uncertainty=("No approved Chapter 7.1 passage was retrieved.",),
                    insufficient_evidence=True,
                    recommended_next_action="ask_about_chapter_7_1",
                ),
                None,
                self.config.tutor_model,
            )

        passages = [
            {
                "sourceId": candidate.passage.source_id,
                "label": candidate.passage.label,
                "sourceHash": candidate.passage.source_hash,
                "text": candidate.passage.text,
            }
            for candidate in candidates
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Phase 1 MCAT tutor reasoner. Use only the provided passages. "
                    "Do not use outside knowledge. Do not invent citations. Preserve numbers, units, equations, "
                    "conditions, and qualifiers exactly. If the passages do not support the answer, set "
                    "insufficientEvidence to true. Return only JSON with keys: answer, claims, citationSourceIds, "
                    "uncertainty, insufficientEvidence, recommendedNextAction."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "studentQuestion": question,
                        "learnerState": learner_state or {},
                        "passages": passages,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        result = self.client.chat_json(
            model=self.config.tutor_model or "",
            messages=messages,
            request_id=request_id,
            temperature=0.1,
            max_tokens=self.config.max_tokens,
        )
        return self._parse(result.content), result.latency_ms, result.model

    def _parse(self, content: str) -> TutorDraft:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise NvidiaClientError("NVIDIA tutor returned malformed JSON") from exc

        claims = tuple(
            Claim(
                text=str(item.get("text", "")),
                source_ids=tuple(str(s) for s in item.get("sourceIds", [])),
                confidence=item.get("confidence"),
            )
            for item in payload.get("claims", [])
            if isinstance(item, dict)
        )
        return TutorDraft(
            answer=str(payload.get("answer", "")),
            claims=claims,
            citation_source_ids=tuple(
                str(s) for s in payload.get("citationSourceIds", [])
            ),
            uncertainty=tuple(str(u) for u in payload.get("uncertainty", [])),
            insufficient_evidence=bool(payload.get("insufficientEvidence", False)),
            recommended_next_action=str(
                payload.get("recommendedNextAction", "review_cited_passages")
            ),
        )


def reasoner_for_config(config: CouncilConfig) -> TutorReasoner:
    if config.mock_mode:
        return MockTutorReasoner()
    return NvidiaTutorReasoner(config)


def new_request_id() -> str:
    return uuid.uuid4().hex
