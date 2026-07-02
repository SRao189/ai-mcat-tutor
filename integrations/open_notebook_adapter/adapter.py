"""Bridge Open Notebook ingestion/retrieval into the MCAT Council gates.

Open Notebook owns source management and retrieval here. The Council remains
the authority for learner-visible answers because this module only adapts
retrieved evidence into the existing CouncilVerifier / answer_question shapes.
"""

from __future__ import annotations

import logging
import re
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from council.retrieval import Retriever, tokenize
from council.schema import RetrievalCandidate, SourcePassage, TutorDraft
from council.source_store import normalize_text, passage_hash
from council.verification import CouncilVerifier

DEFAULT_MCAT_NOTEBOOK_NAME = "MCAT Tutor Source Library"
DEFAULT_MCAT_NOTEBOOK_DESCRIPTION = (
    "Source documents managed in Open Notebook for the MCAT tutor."
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDORED_OPEN_NOTEBOOK = REPO_ROOT / "vendor" / "open-notebook"
DEFAULT_GRAPH_PATH = REPO_ROOT / "wiki" / ".understand-anything" / "knowledge-graph.json"


def _ensure_vendored_api_importable() -> None:
    """Make the vendored Open Notebook API client importable without editing it."""

    if str(VENDORED_OPEN_NOTEBOOK) not in sys.path:
        sys.path.insert(0, str(VENDORED_OPEN_NOTEBOOK))

    if "loguru" not in sys.modules:
        logger = logging.getLogger("open_notebook_adapter.loguru_fallback")
        module = types.ModuleType("loguru")
        module.logger = logger
        sys.modules["loguru"] = module


def _api_client_class():
    _ensure_vendored_api_importable()
    from api.client import APIClient

    return APIClient


def _scalar(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def _sequence_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_sequence_text(item) for item in value)
    if isinstance(value, tuple):
        return " ".join(_sequence_text(item) for item in value)
    return str(value)


def _content_from_result(result: dict[str, Any]) -> str:
    content = _sequence_text(result.get("content"))
    if not content:
        content = _sequence_text(result.get("matches"))
    return content.replace("`", "").strip()


def _score_from_result(result: dict[str, Any]) -> float:
    for key in ("final_score", "score", "relevance", "similarity"):
        value = result.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


@dataclass(frozen=True)
class OpenNotebookNotebook:
    id: str
    name: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestedSource:
    source_id: str
    notebook_id: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedPassage:
    passage_id: str
    source_id: str
    title: str
    text: str
    score: float
    notebook_id: str | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)
    search_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation_id(self) -> str:
        if self.passage_id == self.source_id:
            return self.source_id
        return f"{self.source_id}#{self.passage_id}"

    @property
    def source_hash(self) -> str:
        return passage_hash(self.text)

    @property
    def label(self) -> str:
        return f"{self.title} ({self.source_id}; passage {self.passage_id})"

    def to_source_passage(self) -> SourcePassage:
        return SourcePassage(
            source_id=self.citation_id,
            source_hash=self.source_hash,
            label=self.label,
            text=self.text,
            chapter="open-notebook",
            section="open-notebook",
        )


class OpenNotebookPassageStore:
    """CouncilVerifier-compatible store over Open Notebook retrieved passages."""

    def __init__(self, passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...]) -> None:
        self._retrieved = tuple(passages)
        self._source_passages = tuple(passage.to_source_passage() for passage in self._retrieved)
        self._metadata_by_citation = {
            passage.citation_id: passage for passage in self._retrieved
        }

    def load(self) -> tuple[SourcePassage, ...]:
        return self._source_passages

    def by_id(self) -> dict[str, SourcePassage]:
        return {passage.source_id: passage for passage in self._source_passages}

    def labels_for_response(self, source_ids: list[str] | tuple[str, ...]) -> tuple[dict[str, str], ...]:
        by_id = self.by_id()
        labels: list[dict[str, str]] = []
        for source_id in source_ids:
            passage = by_id[source_id]
            retrieved = self._metadata_by_citation[source_id]
            labels.append(
                {
                    "sourceId": passage.source_id,
                    "label": passage.label,
                    "sourceHash": passage.source_hash,
                    "openNotebookSourceId": retrieved.source_id,
                    "openNotebookPassageId": retrieved.passage_id,
                }
            )
        return tuple(labels)


