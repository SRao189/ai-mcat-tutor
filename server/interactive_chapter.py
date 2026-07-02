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


CHAPTER_THERMODYNAMICS: dict[str, Any] = {
    "id": "thermodynamics",
    "sectionId": "thermo",
    "title": "Thermodynamics",
    "sourcePolicy": "Scientific tutoring answers must use the approved Thermodynamics passage store.",
    "learningObjectives": [
        "Distinguish kinetic energy from potential energy in biochemical systems.",
        "Use the First and Second Laws to reason about energy transfer and entropy.",
        "Apply Delta G = Delta H - TDelta S to determine reaction spontaneity.",
        "Relate standard free energy, equilibrium, and actual cellular concentrations.",
        "Use Le Chatelier's principle and Q versus K to predict reaction direction.",
    ],
    "citations": [
        {"sourceId": "thermo-passage-01", "label": "Thermodynamics, Key concepts"},
        {"sourceId": "thermo-passage-02", "label": "Thermodynamics, Laws of thermodynamics"},
        {"sourceId": "thermo-passage-03", "label": "Thermodynamics, Gibbs free energy"},
        {"sourceId": "thermo-passage-04", "label": "Thermodynamics, Standard free energy"},
        {"sourceId": "thermo-passage-05", "label": "Thermodynamics, Actual cellular free energy"},
        {"sourceId": "thermo-passage-06", "label": "Thermodynamics, Le Chatelier and key questions"},
    ],
    "sections": [
        {
            "id": "energy-and-laws",
            "title": "Energy forms and thermodynamic laws",
            "concept": "energy forms, conservation, and entropy",
            "sourceIds": ["thermo-passage-01", "thermo-passage-02"],
            "explanationBlocks": [
                "Thermodynamics starts by tracking energy. Kinetic energy is molecular movement; potential energy is stored in chemical bonds.",
                "For biochemistry, ATP is the central potential-energy storage molecule named in the source material.",
                "The First Law says energy is conserved across the universe, while the Second Law says universal disorder, or entropy, tends to increase.",
            ],
            "keyIdeaCards": [
                {"title": "Energy accounting", "text": "If a system loses energy, the surroundings gain energy."},
                {"title": "Entropy check", "text": "Delta S = S_final - S_initial; a negative Delta S means disorder decreased."},
            ],
            "checkpoints": [
                {
                    "id": "cp-thermo-energy-forms",
                    "prompt": "Name the two primary forms of energy described in this chapter.",
                    "type": "short_text",
                    "acceptedTerms": [["kinetic"], ["potential"]],
                    "hint": "One is motion; the other is stored in bonds.",
                    "explanation": "The Thermodynamics source identifies kinetic energy as movement of molecules and potential energy as energy stored in chemical bonds.",
                    "misconceptionTags": ["energy_form_confusion"],
                    "sourceIds": ["thermo-passage-01"],
                },
                {
                    "id": "cp-thermo-second-law",
                    "prompt": "According to the Second Law, what tends to happen to disorder in the universe?",
                    "type": "multiple_choice",
                    "choices": [
                        {"id": "a", "text": "It tends to increase."},
                        {"id": "b", "text": "It must always decrease."},
                        {"id": "c", "text": "It is unrelated to spontaneous reactions."},
                    ],
                    "answer": "a",
                    "hint": "The Second Law is the entropy law.",
                    "explanation": "The source states that disorder, or entropy, of the universe tends to increase and that spontaneous reactions increase universal disorder.",
                    "misconceptionTags": ["second_law_direction"],
                    "sourceIds": ["thermo-passage-02"],
                },
            ],
        },
        {
            "id": "gibbs-free-energy",
            "title": "Gibbs free energy predicts spontaneity",
            "concept": "Gibbs free energy and reaction spontaneity",
            "sourceIds": ["thermo-passage-03"],
            "explanationBlocks": [
                "Gibbs free energy, Delta G, is the chapter's central test for reaction spontaneity.",
                "The equation is Delta G = Delta H - TDelta S. Temperature must be in Kelvin, and the signs are from the system's perspective.",
                "Delta G less than 0 means spontaneous and exergonic; Delta G greater than 0 means nonspontaneous and endergonic; Delta G equals 0 means equilibrium.",
            ],
            "keyIdeaCards": [
                {"title": "Sign convention", "text": "Negative Delta G means the system goes to lower free energy."},
                {"title": "Cell shortcut", "text": "In cells, volume change is approximately zero, so Delta H is approximately Delta E."},
            ],
            "checkpoints": [
                {
                    "id": "cp-thermo-gibbs-equation",
                    "prompt": "Write the Gibbs free energy equation using Delta G, Delta H, T, and Delta S.",
                    "type": "short_text",
                    "acceptedTerms": [["delta g", "g"], ["delta h", "h"], ["tdelta s", "t delta s", "t*delta s", "t x delta s"]],
                    "hint": "Free energy equals enthalpy minus temperature times entropy.",
                    "explanation": "The approved passage gives Delta G = Delta H - TDelta S.",
                    "misconceptionTags": ["gibbs_equation_confusion"],
                    "sourceIds": ["thermo-passage-03"],
                },
                {
                    "id": "cp-thermo-dg-sign",
                    "prompt": "What does Delta G less than 0 indicate?",
                    "type": "multiple_choice",
                    "choices": [
                        {"id": "a", "text": "A spontaneous, exergonic reaction"},
                        {"id": "b", "text": "A nonspontaneous, endergonic reaction"},
                        {"id": "c", "text": "A system at equilibrium"},
                    ],
                    "answer": "a",
                    "hint": "Negative Delta G means the system goes to lower free energy.",
                    "explanation": "The source states that Delta G less than 0 means spontaneous and exergonic.",
                    "misconceptionTags": ["delta_g_sign_reversal"],
                    "sourceIds": ["thermo-passage-03"],
                },
            ],
        },
        {
            "id": "standard-vs-actual-free-energy",
            "title": "Standard free energy is not always cellular free energy",
            "concept": "standard free energy, equilibrium, Q, and actual Delta G",
            "sourceIds": ["thermo-passage-04", "thermo-passage-05"],
            "explanationBlocks": [
                "Biochemical standard free energy, Delta G degrees prime, is defined at pH 7 with 1 M concentration for all solutes except H+.",
                "Delta G degrees prime connects to equilibrium through Delta G degrees prime = -RT ln K'_eq.",
                "Actual cellular Delta G also depends on concentrations: Delta G = Delta G degrees prime + RT ln Q, where Q uses actual cellular concentrations.",
            ],
            "keyIdeaCards": [
                {"title": "Standard state", "text": "Delta G degrees prime is a reference condition, not necessarily the actual cellular condition."},
                {"title": "Concentration term", "text": "RT ln Q can make actual Delta G differ from Delta G degrees prime."},
            ],
            "checkpoints": [
                {
                    "id": "cp-thermo-standard-state",
                    "prompt": "For biochemical standard free energy, what pH is used?",
                    "type": "short_text",
                    "acceptedTerms": [["7", "ph 7"]],
                    "hint": "The prime mark indicates the biochemical convention.",
                    "explanation": "The source defines Delta G degrees prime under biochemical standard conditions with pH 7.",
                    "misconceptionTags": ["standard_state_ph_confusion"],
                    "sourceIds": ["thermo-passage-04"],
                },
                {
                    "id": "cp-thermo-actual-g",
                    "prompt": "Which equation relates actual cellular Delta G to standard free energy and Q?",
                    "type": "multiple_choice",
                    "choices": [
                        {"id": "a", "text": "Delta G = Delta G degrees prime + RT ln Q"},
                        {"id": "b", "text": "Delta G = Delta H - QDelta S"},
                        {"id": "c", "text": "Delta G degrees prime = RT ln Q only"},
                    ],
                    "answer": "a",
                    "hint": "Actual conditions enter through the reaction quotient.",
                    "explanation": "The actual cellular free energy passage gives Delta G = Delta G degrees prime + RT ln Q.",
                    "misconceptionTags": ["actual_vs_standard_free_energy"],
                    "sourceIds": ["thermo-passage-05"],
                },
            ],
        },
        {
            "id": "reaction-direction",
            "title": "Q versus K predicts direction",
            "concept": "reaction quotient and Le Chatelier direction",
            "sourceIds": ["thermo-passage-05", "thermo-passage-06"],
            "explanationBlocks": [
                "Q uses actual cellular concentrations. Comparing Q to K_eq predicts which direction is spontaneous.",
                "When Q is less than K_eq, Delta G is less than 0 and the forward reaction is spontaneous.",
                "Le Chatelier's principle gives the same direction language: adding reactants drives forward, while adding products drives backward.",
            ],
            "keyIdeaCards": [
                {"title": "Forward trigger", "text": "Q < K_eq means forward reaction is spontaneous."},
                {"title": "Equilibrium trigger", "text": "Q = K_eq means Delta G = 0 and neither direction is favored."},
            ],
            "checkpoints": [
                {
                    "id": "cp-thermo-q-vs-k",
                    "prompt": "If Q is less than K_eq, which direction is spontaneous?",
                    "type": "multiple_choice",
                    "choices": [
                        {"id": "a", "text": "Forward"},
                        {"id": "b", "text": "Reverse"},
                        {"id": "c", "text": "Neither; the system is at equilibrium"},
                    ],
                    "answer": "a",
                    "hint": "Low Q means relatively more reactants than the equilibrium ratio.",
                    "explanation": "The source states that Q < K_eq gives Delta G < 0, so the forward reaction is spontaneous.",
                    "misconceptionTags": ["q_k_direction_reversal"],
                    "sourceIds": ["thermo-passage-05"],
                },
                {
                    "id": "cp-thermo-rate",
                    "prompt": "Does K_eq indicate reaction rate?",
                    "type": "multiple_choice",
                    "choices": [
                        {"id": "a", "text": "No, it indicates relative concentrations at equilibrium."},
                        {"id": "b", "text": "Yes, larger K_eq always means a faster reaction."},
                    ],
                    "answer": "a",
                    "hint": "This chapter separates thermodynamic position from speed.",
                    "explanation": "The key-questions passage states that K_eq indicates only relative concentrations at equilibrium, not reaction rate.",
                    "misconceptionTags": ["thermodynamics_vs_rate"],
                    "sourceIds": ["thermo-passage-06"],
                },
            ],
        },
    ],
    "workedExamples": [
        {
            "id": "we-thermo-positive-standard-negative-actual",
            "title": "MCAT-style example: positive standard free energy, negative actual free energy",
            "prompt": "Can actual Delta G be negative if Delta G degrees prime is positive?",
            "steps": [
                "Start with Delta G = Delta G degrees prime + RT ln Q.",
                "A positive Delta G degrees prime means the standard-state term alone is unfavorable.",
                "Actual cellular concentrations can make RT ln Q sufficiently negative.",
                "When that concentration term is negative enough, the sum can become Delta G less than 0.",
            ],
            "answer": "Yes. Actual Delta G can be negative if RT ln Q is sufficiently negative.",
            "sourceIds": ["thermo-passage-05", "thermo-passage-06"],
        }
    ],
    "finalQuiz": {
        "id": "quiz-thermodynamics",
        "questions": [
            {
                "id": "quiz-thermo-dg-sign",
                "prompt": "A reaction has Delta G less than 0. How should it be described?",
                "choices": [
                    {"id": "a", "text": "Spontaneous and exergonic"},
                    {"id": "b", "text": "Nonspontaneous and endergonic"},
                    {"id": "c", "text": "At equilibrium"},
                ],
                "answer": "a",
                "explanation": "The Gibbs passage states that Delta G less than 0 means spontaneous and exergonic.",
                "sourceIds": ["thermo-passage-03"],
            },
            {
                "id": "quiz-thermo-standard-equilibrium",
                "prompt": "What is Delta G degrees prime when K'_eq equals 1?",
                "choices": [
                    {"id": "a", "text": "0"},
                    {"id": "b", "text": "Always positive"},
                    {"id": "c", "text": "Always negative"},
                ],
                "answer": "a",
                "explanation": "The standard free energy passage states that when K'_eq = 1, Delta G degrees prime = 0 because ln 1 = 0.",
                "sourceIds": ["thermo-passage-04"],
            },
            {
                "id": "quiz-thermo-q-direction",
                "prompt": "When Q is greater than K_eq, which direction is spontaneous?",
                "choices": [
                    {"id": "a", "text": "Reverse"},
                    {"id": "b", "text": "Forward"},
                    {"id": "c", "text": "Neither direction"},
                ],
                "answer": "a",
                "explanation": "The actual free energy passage states that Q > K_eq gives Delta G > 0 and the reverse reaction is spontaneous.",
                "sourceIds": ["thermo-passage-05"],
            },
            {
                "id": "quiz-thermo-keq-rate",
                "prompt": "What does K_eq indicate in this chapter?",
                "choices": [
                    {"id": "a", "text": "Relative concentrations at equilibrium"},
                    {"id": "b", "text": "Reaction rate"},
                    {"id": "c", "text": "Temperature in Kelvin"},
                ],
                "answer": "a",
                "explanation": "The key-questions passage states that K_eq indicates only relative concentrations at equilibrium, not reaction rate.",
                "sourceIds": ["thermo-passage-06"],
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
    "thermo": CHAPTER_THERMODYNAMICS,
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
