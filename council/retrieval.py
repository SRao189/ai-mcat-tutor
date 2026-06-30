"""Retrieval interfaces and deterministic Chapter 7.1 keyword retrieval."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from .schema import RetrievalCandidate
from .source_store import Chapter71PassageStore


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, question: str, limit: int = 5) -> tuple[RetrievalCandidate, ...]:
        raise NotImplementedError


def tokenize(text: str) -> list[str]:
    stopwords = {
        "what",
        "does",
        "about",
        "chapter",
        "section",
        "say",
        "tell",
        "explain",
    }
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in stopwords
    ]


class KeywordChapter71Retriever(Retriever):
    def __init__(self, store: Chapter71PassageStore | None = None) -> None:
        self.store = store or Chapter71PassageStore()

    def retrieve(self, question: str, limit: int = 5) -> tuple[RetrievalCandidate, ...]:
        terms = set(tokenize(question))
        candidates: list[RetrievalCandidate] = []
        for passage in self.store.load():
            passage_terms = set(tokenize(passage.text))
            matched = tuple(sorted(terms & passage_terms))
            if not matched:
                continue
            score = len(matched) / max(len(terms), 1)
            candidates.append(
                RetrievalCandidate(
                    passage=passage,
                    score=score,
                    matched_terms=matched,
                )
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return tuple(candidates[:limit])


class EmbeddingRetriever(Retriever):
    """Future semantic retriever interface; intentionally inactive in Phase 1."""

    def retrieve(self, question: str, limit: int = 5) -> tuple[RetrievalCandidate, ...]:
        raise NotImplementedError("embedding retrieval is not enabled in phase 1")
