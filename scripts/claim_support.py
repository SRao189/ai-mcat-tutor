#!/usr/bin/env python3
"""Gate 3: deterministic claim-support validation (NO LLM).

Governing rule (contradiction-safe): a claim may PASS only when every extracted
concrete assertion is supported AND no contradiction is detected. One matching
number / unit / symbol must never mask another contradiction or an unsupported
assertion.

Concrete assertions = physical quantities (number+unit), bare numbers, parsed
equations (kind=equation), and worked-example final answers (kind=worked).
sign / direction / negation / conditional are contradiction detectors only — they
never grant a pass.

Status:
- pass      : >=1 concrete assertion, ALL concrete assertions supported, no
              contradiction, no soft flag.
- fail      : any deterministic contradiction.
- ambiguous : no contradiction but something cannot be confirmed (prose, an
              unsupported number, an unparseable equation, a negation polarity
              difference). auditorRequired=true.
- skipped   : no resolvable structured citation to check against.

Dry-run:  python scripts/claim_support.py course-data/module-1.json
"""
import hashlib
import json
import re
import sys
from math import isclose
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citations  # noqa: E402

# ---- tunable ceilings -------------------------------------------------------
RESTATEMENT_CONTAINMENT = 0.6   # linguistic checks need the claim to restate src
QTY_REL_TOL = 1e-3
ARITH_REL_TOL = 1e-3
REUSE_FRACTION = 0.5            # reuse is metadata only (never a downgrade)
REUSE_MIN_COUNT = 4
REUSE_MIN_TOTAL = 5

# ---- unit families ----------------------------------------------------------
# Molar prefixes are CASE-SENSITIVE (M=molar vs m=milli); everything else is
# matched case-insensitively. Each entry converts a value to the family base.
MOLAR = {"μM": 1e-6, "uM": 1e-6, "mM": 1e-3, "nM": 1e-9, "M": 1.0}
MOLAR_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(μM|uM|mM|nM|M)(?![A-Za-z])")


def _c_to_k(v: float) -> float:
    return v + 273.15


OTHER: dict[str, tuple[str, Any]] = {
    "s": ("time", 1.0), "ms": ("time", 1e-3), "min": ("time", 60.0),
    "h": ("time", 3600.0),
    "kj/mol": ("molar_energy", 1e3), "j/mol": ("molar_energy", 1.0),
    "kj": ("energy", 1e3), "j": ("energy", 1.0),
    "kg": ("mass", 1e3), "mg": ("mass", 1e-3), "g": ("mass", 1.0),
    "ml": ("volume", 1e-3), "μl": ("volume", 1e-6), "ul": ("volume", 1e-6),
    "l": ("volume", 1.0),
    "kpa": ("pressure", 1e3), "mmhg": ("pressure", 133.322),
    "atm": ("pressure", 101325.0), "pa": ("pressure", 1.0),
    "k": ("temperature", 1.0), "°c": ("temperature", _c_to_k),
    "c": ("temperature", _c_to_k),
}
_OTHER_KEYS = sorted(OTHER, key=len, reverse=True)
OTHER_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(k) for k in _OTHER_KEYS)
    + r")(?![A-Za-z])", re.IGNORECASE)

NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
ARITH_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*([-+*x×/])\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)")

NEGATION = {"not", "no", "never", "cannot", "without", "neither", "none",
            "isn't", "aren't", "doesn't", "don't", "won't", "n't"}
INCREASE = {"increase", "increases", "increasing", "increased", "rise", "rises",
            "rising", "higher", "greater", "grows", "growth"}
DECREASE = {"decrease", "decreases", "decreasing", "decreased", "fall", "falls",
            "falling", "lower", "smaller", "drop", "drops", "decline"}
SOURCE_QUALIFIER = {"if", "when", "under", "assuming", "provided", "may", "can",
                    "typically", "often", "generally", "usually", "given"}
CLAIM_UNIVERSAL = {"always", "never", "must", "universally", "necessarily",
                   "all", "none", "every", "guaranteed"}
STOPWORDS = {"the", "a", "an", "of", "to", "is", "are", "was", "were", "be",
             "and", "or", "in", "on", "for", "with", "as", "by", "that", "this",
             "it", "its", "from", "at", "which", "than", "then", "but", "will",
             "has", "have", "into", "such", "these", "those", "you", "your"}


def nrm(text: str) -> str:
    t = text.lower().replace("∆", " delta ").replace("δ", " delta ")
    return re.sub(r"\s+", " ", t.replace("−", "-").replace("–", "-")).strip()


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z']+", nrm(text)))