class OpenNotebookRetriever(Retriever):
    """Static retriever over passages already returned by Open Notebook search."""

    def __init__(self, passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...]) -> None:
        self.passages = tuple(passages)

    def retrieve(self, question: str, limit: int = 5) -> tuple[RetrievalCandidate, ...]:
        question_terms = set(tokenize(question))
        candidates: list[RetrievalCandidate] = []
        for passage in self.passages:
            passage_terms = set(tokenize(f"{passage.title} {passage.text}"))
            matched = tuple(sorted(question_terms & passage_terms))
            score = passage.score
            if matched:
                score += len(matched) / max(len(question_terms), 1)
            candidates.append(
                RetrievalCandidate(
                    passage=passage.to_source_passage(),
                    score=score,
                    matched_terms=matched,
                )
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return tuple(candidates[:limit])


class OpenNotebookAdapter:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        client: Any | None = None,
        graph_path: Path | str = DEFAULT_GRAPH_PATH,
    ) -> None:
        self.client = client or _api_client_class()(base_url=base_url)
        self.graph_path = Path(graph_path)

    def create_or_select_mcat_notebook(
        self,
        name: str = DEFAULT_MCAT_NOTEBOOK_NAME,
        description: str = DEFAULT_MCAT_NOTEBOOK_DESCRIPTION,
    ) -> OpenNotebookNotebook:
        for notebook in self.client.get_notebooks(archived=False):
            if notebook.get("name") == name:
                return self._notebook_from_response(notebook)
        created = self.client.create_notebook(name=name, description=description)
        return self._notebook_from_response(created if isinstance(created, dict) else created[0])

    def ingest_source(
        self,
        *,
        title: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        notebook_id: str | None = None,
        transformations: list[str] | None = None,
        embed: bool = True,
    ) -> IngestedSource:
        notebook = (
            OpenNotebookNotebook(id=notebook_id, name="", description="")
            if notebook_id
            else self.create_or_select_mcat_notebook()
        )
        response = self.client.create_source(
            notebooks=[notebook.id],
            source_type="text",
            content=text,
            title=title,
            transformations=transformations,
            embed=embed,
            async_processing=False,
        )
        payload = response if isinstance(response, dict) else response[0]
        source_metadata = dict(metadata or {})
        source_metadata.update(
            {
                "topics": payload.get("topics") or [],
                "embedded": payload.get("embedded"),
                "embedded_chunks": payload.get("embedded_chunks"),
                "notebooks": payload.get("notebooks") or [notebook.id],
            }
        )
        return IngestedSource(
            source_id=_scalar(payload.get("id")),
            notebook_id=notebook.id,
            title=_scalar(payload.get("title"), title),
            metadata=source_metadata,
            raw_response=payload,
        )

    def retrieve_passages(
        self,
        question: str,
        *,
        notebook_id: str | None = None,
        limit: int = 5,
        search_type: str = "text",
        minimum_score: float = 0.2,
    ) -> tuple[RetrievedPassage, ...]:
        allowed_sources = self._source_ids_for_notebook(notebook_id) if notebook_id else None
        response = self.client.search(
            query=question,
            search_type=search_type,
            limit=limit,
            search_sources=True,
            search_notes=False,
            minimum_score=minimum_score,
        )
        results = response.get("results", []) if isinstance(response, dict) else []

        passages: list[RetrievedPassage] = []
        for result in results:
            source_id = _scalar(result.get("parent_id") or result.get("source_id") or result.get("sourceId") or result.get("id"))
            if allowed_sources is not None and source_id not in allowed_sources:
                continue
            passage_id = _scalar(result.get("id"), source_id)
            text = _content_from_result(result)
            source_metadata = self._get_source_metadata(source_id)
            if not text:
                text = _scalar(source_metadata.get("full_text")).strip()
            if not text:
                continue
            title = _scalar(result.get("title") or source_metadata.get("title"), "Open Notebook source")
            passages.append(
                RetrievedPassage(
                    passage_id=passage_id,
                    source_id=source_id,
                    title=title,
                    text=normalize_text(text),
                    score=_score_from_result(result),
                    notebook_id=notebook_id,
                    source_metadata=source_metadata,
                    search_metadata=dict(result),
                )
            )
        return tuple(passages[:limit])

    def citation_candidates(
        self, passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...]
    ) -> tuple[SourcePassage, ...]:
        return tuple(passage.to_source_passage() for passage in passages)

    def request_transformation(
        self,
        *,
        transformation_id: str,
        input_text: str,
        model_id: str,
    ) -> dict[str, Any]:
        result = self.client.execute_transformation(
            transformation_id=transformation_id,
            input_text=input_text,
            model_id=model_id,
        )
        return result if isinstance(result, dict) else result[0]

    def map_to_concept_nodes(
        self,
        passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...],
        *,
        max_nodes_per_passage: int = 3,
    ) -> dict[str, tuple[str, ...]]:
        graph = self._load_graph()
        nodes = graph.get("nodes", [])
        mapped: dict[str, tuple[str, ...]] = {}
        for passage in passages:
            text = f"{passage.title} {passage.text}"
            text_terms = set(_graph_tokens(text))
            scored: list[tuple[int, str]] = []
            for node in nodes:
                node_id = _scalar(node.get("id"))
                if not node_id:
                    continue
                node_text = _node_match_text(node)
                node_terms = set(_graph_tokens(node_text))
                score = len(text_terms & node_terms)
                node_name = _scalar(node.get("name")).lower()
                # ponytail: deterministic keyword/title matching, not an ML linker.
                if node_name and node_name in text.lower():
                    score += 5
                if score:
                    scored.append((score, node_id))
            scored.sort(key=lambda item: (-item[0], item[1]))
            mapped[passage.citation_id] = tuple(
                node_id for _, node_id in scored[:max_nodes_per_passage]
            )
        return mapped

    def passage_store(
        self, passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...]
    ) -> OpenNotebookPassageStore:
        return OpenNotebookPassageStore(passages)

    def retriever(
        self, passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...]
    ) -> OpenNotebookRetriever:
        return OpenNotebookRetriever(passages)

    def verifier(
        self, passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...]
    ) -> CouncilVerifier:
        return CouncilVerifier(self.passage_store(passages))

    def verify_draft(
        self,
        draft: TutorDraft,
        passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...],
    ) -> tuple[bool, bool, tuple[Any, ...]]:
        return self.verifier(passages).verify(draft)

    def _source_ids_for_notebook(self, notebook_id: str | None) -> set[str]:
        if not notebook_id:
            return set()
        sources = self.client.get_sources(notebook_id=notebook_id)
        return {_scalar(source.get("id")) for source in sources if source.get("id")}

    def _get_source_metadata(self, source_id: str) -> dict[str, Any]:
        if not source_id:
            return {}
        try:
            source = self.client.get_source(source_id)
        except Exception:
            return {}
        return dict(source if isinstance(source, dict) else source[0])

    def _load_graph(self) -> dict[str, Any]:
        import json

        return json.loads(self.graph_path.read_text(encoding="utf-8"))

    @staticmethod
    def _notebook_from_response(payload: dict[str, Any]) -> OpenNotebookNotebook:
        return OpenNotebookNotebook(
            id=_scalar(payload.get("id")),
            name=_scalar(payload.get("name")),
            description=_scalar(payload.get("description")),
            metadata={k: v for k, v in payload.items() if k not in {"id", "name", "description"}},
        )


def _graph_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2
    ]


def _node_match_text(node: dict[str, Any]) -> str:
    meta = node.get("knowledgeMeta") if isinstance(node.get("knowledgeMeta"), dict) else {}
    tags = node.get("tags") if isinstance(node.get("tags"), list) else []
    return " ".join(
        [
            _scalar(node.get("id")),
            _scalar(node.get("name")),
            _scalar(node.get("summary")),
            " ".join(_scalar(tag) for tag in tags),
            _scalar(meta.get("content")),
        ]
    )
