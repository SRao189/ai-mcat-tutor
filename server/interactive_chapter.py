"""Reusable interactive chapter data and deterministic lesson helpers."""

from __future__ import annotations

import copy
import re
from typing import Any


CHAPTER_7_1: dict[str, Any] = {
    "id": "chapter-7-section-7.1",
    "sectionId": "7.1",
    "title": "Phosphorus-Containing Compounds",
    "sourcePolicy": "Scientific tutoring answers must use the approved Chapter 7.1 passage store.",
    "learningObjectives": [
        "Predict the major phosphate species near physiological pH from phosphoric acid pKas.",
        "Explain why pyrophosphate hydrolysis is thermodynamically favorable.",
        "Identify nucleotide parts and connect ATP phosphoanhydride bonds to short-term energy storage.",
    ],
    "citations": [
        {"sourceId": "chapter-7-1-passage-01", "label": "Chapter 7.1, Phosphoric acid dissociation"},
        {"sourceId": "chapter-7-1-passage-02", "label": "Chapter 7.1, Pyrophosphate hydrolysis"},
        {"sourceId": "chapter-7-1-passage-03", "label": "Chapter 7.1, Phosphate anhydride energy"},
        {"sourceId": "chapter-7-1-passage-04", "label": "Chapter 7.1, Nucleotide structure"},
        {"sourceId": "chapter-7-1-passage-05", "label": "Chapter 7.1, ATP and nucleotide energy"},
    ],
    "sections": [
        {
            "id": "phosphoric-acid",
            "title": "Phosphoric acid behaves like a three-step acid",
            "concept": "phosphoric acid dissociation",
            "sourceIds": ["chapter-7-1-passage-01"],
            "explanationBlocks": [
                "Phosphoric acid can donate three protons, so it has three dissociation steps.",
                "The pKas are 2.1, 7.2, and 12.4. Around physiological pH, the second pKa matters most because it is close to 7.4.",
                "At physiological pH, phosphate exists mostly as anions, especially hydrogen phosphate and dihydrogen phosphate.",
            ],
            "keyIdeaCards": [
                {"title": "MCAT trigger", "text": "When pH is near a pKa, both conjugate acid/base forms are present."},
                {"title": "Physiology link", "text": "The extracellular mixture is mostly HPO4 2- with substantial H2PO4 -."},
            ],
            "checkpoints": [
                {
                    "id": "cp-pka-order",
                    "prompt": "List the three pKa values for phosphoric acid in increasing order.",
                    "type": "short_text",
                    "acceptedTerms": [["2.1"], ["7.2"], ["12.4"]],
                    "hint": "There are three values because phosphoric acid can donate three protons.",
                    "explanation": "The approved passage gives phosphoric acid pKas as 2.1, 7.2, and 12.4.",
                    "misconceptionTags": ["missing_triprotic_pattern", "pka_order_confusion"],
                    "sourceIds": ["chapter-7-1-passage-01"],
                },
                {
                    "id": "cp-phys-phosphate",
                    "prompt": "At physiological pH, which pair is most important: HPO4 2- / H2PO4 - or fully protonated H3PO4 / neutral phosphate?",
                    "type": "multiple_choice",
                    "choices": [
                        {"id": "a", "text": "HPO4 2- and H2PO4 -"},
                        {"id": "b", "text": "H3PO4 and neutral phosphate"},
                    ],
                    "answer": "a",
                    "hint": "Physiological pH is close to the second pKa, not the first or third.",
                    "explanation": "At physiological pH, the passage says phosphate exists largely in anionic form, with HPO4 2- and H2PO4 - as the common extracellular species.",
                    "misconceptionTags": ["physiological_phosphate_species"],
                    "sourceIds": ["chapter-7-1-passage-01"],
                },
            ],
        },
        {
            "id": "pyrophosphate-energy",
            "title": "Pyrophosphate hydrolysis releases usable free energy",
            "concept": "pyrophosphate hydrolysis",
            "sourceIds": ["chapter-7-1-passage-02", "chapter-7-1-passage-03"],
            "explanationBlocks": [
                "Orthophosphate is a single phosphate unit. Two orthophosphates joined through an anhydride linkage form pyrophosphate.",
                "Pyrophosphate hydrolysis is strongly favorable: about -7 kcal/mol under standard conditions and about -12 kcal/mol in cells.",
                "The products are lower in free energy because charge repulsion is relieved, resonance stabilization improves, and water interactions improve.",
            ],
            "keyIdeaCards": [
                {"title": "Energy language", "text": "High-energy bond means hydrolysis is favorable; it does not mean the bond is unstable by itself."},
                {"title": "Why products win", "text": "Orthophosphate is stabilized by resonance and hydration."},
            ],
            "checkpoints": [
                {
                    "id": "cp-pyrophosphate-bond",
                    "prompt": "What linkage joins two orthophosphates to make pyrophosphate?",
                    "type": "short_text",
                    "acceptedTerms": [["anhydride"], ["p-o-p", "p o p", "phosphate anhydride"]],
                    "hint": "Look for the named linkage between two phosphate groups.",
                    "explanation": "Two orthophosphates bound through an anhydride linkage form pyrophosphate.",
                    "misconceptionTags": ["confuses_ester_and_anhydride"],
                    "sourceIds": ["chapter-7-1-passage-02"],
                },
                {
                    "id": "cp-energy-reason",
                    "prompt": "Name one reason phosphate anhydride hydrolysis is favorable.",
                    "type": "short_text",
                    "acceptedTerms": [["repelling", "repulsion", "negative charges"], ["resonance"], ["water", "hydration"]],
                    "hint": "Think about charge relief, resonance, or interactions with water.",
                    "explanation": "The passage names three reasons: relief of repelling negative charges, more resonance forms in orthophosphate, and more favorable interaction with water.",
                    "misconceptionTags": ["high_energy_bond_literalism"],
                    "sourceIds": ["chapter-7-1-passage-03"],
                },
            ],
        },
        {
            "id": "nucleotides-atp",
            "title": "ATP is a ribonucleotide energy carrier",
            "concept": "ATP and nucleotide structure",
            "sourceIds": ["chapter-7-1-passage-04", "chapter-7-1-passage-05"],
            "explanationBlocks": [
                "A nucleotide contains a sugar, a nitrogenous base, and one to three phosphate units.",
                "The base attaches to carbon 1 of the ribose ring, while phosphate units attach to carbon 5.",
                "ATP is a ribonucleotide and the universal short-term energy storage molecule in cellular metabolism.",
            ],
            "keyIdeaCards": [
                {"title": "Structure anchor", "text": "Base at carbon 1; phosphate at carbon 5."},
                {"title": "Energy anchor", "text": "ATP stores food energy immediately in phosphoanhydride bonds."},
            ],
            "checkpoints": [
                {
                    "id": "cp-nucleotide-parts",
                    "prompt": "Which three parts make up a nucleotide?",
                    "type": "short_text",
                    "acceptedTerms": [["sugar", "ribose", "deoxyribose"], ["base", "purine", "pyrimidine"], ["phosphate"]],
                    "hint": "A nucleotide has one carbohydrate part, one base, and phosphate units.",
                    "explanation": "Each nucleotide contains a ribose or deoxyribose sugar, a purine or pyrimidine base, and one to three phosphate units.",
                    "misconceptionTags": ["missing_nucleotide_component"],
                    "sourceIds": ["chapter-7-1-passage-04"],
                },
                {
                    "id": "cp-atp-role",
                    "prompt": "ATP is best described as which kind of molecule?",
                    "type": "multiple_choice",
                    "choices": [
                        {"id": "a", "text": "A universal short-term energy storage ribonucleotide"},
                        {"id": "b", "text": "A long-term lipid energy reserve"},
                        {"id": "c", "text": "A DNA-only pyrimidine nucleotide"},
                    ],
                    "answer": "a",
                    "hint": "ATP has ribose and phosphate units and is used immediately by cells.",
                    "explanation": "The passage describes ATP as a universal short-term energy storage molecule and a ribonucleotide.",
                    "misconceptionTags": ["atp_identity_confusion"],
                    "sourceIds": ["chapter-7-1-passage-05"],
                },
            ],
        },
    ],
    "workedExamples": [
        {
            "id": "we-phys-pH",
            "title": "MCAT-style example: phosphate species near pH 7.4",
            "prompt": "A passage states that phosphoric acid has pKas of 2.1, 7.2, and 12.4. At extracellular pH, which species should be prominent?",
            "steps": [
                "Find the pKa closest to physiological pH: 7.2 is closest to about 7.4.",
                "Use the conjugate pair around that dissociation step: H2PO4 - and HPO4 2-.",
                "Because the pH is slightly above the pKa, the more deprotonated form, HPO4 2-, should be somewhat more common.",
            ],
            "answer": "HPO4 2- and H2PO4 - are prominent, with HPO4 2- more common in extracellular fluid.",
            "sourceIds": ["chapter-7-1-passage-01"],
        }
    ],
    "finalQuiz": {
        "id": "quiz-7-1",
        "questions": [
            {
                "id": "quiz-triprotic",
                "prompt": "Why does phosphoric acid have three pKa values?",
                "choices": [
                    {"id": "a", "text": "It can donate three protons."},
                    {"id": "b", "text": "It contains three carbons."},
                    {"id": "c", "text": "It is always fully protonated."},
                ],
                "answer": "a",
                "explanation": "Three dissociation equilibria correspond to the potential to donate three protons.",
                "sourceIds": ["chapter-7-1-passage-01"],
            },
            {
                "id": "quiz-pyro-dg",
                "prompt": "What is the approximate cellular free energy change for pyrophosphate hydrolysis?",
                "choices": [
                    {"id": "a", "text": "About -12 kcal/mol"},
                    {"id": "b", "text": "About +12 kcal/mol"},
                    {"id": "c", "text": "About 0 kcal/mol"},
                ],
                "answer": "a",
                "explanation": "The passage gives the actual cellular free energy change as about -12 kcal/mol.",
                "sourceIds": ["chapter-7-1-passage-02"],
            },
            {
                "id": "quiz-atp",
                "prompt": "Where is food energy immediately stored in ATP?",
                "choices": [
                    {"id": "a", "text": "In phosphoanhydride bonds"},
                    {"id": "b", "text": "In the purine base only"},
                    {"id": "c", "text": "In peptide bonds"},
                ],
                "answer": "a",
                "explanation": "Energy extracted from foodstuffs is immediately stored in ATP phosphoanhydride bonds.",
                "sourceIds": ["chapter-7-1-passage-05"],
            },
        ],
    },
}