def keywords(text: str) -> set[str]:
    return {w for w in words(text) if len(w) >= 4 and w not in STOPWORDS}


def has(text: str, vocab: set[str]) -> bool:
    return bool(words(text) & vocab)


def all_numbers(text: str) -> set[float]:
    return {float(x) for x in NUM_RE.findall(text)}


def parse_quantities(text: str) -> list[tuple[str, float, float, str]]:
    """Return (family, base_value, original_value, unit) for each number+unit."""
    out: list[tuple[str, float, float, str]] = []
    for m in MOLAR_RE.finditer(text):
        val = float(m.group(1))
        out.append(("molar", val * MOLAR[m.group(2)], val, m.group(2)))
    for m in OTHER_RE.finditer(text):
        val = float(m.group(1))
        fam, conv = OTHER[m.group(2).lower()]
        base = conv(val) if callable(conv) else val * conv
        out.append((fam, base, val, m.group(2)))
    return out


# ---- equation parsing -------------------------------------------------------
def _eq_norm(s: str) -> str:
    t = s
    t = re.sub(r"(?i)\bequals\b", "=", t)
    t = re.sub(r"(?i)\bplus\b", "+", t)
    t = re.sub(r"(?i)\bminus\b", "-", t)
    t = re.sub(r"(?i)\btimes\b", "*", t)
    t = re.sub(r"(?i)\bdivided by\b", "/", t)
    t = re.sub(r"(?i)\bover\b", "/", t)
    t = t.replace("∆", "#").replace("Δ", "#").replace("δ", "#")
    t = re.sub(r"(?i)delta", "#", t)
    t = t.replace("−", "-").replace("–", "-").lower()
    return re.sub(r"\s+", "", t)


def _factors(term: str) -> tuple[float, tuple[str, ...]]:
    coeff, num, vars_ = 1.0, "", []
    i = 0
    while i < len(term):
        ch = term[i]
        if ch in "0123456789.":  # ASCII only; str.isdigit() also matches ₃, ²
            num += ch
        elif ch == "#" and i + 1 < len(term) and term[i + 1].isascii() \
                and term[i + 1].isalpha():
            vars_.append("d" + term[i + 1])
            i += 1
        elif ch.isascii() and ch.isalpha():
            vars_.append(ch)
        i += 1
    if num not in ("", "."):
        coeff = float(num)
    return coeff, tuple(sorted(vars_))


def _add_terms(side: str) -> dict[tuple[str, ...], float]:
    d: dict[tuple[str, ...], float] = {}
    for part in side.replace("-", "+-").split("+"):
        if not part:
            continue
        sign = 1.0
        if part.startswith("-"):
            sign, part = -1.0, part[1:]
        if not part:
            continue
        coeff, vrs = _factors(part)
        d[vrs] = d.get(vrs, 0.0) + sign * coeff
    return d


def _side_fraction(side: str):
    if side.count("/") > 1:
        return None
    if "/" in side:
        num, den = side.split("/")
    else:
        num, den = side, ""
    _, nv = _factors(num)
    _, dv = _factors(den) if den else (1.0, ())
    return tuple(sorted(nv)), tuple(sorted(dv))


def parse_equation(raw: str):
    """('add', {terms:coeff}) | ('mul', frozenset(product, product)) | None."""
    s = _eq_norm(raw)
    if s.count("=") != 1:
        return None
    lhs, rhs = s.split("=")
    if not lhs or not rhs:
        return None
    if "/" in s:
        a, b = _side_fraction(lhs), _side_fraction(rhs)
        if not a or not b:
            return None
        p1 = tuple(sorted(a[0] + b[1]))
        p2 = tuple(sorted(b[0] + a[1]))
        return ("mul", frozenset([p1, p2]))
    canon: dict[tuple[str, ...], float] = {}
    for k, v in _add_terms(lhs).items():
        canon[k] = canon.get(k, 0.0) + v
    for k, v in _add_terms(rhs).items():
        canon[k] = canon.get(k, 0.0) - v
    canon = {k: v for k, v in canon.items() if abs(v) > 1e-9 and k}
    return ("add", canon) if canon else None


def _eq_vars(parsed) -> frozenset:
    kind, body = parsed
    out: set[str] = set()
    if kind == "add":
        for k in body:
            out.update(k)
    else:
        for tup in body:
            out.update(tup)
    return frozenset(out)


