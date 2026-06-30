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

        source_block = "\n\n".join(
            "\n".join(
                [
                    f"SOURCE_ID: {candidate.passage.source_id}",
                    f"SOURCE_LABEL: {candidate.passage.label}",
                    f"SOURCE_HASH: {candidate.passage.source_hash}",
                    f"SOURCE_TEXT: {candidate.passage.text}",
                ]
            )
            for candidate in candidates
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Phase 1 MCAT tutor reasoner. Return strict JSON only, with no markdown.\n"
                    "\n"
                    "Grounding rules:\n"
                    "- Use only the provided SOURCE_TEXT blocks.\n"
                    "- Every factual claim must include at least one citationSourceIds entry.\n"
                    "- citationSourceIds must be copied exactly from the provided SOURCE_ID values.\n"
                    "- Do not invent citation IDs.\n"
                    "- Do not make uncited numeric, chemical, equation, definition, or cause/effect claims.\n"
                    "- Preserve numbers, units, equations, conditions, and qualifiers exactly.\n"
                    "- If no source supports the answer, set insufficientEvidence to true, use an empty claims array, and do not answer from memory.\n"
                    "\n"
                    "Required output schema:\n"
                    "{\n"
                    '  "answer": "...",\n'
                    '  "claims": [\n'
                    '    {"text": "...", "citationSourceIds": ["chapter-7-1-passage-01"]}\n'
                    "  ],\n"
                    '  "uncertainty": [],\n'
                    '  "insufficientEvidence": false,\n'
                    '  "recommendedNextAction": "..."\n'
                    "}\n"
                    "\n"
                    "Valid example:\n"
                    "{\n"
                    '  "answer": "Phosphoric acid has three acid dissociation pKas: 2.1, 7.2, and 12.4.",\n'
                    '  "claims": [\n'
                    '    {"text": "The pKas for the three acid dissociation equilibria are 2.1, 7.2, and 12.4.", "citationSourceIds": ["chapter-7-1-passage-01"]}\n'
                    "  ],\n"
                    '  "uncertainty": [],\n'
                    '  "insufficientEvidence": false,\n'
                    '  "recommendedNextAction": "review_phosphoric_acid_dissociation"\n'
                    "}\n"
                    "\n"
                    "Insufficient-evidence example:\n"
                    "{\n"
                    '  "answer": "The approved Chapter 7.1 passages do not provide enough evidence to answer that.",\n'
                    '  "claims": [],\n'
                    '  "uncertainty": ["No provided SOURCE_TEXT supports the requested claim."],\n'
                    '  "insufficientEvidence": true,\n'
                    '  "recommendedNextAction": "ask_about_chapter_7_1_phosphorus_containing_compounds"\n'
                    "}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"STUDENT_QUESTION: {question}\n\n"
                    f"LEARNER_STATE_JSON: {json.dumps(learner_state or {}, ensure_ascii=False)}\n\n"
                    "APPROVED SOURCES:\n"
                    f"{source_block}\n\n"
                    "Return the required JSON object now."
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
        if not isinstance(payload, dict):
            raise NvidiaClientError("NVIDIA tutor returned non-object JSON")

        claims = _normalize_claims(payload.get("claims"))
        return TutorDraft(
            answer=_normalize_string(payload.get("answer")),
            claims=claims,
            citation_source_ids=_normalize_string_tuple(
                payload.get("citationSourceIds")
            ),
            uncertainty=_normalize_uncertainty(payload.get("uncertainty")),
            insufficient_evidence=_normalize_bool(
                payload.get("insufficientEvidence")
            ),
            recommended_next_action=_normalize_string(
                payload.get("recommendedNextAction"),
                default="review_cited_passages",
            ),
        )


def reasoner_for_config(config: CouncilConfig) -> TutorReasoner:
    if config.mock_mode:
        return MockTutorReasoner()
    return NvidiaTutorReasoner(config)


def new_request_id() -> str:
    return uuid.uuid4().hex


def _normalize_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else default
    if isinstance(value, (int, float)):
        return str(value)
    return default


def _normalize_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value is False:
        return ()
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, bool):
        return ("true",)
    if isinstance(value, (list, tuple)):
        return tuple(
            str(item)
            for item in value
            if item is not None and item is not False and str(item).strip()
        )
    return (str(value),)


def _normalize_uncertainty(value: Any) -> tuple[str, ...]:
    if value is True:
        return ("model_reported_unspecified_uncertainty",)
    return _normalize_string_tuple(value)


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _normalize_claims(value: Any) -> tuple[Claim, ...]:
    if value is None or value is False:
        return ()
    if isinstance(value, dict):
        items = (value,)
    elif isinstance(value, (list, tuple)):
        items = tuple(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return ()
        return (Claim(text=text, source_ids=(), confidence=None),)
    else:
        return (Claim(text=str(value), source_ids=(), confidence=None),)

    claims: list[Claim] = []
    for item in items:
        if isinstance(item, dict):
            text = _normalize_string(item.get("text"))
            source_ids = _normalize_string_tuple(
                item.get("sourceIds", item.get("citationSourceIds"))
            )
            confidence = item.get("confidence")
            if isinstance(confidence, bool) or not isinstance(
                confidence, (int, float)
            ):
                confidence = None
            claims.append(
                Claim(
                    text=text,
                    source_ids=source_ids,
                    confidence=confidence,
                )
            )
        elif isinstance(item, str) and item.strip():
            claims.append(
                Claim(text=item.strip(), source_ids=(), confidence=None)
            )
    return tuple(claims)