REQUIRED_CHAPTER_KEYS = {
    "title",
    "learningObjectives",
    "sections",
    "workedExamples",
    "citations",
    "finalQuiz",
}

CHAPTERS: dict[str, dict[str, Any]] = {
    "7.1": CHAPTER_7_1,
}


def list_chapters() -> list[dict[str, str]]:
    return [
        {"id": section_id, "title": chapter["title"]}
        for section_id, chapter in CHAPTERS.items()
    ]


def get_chapter(section_id: str = "7.1") -> dict[str, Any]:
    if section_id not in CHAPTERS:
        raise KeyError(section_id)
    return copy.deepcopy(CHAPTERS[section_id])


def validate_chapter_schema(chapter: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_CHAPTER_KEYS - set(chapter))
    if missing:
        errors.append("missing chapter keys: " + ", ".join(missing))
    if not chapter.get("learningObjectives"):
        errors.append("chapter must include learning objectives")
    for section in chapter.get("sections", []):
        for key in ("id", "title", "explanationBlocks", "keyIdeaCards", "checkpoints", "concept"):
            if not section.get(key):
                errors.append(f"section {section.get('id', '?')} missing {key}")
        for checkpoint in section.get("checkpoints", []):
            for key in ("id", "prompt", "hint", "explanation", "misconceptionTags", "sourceIds"):
                if not checkpoint.get(key):
                    errors.append(f"checkpoint {checkpoint.get('id', '?')} missing {key}")
    if not chapter.get("finalQuiz", {}).get("questions"):
        errors.append("final quiz must include questions")
    return errors


