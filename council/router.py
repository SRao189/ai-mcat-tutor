"""Intent router above the verified RAG pipeline.

The rule that matters: *not every message is a RAG query, but every factual
educational claim must stay grounded.*

Greetings, chit-chat, navigation, and short "say that simpler" prompts get a
conversational reply with NO retrieval and NO NVIDIA call. Everything else is
the SAFE DEFAULT and is delegated, unchanged, to the verified, Gate 2/Gate 3
factual pipeline. This module never weakens or bypasses those gates — it only
decides whether the factual pipeline should run at all.

Deterministic-first by design (CLAUDE.md: deterministic code for routing).
A model-backed classifier can be layered in later behind the same `classify`.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

from .roles import new_request_id
from .schema import CouncilResponse, ResponseStatus

# Intent labels.
GREETING = "greeting"
CASUAL = "casual_conversation"
NAVIGATION = "textbook_navigation"
CLARIFICATION = "clarification"
FACTUAL = "factual"  # concept / lesson / quiz / answer-check all flow through the gates

# Conversational intents never touch retrieval or the model.
CONVERSATIONAL_INTENTS = frozenset({GREETING, CASUAL, NAVIGATION, CLARIFICATION})

AnswerFn = Callable[..., CouncilResponse]

# Anchored patterns. They must match the WHOLE message (after trimming) so that
# real factual questions containing these words fall through to FACTUAL.
_TAIL = r"[\s.!?]*$"
_GREETING_RE = re.compile(
    r"^(hi+|hey+|hello+|hiya|yo|howdy|sup|heya|good\s+(morning|afternoon|evening)|what'?s\s+up)" + _TAIL,
    re.I,
)
_CASUAL_RE = re.compile(
    r"^(thanks|thank\s+you|ty|thx|ok(ay)?|cool|nice|great|awesome|got\s+it|makes\s+sense|"
    r"never\s*mind|nvm|lol|bye|goodbye|see\s+ya|cya)" + _TAIL,
    re.I,
)
_NAV_RE = re.compile(
    r"^(go\s+to|open|navigate\s+to|take\s+me\s+to|jump\s+to|show\s+me\s+section|"
    r"next\s+section|previous\s+section|prev\s+section|back\s+to)\b",
    re.I,
)
_CLARIFY_RE = re.compile(
    r"^(why\??|how\s+come|huh|what\?|i('?m|\s+am)?\s*(confused|lost)|"
    r"i\s+don'?t\s+understand|explain\s+(that|it)(\s+more)?\s+simpl(y|er)|"
    r"simpler|more\s+simply|say\s+(that|it)\s+again|what\s+do\s+you\s+mean|"
    r"give\s+me\s+an\s+analogy|can\s+you\s+simplify)" + _TAIL,
    re.I,
)


def classify(text: str) -> str:
    """Classify a learner message. Unknown/ambiguous -> FACTUAL (safe: gated)."""
    t = (text or "").strip()
    if not t:
        return FACTUAL
    if _GREETING_RE.match(t):
        return GREETING
    if _CASUAL_RE.match(t):
        return CASUAL
    if _NAV_RE.match(t):
        return NAVIGATION
    # Clarification only for short prompts, so "why is the second pKa near
    # physiological pH?" stays FACTUAL and gets grounded with a citation.
    if len(t.split()) <= 7 and _CLARIFY_RE.match(t):
        return CLARIFICATION
    return FACTUAL


# Conversational replies avoid scientific claims, so they need no citation.
# Suggestions are phrased so that
# clicking one becomes a FACTUAL question that DOES go through the gates.
_REPLIES: dict[str, tuple[str, tuple[str, ...]]] = {
    GREETING: (
        "Hi! I'm your biochemistry tutor. Where would you like to start in this chapter?",
        (
            "Review the current section",
            "Explain the main equation",
            "Quiz me on this chapter",
            "Ask a question about this chapter",
        ),
    ),
    CASUAL: (
        "Anytime. Want to keep going in this chapter?",
        (
            "Continue the lesson",
            "Quiz me on this chapter",
            "Ask a question about this chapter",
        ),
    ),
    NAVIGATION: (
        "Use the chapter list or the current lesson sections to navigate. What would you like to review?",
        (
            "Review the current section",
            "Open the final quiz",
            "Ask a question about this chapter",
        ),
    ),
    CLARIFICATION: (
        "Happy to break it down. Which part should I explain?",
        (
            "What are the pKa values of phosphoric acid?",
            "Why is phosphate negatively charged at physiological pH?",
            "Why are pyrophosphate bonds high-energy?",
        ),
    ),
}


def _conversational_response(intent: str, *, section_id: str = "") -> CouncilResponse:
    text, suggestions = _REPLIES.get(intent, _REPLIES[GREETING])
    return CouncilResponse(
        request_id=new_request_id(),
        status=ResponseStatus.CONVERSATIONAL,
        answer=text,
        cited_sources=(),
        recommended_next_action="",
        metadata={
            "liveModelCalls": 0,
            "intent": intent,
            "section": section_id,
            "suggestions": list(suggestions),
        },
    )


def route_message(
    question: str,
    *,
    answer_fn: AnswerFn,
    learner_state: dict[str, Any] | None = None,
    section_id: str = "7.1",
    config: Any | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Route one message. Returns a response dict (the server serializes it).

    `answer_fn` is the verified factual pipeline (council.phase1.answer_question).
    It is only called for FACTUAL intents, so greetings never hit the model and
    never return insufficient_evidence.
    """
    intent = classify(question)
    if logger is not None:
        logger.info("route %s", {"intent": intent})

    if intent in CONVERSATIONAL_INTENTS:
        return _conversational_response(intent, section_id=section_id).to_dict()

    # Safe default: the gated factual pipeline, unchanged.
    return answer_fn(
        question,
        section_id=section_id,
        learner_state=learner_state,
        config=config,
        logger=logger,
    ).to_dict()


if __name__ == "__main__":
    assert classify("hi") == GREETING
    assert classify("Hello!") == GREETING
    assert classify("good morning") == GREETING
    assert classify("thanks") == CASUAL
    assert classify("makes sense, thanks") == FACTUAL  # not an exact casual match -> safe default
    assert classify("go to ATP") == NAVIGATION
    assert classify("why?") == CLARIFICATION
    assert classify("explain that more simply") == CLARIFICATION
    assert classify("What are the pKa values of phosphoric acid?") == FACTUAL
    assert classify("Why is the second pKa near physiological pH?") == FACTUAL
    assert classify("what do you mean by the second pKa?") == FACTUAL

    calls: list[str] = []

    def boom(*_a, **_k):  # delegate must NOT run for conversational intents
        calls.append("called")
        raise AssertionError("factual pipeline called for a greeting")

    out = route_message("hi", answer_fn=boom)
    assert out["status"] == "conversational" and not calls
    assert out["metadata"]["suggestions"], "greeting should offer next steps"

    def ok(question, **_k):
        return CouncilResponse(
            request_id="t", status=ResponseStatus.VERIFIED, answer="ok",
            cited_sources=(), metadata={"liveModelCalls": 1},
        )

    out2 = route_message("What are the pKa values of phosphoric acid?", answer_fn=ok)
    assert out2["status"] == "verified"
    print("router self-check passed")
