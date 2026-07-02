"""Course-data adapters for interactive chapters and approved passages."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
COURSE_DATA = REPO / "course-data"

MODULE_BY_SECTION: dict[str, str] = {
    "kinetics": "module-2",
    "redox": "module-3",
    "acids-bases": "module-4",
    "chapter-3-summary": "module-5",
}


def load_module(section_id: str) -> dict[str, Any]:
    module_id = MODULE_BY_SECTION[section_id]
    return json.loads((COURSE_DATA / f"{module_id}.json").read_text(encoding="utf-8"))


def parse_source_ref(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        source_id = str(value.get("sourceId", "")).strip()
        quote = str(value.get("quote", "")).strip()
        passage_hash = str(value.get("passageHash", "")).strip()
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith("@{") and text.endswith("}"):
            text = text[2:-1]
        source_marker = "sourceId="
        quote_marker = "; quote="
        hash_marker = "; passageHash="
        if source_marker not in text or quote_marker not in text or hash_marker not in text:
            return None
        source_start = text.index(source_marker) + len(source_marker)
        quote_start = text.index(quote_marker)
        hash_start = text.rindex(hash_marker)
        source_id = text[source_start:quote_start].strip()
        quote = text[quote_start + len(quote_marker):hash_start].strip()
        passage_hash = text[hash_start + len(hash_marker):].strip()
    else:
        return None

    if not source_id or not quote or not passage_hash:
        return None
    return {"sourceId": source_id, "quote": quote, "passageHash": passage_hash}


def _collect_refs(value: Any) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    if isinstance(value, dict):
        if "sourceRefs" in value:
            for ref in value.get("sourceRefs") or []:
                parsed = parse_source_ref(ref)
                if parsed is not None:
                    refs.append(parsed)
        for item in value.values():
            refs.extend(_collect_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_collect_refs(item))
    return refs


def module_refs(module: dict[str, Any]) -> list[dict[str, str]]:
    seen: set[str] = set()
    refs: list[dict[str, str]] = []
    for ref in _collect_refs(module):
        source_id = ref["sourceId"]
        if source_id in seen:
            continue
        seen.add(source_id)
        refs.append(ref)
    return refs


def module_passages(section_id: str) -> list[dict[str, str]]:
    module = load_module(section_id)
    passages: list[dict[str, str]] = []
    for ref in module_refs(module):
        anchor = ref["sourceId"].split("#", 1)[-1].replace("-", " ")
        passages.append(
            {
                "sourceId": ref["sourceId"],
                "sourceHash": ref["passageHash"],
                "label": f"{module['title']}, {anchor}",
                "text": ref["quote"],
                "chapter": module["title"],
                "section": section_id,
            }
        )
    return passages


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _passage_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()


def build_course_chapter(section_id: str) -> dict[str, Any]:
    module = load_module(section_id)
    citations = [
        {"sourceId": passage["sourceId"], "label": passage["label"]}
        for passage in module_passages(section_id)
    ]
    sections = _build_sections(module, section_id)
    return {
        "id": section_id,
        "sectionId": section_id,
        "title": module["title"],
        "sourcePolicy": f"Scientific tutoring answers must use the approved {module['title']} passage store.",
        "learningObjectives": list(module.get("objectives") or []),
        "citations": citations,
        "sections": sections,
        "workedExamples": _build_worked_examples(module),
        "finalQuiz": {
            "id": f"quiz-{section_id}",
            "questions": _build_final_quiz(module, section_id),
        },
    }


def _source_ids(item: dict[str, Any]) -> list[str]:
    ids = [ref["sourceId"] for ref in _collect_refs(item)]
    return ids or []


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0] if parts and parts[0] else text.strip()


def _tokens(text: str) -> list[str]:
    stop = {
        "about",
        "according",
        "because",
        "chapter",
        "following",
        "reaction",
        "section",
        "their",
        "there",
        "these",
        "which",
        "with",
    }
    seen: set[str] = set()
    result: list[str] = []
    for token in re.findall(r"[A-Za-z0-9]+", text.lower()):
        if len(token) < 4 or token in stop or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def _accepted_terms(answer: str) -> list[list[str]]:
    terms = _tokens(answer)
    if not terms:
        return [[str(answer).strip().lower()]]
    return [[term] for term in terms[:3]]


def _choice_id(index: int) -> str:
    return chr(ord("a") + index)


def _normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _section_match_score(check: dict[str, Any], section: dict[str, Any]) -> int:
    review_target = _normalize_key(str(check.get("reviewTarget", "")))
    if not review_target:
        return 0
    section_blob = " ".join(
        [
            str(section.get("id", "")),
            str(section.get("title", "")),
            str(section.get("content", "")),
            str(section.get("reviewTarget", "")),
        ]
    )
    normalized_blob = _normalize_key(section_blob)
    score = 0
    if review_target in normalized_blob:
        score += 8
    target_tokens = [token for token in review_target.split() if len(token) > 2]
    for token in target_tokens:
        if token in normalized_blob:
            score += 1
    return score


def _checkpoint_from_check(check: dict[str, Any], section_id: str, index: int) -> dict[str, Any]:
    choices = check.get("choices")
    answer = str(check.get("answer", "")).strip()
    source_ids = _source_ids(check)
    base = {
        "id": f"cp-{section_id}-{index + 1}",
        "prompt": str(check.get("question", "")).strip(),
        "hint": f"Review the source passage for {check.get('reviewTarget', 'this topic')}.",
        "explanation": str(check.get("explanation", answer)).strip(),
        "misconceptionTags": [f"{section_id}_checkpoint_review"],
        "sourceIds": source_ids,
    }
    if isinstance(choices, list) and choices:
        normalized_answer = answer.lower()
        mapped_choices = [
            {"id": _choice_id(i), "text": str(choice)}
            for i, choice in enumerate(choices)
        ]
        correct = next(
            (
                choice["id"]
                for choice in mapped_choices
                if choice["text"].strip().lower() == normalized_answer
            ),
            "a",
        )
        return {**base, "type": "multiple_choice", "choices": mapped_choices, "answer": correct}
    if answer.lower() in {"true", "false"}:
        return {
            **base,
            "type": "multiple_choice",
            "choices": [{"id": "a", "text": "True"}, {"id": "b", "text": "False"}],
            "answer": "a" if answer.lower() == "true" else "b",
        }
    return {**base, "type": "short_text", "acceptedTerms": _accepted_terms(answer)}


def _auto_checkpoint(section: dict[str, Any], section_id: str, index: int) -> dict[str, Any]:
    title = str(section.get("title", "this section"))
    content = str(section.get("content", ""))
    source_ids = _source_ids(section)
    return {
        "id": f"cp-{section_id}-section-{index + 1}",
        "prompt": f"Which statement best matches {title}?",
        "type": "multiple_choice",
        "choices": [
            {"id": "a", "text": _first_sentence(content)},
            {"id": "b", "text": "This topic is not covered in the approved chapter material."},
        ],
        "answer": "a",
        "hint": f"Review the explanation under {title}.",
        "explanation": _first_sentence(content),
        "misconceptionTags": [f"{section_id}_section_review"],
        "sourceIds": source_ids,
    }


def _build_sections(module: dict[str, Any], section_id: str) -> list[dict[str, Any]]:
    sections = list(module.get("sections") or [])
    assigned: list[list[dict[str, Any]]] = [[] for _ in sections]
    for index, check in enumerate(module.get("checks") or []):
        scored = [
            (_section_match_score(check, section), section_index)
            for section_index, section in enumerate(sections)
        ]
        scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        best_score, best_index = scored[0]
        if best_score <= 0:
            continue
        assigned[best_index].append(_checkpoint_from_check(check, section_id, index))

    result: list[dict[str, Any]] = []
    for index, section in enumerate(sections):
        section_checkpoints = assigned[index] or [_auto_checkpoint(section, section_id, index)]
        result.append(
            {
                "id": str(section.get("id") or f"section-{index + 1}"),
                "title": str(section.get("title", f"Section {index + 1}")),
                "concept": str(section.get("title", "")),
                "sourceIds": _source_ids(section),
                "explanationBlocks": [str(section.get("content", "")).strip()],
                "keyIdeaCards": [
                    {"title": "Key idea", "text": _first_sentence(str(section.get("content", "")))},
                    {"title": "Source", "text": "This section is grounded in the approved course passage listed in its citations."},
                ],
                "checkpoints": section_checkpoints,
            }
        )
    return result


def _build_worked_examples(module: dict[str, Any]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for index, example in enumerate(module.get("workedExamples") or []):
        examples.append(
            {
                "id": f"we-{index + 1}",
                "title": f"Worked example: {example.get('question', 'practice')}",
                "prompt": str(example.get("question", "")),
                "steps": [str(step) for step in example.get("steps", [])],
                "answer": str(example.get("answer", "")),
                "sourceIds": _source_ids(example),
            }
        )
    return examples or [
        {
            "id": "we-review",
            "title": "Worked example: review the chapter",
            "prompt": f"How should you approach {module['title']} questions?",
            "steps": ["Identify the relevant section.", "Use the cited source passage.", "Apply the chapter's stated relationship or definition."],
            "answer": "Use the approved chapter material and cite the supporting passage.",
            "sourceIds": [ref["sourceId"] for ref in module_refs(module)[:1]],
        }
    ]


def _quiz_question(item: dict[str, Any], section_id: str, index: int) -> dict[str, Any]:
    answer = str(item.get("answer", "")).strip()
    choices = item.get("choices")
    source_ids = _source_ids(item)
    if isinstance(choices, list) and choices:
        mapped = [{"id": _choice_id(i), "text": str(choice)} for i, choice in enumerate(choices)]
        normalized_answer = answer.lower()
        correct = next(
            (
                choice["id"]
                for choice in mapped
                if choice["text"].strip().lower() == normalized_answer
            ),
            "a",
        )
    else:
        mapped = [
            {"id": "a", "text": answer},
            {"id": "b", "text": "The approved chapter material says the opposite."},
            {"id": "c", "text": "The approved chapter material does not discuss this topic."},
        ]
        correct = "a"
    return {
        "id": f"quiz-{section_id}-{index + 1}",
        "prompt": str(item.get("question", "")),
        "choices": mapped,
        "answer": correct,
        "explanation": str(item.get("explanation", answer)),
        "sourceIds": source_ids,
    }


def _build_final_quiz(module: dict[str, Any], section_id: str) -> list[dict[str, Any]]:
    items = module.get("practiceQuestions") or []
    if items:
        return [_quiz_question(item, section_id, index) for index, item in enumerate(items)]
    items = module.get("checks") or []
    return [_quiz_question(item, section_id, index) for index, item in enumerate(items)]
