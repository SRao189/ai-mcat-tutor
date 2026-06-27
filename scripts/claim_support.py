#!/usr/bin/env python3
"""Gate 3: deterministic claim-support validation (NO LLM).

For every claim-bearing field in a module, resolve its cited passage(s) and run
deterministic checks that can only *catch contradictions* and *confirm concrete
token matches*. It deliberately cannot prove prose entailment — anything it
cannot confirm or refute is marked `ambiguous` with `auditorRequired=true`, which
is where a future small auditor model (Gate 3 phase 2) takes over.

Status meaning per claim:
- pass      : no contradiction AND at least one concrete supporting signal matched
              (number / sign / direction / unit / equation-symbol present in source)
- fail      : a deterministic contradiction was found
- ambiguous : no contradiction, but nothing concrete to confirm support (prose)
- skipped   : the claim has no resolvable structured citation to check against

Run as a dry-run:  python scripts/claim_support.py course-data/module-1.json
"""
import json
import re
import sys
from math import isclose
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citations  # noqa: E402

# ---- tunable ceilings (ponytail: named so they're easy to revisit) ----------
# A sourceId reused by at least this fraction of all claims (and at least this
# many, with a minimum module size) is flagged as over-reused -> auditorRequired.
REUSE_FRACTION = 0.5
REUSE_MIN_COUNT = 4
REUSE_MIN_TOTAL = 5
ARITH_REL_TOL = 1e-3

NEGATION = {"not", "no", "never", "cannot", "without", "neither", "none",
            "isn't", "aren't", "doesn't", "don't", "won't", "n't"}
INCREASE = {"increase", "increases", "increasing", "increased", "rise", "rises",
            "rising", "higher", "greater", "more", "grows", "growth", "gain"}
DECREASE = {"decrease", "decreases", "decreasing", "decreased", "fall", "falls",
            "falling", "lower", "less", "fewer", "smaller", "drop", "drops",
            "decline", "loss"}
CONDITIONAL = {"when", "if", "under", "assuming", "provided", "given",
               "standard", "equilibrium", "only"}
ABSOLUTE = {"always", "never", "all", "every", "any", "regardless",
            "unconditionally", "must", "guaranteed"}
STOPWORDS = {"the", "a", "an", "of", "to", "is", "are", "was", "were", "be",
             "and", "or", "in", "on", "for", "with", "as", "by", "that", "this",
             "it", "its", "from", "at", "which", "when", "than", "then", "but",
             "can", "will", "has", "have", "into", "such", "more", "less",
             "between", "because", "due", "also", "these", "those"}
# units only count when adjacent to a number, which kills false positives from
# stray letters like 'm', 'k', 's' inside ordinary words.
UNIT = r"(kj/mol|kcal/mol|j/mol|kj|kcal|kelvin|°c|atm|kpa|pa|mol/l|mol|m/s)"
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
UNIT_RE = re.compile(r"-?\d+(?:\.\d+)?\s*(" + UNIT + r")")
ARITH_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*([-+*x×/])\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)")


def nrm(text: str) -> str:
    """lowercase + collapse whitespace + normalize math glyphs."""
    t = text.lower().replace("∆", " delta ").replace("δ", " delta ")
    t = t.replace("−", "-").replace("–", "-")
    return re.sub(r"\s+", " ", t).strip()


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z']+", nrm(text)))


def keywords(text: str) -> set[str]:
    return {w for w in words(text) if len(w) >= 4 and w not in STOPWORDS}


def numbers(text: str) -> set[float]:
    return {float(m) for m in NUM_RE.findall(nrm(text))}


def units(text: str) -> set[str]:
    # only units written next to a number count (kills stray-letter matches)
    return {m.group(1) for m in UNIT_RE.finditer(nrm(text))}


def has(text: str, vocab: set[str]) -> bool:
    return bool(words(text) & vocab)


def equation_symbols(expression: str) -> set[str]:
    """Variable-like tokens from an equation expression (operators dropped)."""
    t = nrm(expression)
    t = re.sub(r"[=+\-*/^()]", " ", t)
    toks = t.split()
    syms: set[str] = set()
    i = 0
    while i < len(toks):
        if toks[i] == "delta" and i + 1 < len(toks):
            syms.add(f"delta {toks[i+1]}")
            i += 2
        else:
            if toks[i] and not toks[i].isdigit():
                syms.add(toks[i])
            i += 1
    return syms


def _arith_ok(steps: list[str]) -> tuple[bool, list[str]]:
    """Verify any 'a op b = c' arithmetic found in steps. Returns (ok, bad)."""
    bad: list[str] = []
    for step in steps:
        for a, op, b, c in ARITH_RE.findall(nrm(str(step))):
            a, b, c = float(a), float(b), float(c)
            op = "*" if op in ("x", "×") else op
            try:
                got = {"+": a + b, "-": a - b, "*": a * b,
                       "/": a / b if b else None}[op]
            except ZeroDivisionError:
                got = None
            if got is None:
                continue
            if not isclose(got, c, rel_tol=ARITH_REL_TOL, abs_tol=1e-9):
                bad.append(f"{a} {op} {b} = {c} (expected {got})")
    return (not bad), bad