def _eq_equiv(a, b) -> bool:
    if a is None or b is None or a[0] != b[0]:
        return False
    if a[0] == "add":
        if a[1] == b[1]:
            return True
        return {k: -v for k, v in a[1].items()} == b[1]
    return a[1] == b[1]


def _passage_equations(passage: str) -> list:
    found = []
    for piece in re.split(r"[.\n;]", passage):
        norm = _eq_norm(piece)
        for m in re.finditer(r"[#a-z0-9.]+(?:[-+*/=][#a-z0-9.]+)+", norm):
            frag = m.group(0)
            if "=" in frag:
                parsed = parse_equation(frag)
                if parsed:
                    found.append(parsed)
    return found


def equation_verdict(expression: str, passage: str) -> str:
    claim = parse_equation(expression)
    if claim is None:
        return "unsupported"          # unparseable -> never auto-pass
    same = [e for e in _passage_equations(passage)
            if _eq_vars(e) == _eq_vars(claim)]
    if not same:
        return "unsupported"
    if any(_eq_equiv(claim, e) for e in same):
        return "supported"
    return "contradiction"


# kept for the symbol unit test; no longer used to grant a pass
def equation_symbols(expression: str) -> set[str]:
    s = _eq_norm(expression)
    s = re.sub(r"[=+\-*/()]", " ", s)
    syms: set[str] = set()
    for tok in s.split():
        _, vrs = _factors(tok)
        for v in vrs:
            syms.add("delta " + v[1] if v.startswith("d") and len(v) == 2 else v)
    return syms


def _arith_final(steps: list[str], answer: str | None):
    """Return ('ok', last_result) | ('error', detail) | ('unparsed', None)."""
    last = None
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
                return "error", f"{a}{op}{b}={c} (expected {got})"
            last = c
    if last is None:
        return "unparsed", None
    if answer:
        ans = all_numbers(str(answer))
        if ans and not any(isclose(n, last, rel_tol=ARITH_REL_TOL, abs_tol=1e-9)
                           for n in ans):
            return "error", f"steps compute {last} but final answer {sorted(ans)}"
    return "ok", last


