from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTEXT_FILE = ROOT / "input" / "context.md"
CANDIDATE_FILE = ROOT / "output" / "candidate-module.json"
AUDIT_FILE = ROOT / "output" / "phi-audit.json"
RUN_FILE = ROOT / "logs" / "phi-audit-performance.json"

OLLAMA_URL = "http://localhost:11434/api/generate"

AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["pass", "pass_with_concerns", "fail"],
        },
        "unsupported_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "location": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["claim", "location", "reason"],
                "additionalProperties": False,
            },
        },
        "equation_issues": {
            "type": "array",
            "items": {"type": "string"},
        },
        "source_reference_issues": {
            "type": "array",
            "items": {"type": "string"},
        },
        "pedagogy_issues": {
            "type": "array",
            "items": {"type": "string"},
        },
        "assessment_issues": {
            "type": "array",
            "items": {"type": "string"},
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_repairs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "summary": {"type": "string"},
    },
    "required": [
        "verdict",
        "unsupported_claims",
        "equation_issues",
        "source_reference_issues",
        "pedagogy_issues",
        "assessment_issues",
        "strengths",
        "recommended_repairs",
        "summary",
    ],
    "additionalProperties": False,
}


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else "phi4-mini"

    context = CONTEXT_FILE.read_text(encoding="utf-8-sig")
    candidate = CANDIDATE_FILE.read_text(encoding="utf-8-sig")

    prompt = f"""
Act as an independent quality auditor for an MCAT tutoring lesson.

Audit rules:
- Treat the context packet as the only permitted factual source.
- Do not introduce outside facts.
- Identify claims that are absent from or conflict with the packet.
- Check whether source references genuinely support their sections.
- Check equation accuracy and whether items labeled equations are truly equations.
- Evaluate conceptual progression, explanatory clarity, and completeness.
- Check whether assessments test material actually taught.
- Do not rewrite the lesson.
- Report only specific, actionable findings.
- Do not invent defects merely to appear critical.

CONTEXT PACKET START
{context}
CONTEXT PACKET END

CANDIDATE MODULE START
{candidate}
CANDIDATE MODULE END
""".strip()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": AUDIT_SCHEMA,
        "keep_alive": 0,
        "options": {
            "temperature": 0,
            "seed": 42,
            "num_ctx": 16384,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"Auditor: {model}")
    print(f"Context characters: {len(context)}")
    print(f"Candidate characters: {len(candidate)}")
    print("Independent audit started.")

    started = time.perf_counter()

    with urllib.request.urlopen(request, timeout=600) as response:
        outer = json.loads(response.read().decode("utf-8"))

    elapsed = time.perf_counter() - started
    raw = outer.get("response", "")
    audit = json.loads(raw)

    AUDIT_FILE.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    performance = {
        "model": model,
        "elapsed_seconds": round(elapsed, 3),
        "done_reason": outer.get("done_reason"),
        "total_duration_ns": outer.get("total_duration"),
        "load_duration_ns": outer.get("load_duration"),
        "prompt_eval_count": outer.get("prompt_eval_count"),
        "prompt_eval_duration_ns": outer.get("prompt_eval_duration"),
        "eval_count": outer.get("eval_count"),
        "eval_duration_ns": outer.get("eval_duration"),
        "verdict": audit.get("verdict"),
        "unsupported_claim_count": len(audit.get("unsupported_claims", [])),
        "recommended_repair_count": len(
            audit.get("recommended_repairs", [])
        ),
    }

    RUN_FILE.write_text(
        json.dumps(performance, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Elapsed seconds: {elapsed:.3f}")
    print(f"Verdict: {audit.get('verdict')}")
    print(
        "Unsupported claims:",
        len(audit.get("unsupported_claims", [])),
    )
    print(
        "Recommended repairs:",
        len(audit.get("recommended_repairs", [])),
    )
    print(f"Audit report: {AUDIT_FILE}")
    print(f"Performance report: {RUN_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