def find_checkpoint(
    checkpoint_id: str,
    chapter: dict[str, Any] | None = None,
    section_id: str = "7.1",
) -> tuple[dict[str, Any], dict[str, Any]]:
    active = chapter or get_chapter(section_id)
    for section in active["sections"]:
        for checkpoint in section.get("checkpoints", []):
            if checkpoint["id"] == checkpoint_id:
                return section, checkpoint
    raise KeyError(checkpoint_id)


def normalize_answer(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _term_present(answer: str, options: list[str]) -> bool:
    return any(normalize_answer(option) in answer for option in options)


def evaluate_checkpoint(
    checkpoint_id: str,
    answer: Any,
    chapter: dict[str, Any] | None = None,
    section_id: str = "7.1",
) -> dict[str, Any]:
    active = chapter or get_chapter(section_id)
    section, checkpoint = find_checkpoint(checkpoint_id, active, section_id)
    normalized = normalize_answer(answer)
    if not normalized:
        return {
            "checkpointId": checkpoint_id,
            "sectionId": section["id"],
            "result": "incorrect",
            "completed": False,
            "detectedMisconception": checkpoint["misconceptionTags"][0],
            "explanation": checkpoint["explanation"],
            "sourceIds": checkpoint["sourceIds"],
        }

    if checkpoint["type"] == "multiple_choice":
        correct = normalized == normalize_answer(checkpoint["answer"])
        result = "correct" if correct else "incorrect"
    else:
        groups = checkpoint.get("acceptedTerms", [])
        matched = sum(1 for group in groups if _term_present(normalized, group))
        if matched == len(groups):
            result = "correct"
        elif matched:
            result = "partial"
        else:
            result = "incorrect"

    completed = result == "correct"
    misconception = "" if completed else checkpoint["misconceptionTags"][0]
    return {
        "checkpointId": checkpoint_id,
        "sectionId": section["id"],
        "result": result,
        "completed": completed,
        "detectedMisconception": misconception,
        "explanation": checkpoint["explanation"],
        "sourceIds": checkpoint["sourceIds"],
    }


def default_learner_state(section_id: str = "phosphoric-acid") -> dict[str, Any]:
    return {
        "chapter": "7.1",
        "currentSection": section_id,
        "currentConcept": "",
        "latestCheckpoint": "",
        "completedCheckpoints": [],
        "checkpointAttempts": {},
        "detectedMisconception": "",
        "chapterQuizScore": None,
    }


def update_progress(
    learner_state: dict[str, Any] | None,
    section_id: str,
    checkpoint_id: str,
    evaluation: dict[str, Any],
    chapter_id: str = "7.1",
) -> dict[str, Any]:
    state = default_learner_state(section_id)
    if isinstance(learner_state, dict):
        state.update(copy.deepcopy(learner_state))
    get_chapter(chapter_id)
    state["chapter"] = chapter_id
    state["currentSection"] = section_id
    state["latestCheckpoint"] = checkpoint_id
    attempts = dict(state.get("checkpointAttempts") or {})
    attempts[checkpoint_id] = int(attempts.get(checkpoint_id, 0)) + 1
    state["checkpointAttempts"] = attempts
    completed = list(state.get("completedCheckpoints") or [])
    if evaluation.get("completed") and checkpoint_id not in completed:
        completed.append(checkpoint_id)
    state["completedCheckpoints"] = completed
    state["detectedMisconception"] = evaluation.get("detectedMisconception") or ""
    return state


def grade_final_quiz(
    answers: dict[str, Any],
    learner_state: dict[str, Any] | None = None,
    section_id: str = "7.1",
) -> dict[str, Any]:
    chapter = get_chapter(section_id)
    questions = chapter["finalQuiz"]["questions"]
    results = []
    correct = 0
    for question in questions:
        selected = normalize_answer(answers.get(question["id"]))
        ok = selected == normalize_answer(question["answer"])
        if ok:
            correct += 1
        results.append(
            {
                "questionId": question["id"],
                "result": "correct" if ok else "incorrect",
                "correctAnswer": question["answer"],
                "explanation": question["explanation"],
                "sourceIds": question["sourceIds"],
            }
        )
    score = {"correct": correct, "total": len(questions)}
    state = default_learner_state()
    if isinstance(learner_state, dict):
        state.update(copy.deepcopy(learner_state))
    state["chapter"] = section_id
    state["chapterQuizScore"] = score
    return {"score": score, "results": results, "learnerState": state}


def build_tutor_context(learner_state: dict[str, Any] | None, section_id: str = "7.1") -> dict[str, Any]:
    chapter = get_chapter(section_id)
    state = default_learner_state()
    if isinstance(learner_state, dict):
        state.update(copy.deepcopy(learner_state))
    state["chapter"] = section_id
    section_by_id = {section["id"]: section for section in chapter["sections"]}
    section = section_by_id.get(state.get("currentSection")) or chapter["sections"][0]
    state["currentSectionTitle"] = section["title"]
    state["currentConcept"] = section["concept"]
    return state