def evaluate_claim(claim_text: str, passage: str, *, kind: str = "section",
                   expression: str | None = None,
                   steps: list[str] | None = None,
                   answer: str | None = None,
                   explanation: str | None = None) -> dict[str, Any]:
    c, p = claim_text, passage
    ckw, pkw = keywords(c), keywords(p)
    related = len(ckw & pkw) >= 1
    restatement = bool(ckw) and len(ckw & pkw) / len(ckw) >= RESTATEMENT_CONTAINMENT

    checks: list[str] = []
    contradictions: list[str] = []
    unsupported: list[str] = []
    soft: list[str] = []
    supported = 0

    # --- concrete: quantities (skip for worked; those numbers are computed) ---
    if kind != "worked":
        checks.append("quantity")
        cq, pq = parse_quantities(c), parse_quantities(p)
        p_by_fam: dict[str, list[float]] = {}
        for fam, base, _, _ in pq:
            p_by_fam.setdefault(fam, []).append(base)
        for fam, base, val, unit in cq:
            fams = p_by_fam.get(fam, [])
            if any(isclose(base, b, rel_tol=QTY_REL_TOL, abs_tol=1e-12)
                   for b in fams):
                supported += 1
            elif fams:
                contradictions.append(
                    f"quantity-mismatch: claim {val}{unit} vs source {fam} "
                    f"{sorted(fams)} (base)")
            else:
                unsupported.append(f"unsupported-quantity: {val}{unit}")

        checks.append("number")
        united_vals = {val for _, _, val, _ in cq}
        p_nums = all_numbers(p)
        for n in (all_numbers(c) - united_vals):
            if any(isclose(n, m, rel_tol=QTY_REL_TOL, abs_tol=1e-12)
                   for m in p_nums):
                supported += 1
            else:
                unsupported.append(f"unsupported-number: {n}")

    # --- concrete: equation relationship -------------------------------------
    if kind == "equation" and expression:
        checks.append("equation")
        verdict = equation_verdict(expression, p)
        if verdict == "supported":
            supported += 1
        elif verdict == "contradiction":
            contradictions.append("equation-mismatch: relationship differs")
        else:
            unsupported.append("equation-unparsed-or-unsupported")

    # --- concrete: worked-example arithmetic + final answer ------------------
    if kind == "worked" and steps:
        checks.append("arithmetic")
        verdict, detail = _arith_final(steps, answer)
        if verdict == "ok":
            supported += 1
        elif verdict == "error":
            contradictions.append(f"arithmetic-error: {detail}")
        # unparsed -> no concrete assertion (stays ambiguous)

    # --- contradiction detectors (no positive credit) ------------------------
    checks.append("sign")
    if restatement:
        if "negative" in words(c) and "positive" in words(p) \
                and "positive" not in words(c) and "negative" not in words(p):
            contradictions.append("sign-mismatch: claim negative vs source positive")
        if "positive" in words(c) and "negative" in words(p) \
                and "negative" not in words(c) and "positive" not in words(p):
            contradictions.append("sign-mismatch: claim positive vs source negative")

    checks.append("direction")
    if restatement:
        if has(c, INCREASE) and has(p, DECREASE) \
                and not has(c, DECREASE) and not has(p, INCREASE):
            contradictions.append("direction-mismatch: increase vs decrease")
        if has(c, DECREASE) and has(p, INCREASE) \
                and not has(c, INCREASE) and not has(p, DECREASE):
            contradictions.append("direction-mismatch: decrease vs increase")

    # conditional source vs universal claim: padding with topic words cannot
    # bypass this (one shared keyword is enough; no containment threshold).
    # Soft, not a hard fail: a universalization may be a correct restatement of a
    # universally-true conditional ("when X, Y must happen" -> "X and Y always"),
    # which deterministic code cannot distinguish from a material over-claim. It
    # still blocks pass (-> auditor) so the claim cannot ship.
    checks.append("conditional-vs-universal")
    if related and has(c, CLAIM_UNIVERSAL) and has(p, SOURCE_QUALIFIER) \
            and not has(c, SOURCE_QUALIFIER):
        soft.append(
            "conditional-vs-universal: source qualified, claim universalized "
            "(needs auditor)")

    checks.append("negation")
    if restatement and has(c, NEGATION) != has(p, NEGATION):
        soft.append("negation-polarity-differs: needs auditor")

    if kind == "question" and answer is not None and explanation is not None:
        checks.append("answer-explanation-consistency")
        if len(keywords(answer) & keywords(explanation)) >= 1:
            if "negative" in words(answer) and "positive" in words(explanation) \
                    and "negative" not in words(explanation):
                contradictions.append("answer-explanation-inconsistent: sign")
            if has(answer, INCREASE) and has(explanation, DECREASE) \
                    and not has(answer, DECREASE):
                contradictions.append("answer-explanation-inconsistent: direction")

    # --- conservative aggregation -------------------------------------------
    if contradictions:
        status = "fail"
    elif unsupported or soft:
        status = "ambiguous"
    elif supported >= 1:
        status = "pass"
    else:
        status = "ambiguous"

    return {
        "status": status,
        "checks": checks,
        "failureReasons": contradictions + unsupported + soft,
        "auditorRequired": status == "ambiguous",
    }


# ---- module-level orchestration --------------------------------------------
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
                           "text": f"{w.get('question','')} {w.get('answer','')}",
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


def source_dependency_hash(module: dict[str, Any], repo_root: Path) -> str:
    """Aggregate hash over the CURRENT content of every cited claim passage, so a
    later source edit is detectable independently of the module bytes."""
    parts: set[str] = set()
    for cl in gather_claims(module):
        for sid in _structured_ids(cl["refs"]):
            ok, _, passage = citations._resolve(repo_root, sid)
            if ok:
                parts.add(f"{sid}={citations.passage_hash(passage)}")
    agg = ";".join(sorted(parts))
    return "sha256:" + hashlib.sha256(agg.encode("utf-8")).hexdigest()


def evaluate_module(module: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    claims = gather_claims(module)
    results: list[dict[str, Any]] = []

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

        # reuse is metadata only: record it, never downgrade a valid claim
        if set(sids) & overused:
            res["checks"] = res["checks"] + ["citation-reuse(info)"]

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
        "sourceDependencyHash": source_dependency_hash(module, repo_root),
        "claimResults": results,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: claim_support.py <module.json>")
    module = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    out = evaluate_module(module, Path.cwd())
    print(json.dumps({k: v for k, v in out.items() if k != "claimResults"},
                     indent=2))
    for r in out["claimResults"]:
        if r["status"] in ("fail", "ambiguous"):
            print(f"  {r['status'].upper():9} {r['location']:22} "
                  f"{r['failureReasons']}")


if __name__ == "__main__":
    main()
