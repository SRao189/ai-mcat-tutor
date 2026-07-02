"""Approved passage stores for Phase 1 Council retrieval."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .course_modules import MODULE_BY_SECTION, module_passages
from .schema import SourcePassage


class PassageStoreError(RuntimeError):
    pass


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def passage_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


class ChapterPassageStore:
    def __init__(
        self,
        path: Path,
        *,
        default_chapter: str,
        default_section: str,
    ) -> None:
        self.path = path
        self.default_chapter = default_chapter
        self.default_section = default_section
        self._passages: tuple[SourcePassage, ...] | None = None

    def load(self) -> tuple[SourcePassage, ...]:
        if self._passages is not None:
            return self._passages

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        passages: list[SourcePassage] = []
        for item in payload.get("passages", []):
            text = item["text"]
            expected_hash = item["sourceHash"]
            actual_hash = passage_hash(text)
            if actual_hash != expected_hash:
                raise PassageStoreError(
                    f"stale passage hash for {item.get('sourceId', '?')}"
                )
            passages.append(
                SourcePassage(
                    source_id=item["sourceId"],
                    source_hash=expected_hash,
                    label=item["label"],
                    text=text,
                    chapter=item.get("chapter", self.default_chapter),
                    section=item.get("section", self.default_section),
                )
            )
        self._passages = tuple(passages)
        return self._passages

    def by_id(self) -> dict[str, SourcePassage]:
        return {passage.source_id: passage for passage in self.load()}

    def labels_for_response(self, source_ids: list[str] | tuple[str, ...]) -> tuple[dict[str, str], ...]:
        if not source_ids:
            return ()
        by_id = self.by_id()
        labels: list[dict[str, str]] = []
        for source_id in source_ids:
            passage = by_id[source_id]
            labels.append(
                {
                    "sourceId": passage.source_id,
                    "label": passage.label,
                    "sourceHash": passage.source_hash,
                }
            )
        return tuple(labels)


class Chapter71PassageStore(ChapterPassageStore):
    def __init__(self, path: Path | None = None) -> None:
        super().__init__(
            path or Path(__file__).with_name("data") / "chapter_7_1_passages.json",
            default_chapter="7",
            default_section="7.1",
        )


class ThermodynamicsPassageStore(ChapterPassageStore):
    def __init__(self, path: Path | None = None) -> None:
        super().__init__(
            path or Path(__file__).with_name("data") / "thermodynamics_passages.json",
            default_chapter="Thermodynamics",
            default_section="thermo",
        )


class CourseModulePassageStore:
    def __init__(self, section_id: str) -> None:
        self.section_id = section_id
        self._passages: tuple[SourcePassage, ...] | None = None

    def load(self) -> tuple[SourcePassage, ...]:
        if self._passages is not None:
            return self._passages

        passages: list[SourcePassage] = []
        for item in module_passages(self.section_id):
            text = item["text"]
            expected_hash = item["sourceHash"]
            actual_hash = passage_hash(text)
            if actual_hash != expected_hash:
                raise PassageStoreError(
                    f"stale passage hash for {item.get('sourceId', '?')}"
                )
            passages.append(
                SourcePassage(
                    source_id=item["sourceId"],
                    source_hash=expected_hash,
                    label=item["label"],
                    text=text,
                    chapter=item["chapter"],
                    section=item["section"],
                )
            )
        self._passages = tuple(passages)
        return self._passages

    def by_id(self) -> dict[str, SourcePassage]:
        return {passage.source_id: passage for passage in self.load()}

    def labels_for_response(self, source_ids: list[str] | tuple[str, ...]) -> tuple[dict[str, str], ...]:
        if not source_ids:
            return ()
        by_id = self.by_id()
        labels: list[dict[str, str]] = []
        for source_id in source_ids:
            passage = by_id[source_id]
            labels.append(
                {
                    "sourceId": passage.source_id,
                    "label": passage.label,
                    "sourceHash": passage.source_hash,
                }
            )
        return tuple(labels)


def passage_store_for_section(section_id: str) -> ChapterPassageStore:
    if section_id == "7.1":
        return Chapter71PassageStore()
    if section_id == "thermo":
        return ThermodynamicsPassageStore()
    if section_id in MODULE_BY_SECTION:
        return CourseModulePassageStore(section_id)
    raise PassageStoreError(f"no approved passage store for sectionId {section_id!r}")
