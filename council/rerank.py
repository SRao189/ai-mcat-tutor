"""Reranking interfaces for Council retrieval candidates."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .retrieval import tokenize
from .schema import RetrievalCandidate


class Reranker(ABC):
    @abstractmethod
    def rerank(
        self,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        limit: int = 4,
    ) -> tuple[RetrievalCandidate, ...]:
        raise NotImplementedError


class LexicalReranker(Reranker):
    """Deterministic fallback. This ranks relevance; it does not verify support."""

    def rerank(
        self,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        limit: int = 4,
    ) -> tuple[RetrievalCandidate, ...]:
        question_terms = set(tokenize(question))
        rescored: list[RetrievalCandidate] = []
        for candidate in candidates:
            label_terms = set(tokenize(candidate.passage.label))
            bonus = 0.15 * len(question_terms & label_terms)
            rescored.append(
                RetrievalCandidate(
                    passage=candidate.passage,
                    score=candidate.score + bonus,
                    matched_terms=candidate.matched_terms,
                )
            )
        rescored.sort(key=lambda item: item.score, reverse=True)
        return tuple(rescored[:limit])


class NvidiaReranker(Reranker):
    """Future NVIDIA reranker adapter; not called by Phase 1 live path."""

    def rerank(
        self,
        question: str,
        candidates: tuple[RetrievalCandidate, ...],
        limit: int = 4,
    ) -> tuple[RetrievalCandidate, ...]:
        # Reranking is deliberately kept deterministic until the exact active
        # NVIDIA rerank endpoint is audited. It must never be treated as Gate 3.
        return LexicalReranker().rerank(question, candidates, limit=limit)