def evaluate_claim(claim_text: str, passage: str, *, kind: str = "section",
                   expression: str | None = None,
                   steps: list[str] | None = None,
                   answer: str | None = None,
                   explanation: str | None = None) -> dict[str, Any]:
    """Run deterministic checks for one claim against its cited passage."""
    checks: list[str] = []
    failures: list[str] = []
    c, p = claim_text, passage
    ckw, pkw = keywords(c), keywords(p)
    related = len(ckw & pkw) >= 1
    # Linguistic-contradiction checks (sign/direction/negation/conditional) are
    # scope-sensitive and only trustworthy when the claim is essentially a
    # restatement of the source sentence. Without this gate, any stray "not" or
    # "positive" in long prose produces false contradictions.
    # ponytail: 0.6 containment threshold; tune if precision/recall shifts.
    restatement = bool(ckw) and len(ckw & pkw) / len(ckw) >= 0.6
    signal = False
    soft: list[str] = []  # not provably wrong, but blocks auto-pass -> auditor

    checks.append("sign")
    if restatement:
        if "negative" in words(c) and "positive" in words(p) \
                and "positive" not in words(c) and "negative" not in words(p):
            failures.append("sign-mismatch: claim 'negative' vs source 'positive'")
        if "positive" in words(c) and "negative" in words(p) \
                and "negative" not in words(c) and "positive" not in words(p):
            failures.append("sign-mismatch: claim 'positive' vs source 'negative'")

    checks.append("direction")
    if restatement:
        if has(c, INCREASE) and has(p, DECREASE) \
                and not has(c, DECREASE) and not has(p, INCREASE):
            failures.append("direction-mismatch: claim increase vs source decrease")
        if has(c, DECREASE) and has(p, INCREASE) \
                and not has(c, INCREASE) and not has(p, DECREASE):
            failures.append("direction-mismatch: claim decrease vs source increase")

    checks.append("negation")
    # Negation is scope-blind deterministically (a correct "not a donor" or a
    # T/F answer of "False" looks identical to a real flip), so a polarity
    # difference is routed to the auditor as ambiguous, never a hard fail.
    if restatement and has(c, NEGATION) != has(p, NEGATION):
        soft.append("negation-polarity-differs: needs auditor review")

    checks.append("number")
    nums_c, nums_p = numbers(c), numbers(p)
    if nums_c:
        if nums_c & nums_p:
            signal = True
        elif nums_p:
            failures.append(
                f"number-mismatch: claim {sorted(nums_c)} not in source "
                f"{sorted(nums_p)}")

    checks.append("unit")
    units_c, units_p = units(c), units(p)
    if units_c and units_p:
        if units_c & units_p:
            signal = True
        elif units_c.isdisjoint(units_p):
            failures.append(
                f"unit-mismatch: claim {sorted(units_c)} vs source "
                f"{sorted(units_p)}")

    checks.append("conditional-vs-absolute")
    if restatement and has(p, CONDITIONAL) and has(c, ABSOLUTE) \
            and not has(c, CONDITIONAL):
        failures.append(
            "conditional-vs-absolute: source is conditional, claim is absolute")

    if kind == "equation" and expression:
        checks.append("equation-symbol")
        syms = equation_symbols(expression)
        np_ = nrm(p)
        present = [s for s in syms if s in np_]
        if syms and len(present) >= max(1, len(syms) // 2):
            signal = True

    if kind == "worked" and steps:
        checks.append("arithmetic")
        ok, bad = _arith_ok(steps)
        if not ok:
            failures.append("arithmetic-error: " + "; ".join(bad))
        elif bad == [] and ARITH_RE.search(nrm(" ".join(map(str, steps)))):
            signal = True

    if kind == "question" and answer is not None and explanation is not None:
        checks.append("answer-explanation-consistency")
        if len(keywords(answer) & keywords(explanation)) >= 1:
            if ("negative" in words(answer)) and ("positive" in words(explanation)) \
                    and "negative" not in words(explanation):
                failures.append("answer-explanation-inconsistent: sign")
            if has(answer, INCREASE) and has(explanation, DECREASE) \
                    and not has(answer, DECREASE):
                failures.append("answer-explanation-inconsistent: direction")

    # --- positive supporting signals (only matter if no contradiction) -------
    if related:
        if "negative" in words(c) and "negative" in words(p):
            signal = True
        if "positive" in words(c) and "positive" in words(p):
            signal = True
        if (has(c, INCREASE) and has(p, INCREASE)) or \
                (has(c, DECREASE) and has(p, DECREASE)):
            signal = True

    if failures:
        status = "fail"
    elif soft:
        status = "ambiguous"
    elif signal:
        status = "pass"
    else:
        status = "ambiguous"

    return {
        "status": status,
        "checks": checks,
        "failureReasons": failures + soft,
        "auditorRequired": status == "ambiguous",
    }


def _structured_ids(refs: list[Any]) -> list[str]:
    return [r["sourceId"] for r in refs
            if citations.is_structured(r) and r.get("sourceId")]


def _resolve_passages(refs: list[Any], repo_root: Path) -> str:
    chunks = []
    for sid in _structured_ids(refs):
        ok, _, passage = citations._resolve(repo_root, sid)
        if ok:
            chunks.append(passage)
    return "\n".join(chunks)


def gather_claims(module: dict[str, Any]) -> list[dict[str, Any]]:
    """Inventory of every claim-bearing field with its text + citations."""
    claims: list[dict[str, Any]] = []

    for i, s in enumerate(module.get("sections", []) or []):
        if isinstance(s, dict):
            claims.append({"location": f"sections[{i}]", "kind": "section",
                           "text": str(s.get("content", "")),
                           "refs": s.get("sourceRefs", []) or []})

    for i, e in enumerate(module.get("equations", []) or []):
        if isinstance(e, dict):
            expr = str(e.get("expression", ""))
            claims.append({"location": f"equations[{i}]", "kind": "equation",
                           "text": f"{expr} {e.get('meaning', '')}",
                           "expression": expr,
                           "refs": e.get("sourceRefs", []) or []})

    for i, w in enumerate(module.get("workedExamples", []) or []):
        if isinstance(w, dict):
            steps = w.get("steps", []) or []
            claims.append({"location": f"workedExamples[{i}]", "kind": "worked",
                           "text": f"{w.get('question','')} {w.get('answer','')} "
                                   f"{' '.join(map(str, steps))}",
                           "steps": steps, "answer": str(w.get("answer", "")),
                           "refs": w.get("sourceRefs", []) or []})

    for field in ("checks", "practiceQuestions"):
        for i, q in enumerate(module.get(field, []) or []):
            if isinstance(q, dict):
                ans, expl = str(q.get("answer", "")), str(q.get("explanation", ""))
                claims.append({"location": f"{field}[{i}]", "kind": "question",
                               "text": f"{ans} {expl}", "answer": ans,
                               "explanation": expl,
                               "refs": q.get("sourceRefs", []) or []})
    return claims


def evaluate_module(module: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    claims = gather_claims(module)
    results: list[dict[str, Any]] = []

    # citation-reuse accounting across the whole module
    id_counts: dict[str, int] = {}
    for cl in claims:
        for sid in set(_structured_ids(cl["refs"])):
            id_counts[sid] = id_counts.get(sid, 0) + 1
    total = len(claims)
    overused = {
        sid for sid, n in id_counts.items()
        if n >= REUSE_MIN_COUNT and total >= REUSE_MIN_TOTAL
        and n >= REUSE_FRACTION * total
    }

    for cl in claims:
        sids = _structured_ids(cl["refs"])
        passage = _resolve_passages(cl["refs"], repo_root)
        if not passage:
            res = {"status": "skipped", "checks": [],
                   "failureReasons": ["no-resolvable-citation"],
                   "auditorRequired": False}
        else:
            res = evaluate_claim(
                cl["text"], passage, kind=cl["kind"],
                expression=cl.get("expression"), steps=cl.get("steps"),
                answer=cl.get("answer"), explanation=cl.get("explanation"))

        # over-reused citation: never an outright fail, but force auditor review
        if set(sids) & overused:
            res["checks"] = res["checks"] + ["citation-reuse"]
            res["auditorRequired"] = True
            if res["status"] == "pass":
                res["status"] = "ambiguous"
                res["failureReasons"] = res["failureReasons"] + [
                    "citation-reuse: sourceId reused across many claims"]

        results.append({
            "location": cl["location"],
            "claimText": cl["text"][:240],
            "sourceId": ";".join(sids) if sids else None,
            "status": res["status"],
            "checks": res["checks"],
            "failureReasons": res["failureReasons"],
            "auditorRequired": res["auditorRequired"],
        })

    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in ("pass", "fail", "ambiguous", "skipped")}
    return {
        "claimsVerified": counts["fail"] == 0 and counts["ambiguous"] == 0
        and counts["skipped"] == 0,
        "claimPassCount": counts["pass"],
        "claimFailCount": counts["fail"],
        "claimAmbiguousCount": counts["ambiguous"],
        "claimSkippedCount": counts["skipped"],
        "claimResults": results,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: claim_support.py <module.json>")
    module = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    out = evaluate_module(module, Path.cwd())
    summary = {k: v for k, v in out.items() if k != "claimResults"}
    print(json.dumps(summary, indent=2))
    for r in out["claimResults"]:
        if r["status"] in ("fail", "ambiguous"):
            print(f"  {r['status'].upper():9} {r['location']:22} "
                  f"{r['failureReasons']}")


if __name__ == "__main__":
    main()
