# Validation Gates

Authoritative design doc for how the MCAT pipeline gates generated modules
before they reach students. Three gates, layered. Each answers a different
question and explicitly does **not** answer the next one's.

## Purpose & threat model

The course is student-facing MCAT material. The adversary is not a hacker — it
is a **plausible-but-unsupported model claim**: well-formed JSON, citation-shaped
references, scientifically wrong or unsupported content. Structure alone cannot
catch this. The gates exist to make "valid" mean progressively closer to "true".

Current honest status of the pipeline:

```
well-formed + citation-shaped + gated  ≠  scientifically verified
```

The gates close that gap one layer at a time.

---

## Gate 1 — Artifact integrity (IMPLEMENTED)

**Question:** *Was this exact file the thing that was validated?*

**Mechanism:**
- `scripts/validate-module.py` hashes the exact module bytes it reads
  (`sha256:<hex>`) and writes `moduleHash` + `validatedAt` into the validation
  report.
- `scripts/build-course.py` recomputes the hash of each module before assembly
  and **skips** the module unless the recorded and recomputed hashes match.

**Acceptance criteria (a module ships only if):** a report exists, the report is
well-formed JSON, `valid` is true, `moduleHash` is present, and the recomputed
hash matches.

**Failure behavior:** any failure → module is **skipped, never shipped**. A
distinct skip reason is printed for each cause (missing report, malformed report,
invalid report, missing hash, hash mismatch).

**Does NOT guarantee:** that any citation resolves, that cited passages exist, or
that the content is true. It only proves the validated bytes are the shipped
bytes — i.e. no edit-after-validation drift.

**Tests:** `tests/test_validation_guard.py` — unchanged module ships,
edited-after-validation skipped, missing hash skipped, malformed report skipped,
revalidated module ships.

---

## Gate 2 — Citation integrity (IMPLEMENTED)

**Question:** *Does the cited passage exist, resolve, and remain unchanged?*

Replaces bare/line-range citation strings with structured citations that point at
a specific passage in canonical `wiki/*.md` source:

```json
{
  "sourceId": "wiki/thermodynamics.md#gibbs-free-energy-g",
  "quote": "A reaction is spontaneous when ΔG is negative.",
  "passageHash": "sha256:<hex>"
}
```

**Deterministic checks (no LLM), in order:** citation is a well-formed object →
source file exists → heading-slug anchor resolves to exactly one heading →
`passageHash` matches the hash of the normalized resolved passage (heading line
through the next heading of equal-or-higher depth) → `quote` is a normalized
substring of that passage. Any failure → validation error.

A changed source changes the passage hash → dependent validation fails. Legacy
string citations are accepted during migration but recorded as **unverified**,
never silently passed as Gate-2-clean.

**Citation scope.** Citations come in two scopes:
- **claim** — attached to a specific section / equation / worked example /
  question. These gate `citationsVerified`: every claim citation must be a
  verified structured object, or the module is not citation-verified.
- **provenance** — the module-level `sourceRefs` listing *which source files*
  were used. These are recorded (`legacyCitationCount`) but **excluded** from
  `citationsVerified`, because file-level provenance is not a passage-level claim.

**Mechanism:**
- `scripts/citations.py` — the deterministic resolver (no LLM).
- `scripts/validate-module.py` — verifies claim citations (failures are errors),
  flags legacy strings as warnings (errors under `--strict`), and writes
  `legacyCitationCount` + `citationsVerified` to the report.
- `scripts/build-course.py` — **by default** skips any module whose
  `citationsVerified` is not true (citation integrity is enforced by default).
  Use `--allow-unverified-citations` as an explicit escape hatch to ship
  unverified-but-valid modules.
- `scripts/migrate-citations.py` — converts legacy `file:line-range` refs into
  hashed structured citations and stamps `passageHash` onto model-emitted
  `{sourceId, quote}` pairs; unresolved refs go to a review list, never verified.

**Acceptance criteria (`citationsVerified=true`):** zero legacy claim citations
and zero claim-citation verification failures.

**Failure behavior:** a claim-citation failure is a validation error (module
invalid). An unverified-but-valid module is skipped by the default build and
shipped only with `--allow-unverified-citations`.

**Does NOT guarantee:** that the passage actually *supports* the claim — only
that the citation resolves to real, unchanged source text.

---

## Gate 3 — Claim support (DETERMINISTIC LAYER IMPLEMENTED; auditor model FUTURE)

**Question:** *Does the cited passage substantively support what the tutor says?*

Deterministic-first, model-last. `scripts/claim_support.py` (no LLM) resolves
each claim's cited passage and runs checks that can only **catch contradictions**
or **confirm concrete token matches**. It deliberately cannot prove prose
entailment — whatever it can neither confirm nor refute becomes `ambiguous` with
`auditorRequired=true`, the hand-off point for a future small auditor model.

**Claim-bearing fields evaluated:** `sections.content`, `equations`
(expression + meaning), `workedExamples` (question/steps/answer),
`checks` and `practiceQuestions` (answer + explanation).

**Per-claim result schema (`claimResults[]`):**
```json
{
  "location": "sections[0]",
  "claimText": "…(truncated)…",
  "sourceId": "wiki/thermodynamics.md#gibbs-free-energy",
  "status": "pass | fail | ambiguous | skipped",
  "checks": ["sign", "direction", "negation", "number", "unit", "…"],
  "failureReasons": ["…"],
  "auditorRequired": false
}
```

**Governing rule (contradiction-safe):** a claim may **pass only when every
extracted concrete assertion is supported and no contradiction is detected**. One
matching number / unit / symbol must never mask another unsupported or
contradictory assertion. `pass` = ≥1 concrete assertion, ALL concrete assertions
supported, no contradiction, no soft flag; `fail` = any contradiction;
`ambiguous` = no contradiction but something unconfirmable (prose, an unsupported
number, an unparseable equation, a negation/conditional difference) → auditor;
`skipped` = no resolvable structured citation. Token overlap alone never yields
`pass`.

**Concrete assertions** (the only things that can earn a pass): physical
quantities, bare numbers, parsed equations, worked-example final answers.

**Hard-fail contradiction checks:**
- **Dimensional quantities** — values parsed *with* units, normalized to a base
  unit, compared after conversion. Supported unit families: concentration
  (M, mM, μM/uM, nM), time (s, ms, min, h), energy (J, kJ), molar energy
  (J/mol, kJ/mol), mass (g, mg, kg), volume (L, mL, μL/uL), pressure
  (Pa, kPa, atm, mmHg), temperature (K, °C/C, affine). Molar prefixes are
  case-sensitive (M≠m). Same-family quantities that differ after conversion fail
  (30 M vs 30 mM, 30 kJ/mol vs 30 J/mol); equivalent ones pass (60 s = 1 min,
  1000 J = 1 kJ).
- **Numeric completeness** — every claim-side number must be matched in the
  source; a matching number cannot hide an extra unsupported/contradictory one.
- **Equation relationships** — equations are parsed into normalized forms.
  Additive equations compare as sign-normalized term sets (algebraically
  equivalent forms pass: `ΔG = ΔH − TΔS` ≡ `ΔH = ΔG + TΔS`; reversed/sign-flipped
  fail: `ΔG = TΔS − ΔH`). Single-division equations cross-multiply (`x = a/b` vs
  `x = b/a` fail). Anything outside the parser is **ambiguous, never auto-pass**.
- **Worked-example final answer** — supported arithmetic steps are recomputed and
  compared (with units/tolerance) to the stated final answer; `10−4=6` with final
  answer `5` fails. Unparseable calculations are ambiguous.
- **sign reversal**, **direction reversal**, **answer/explanation inconsistency**.
  The linguistic checks (sign/direction/negation) fire only when the claim
  *restates* the source (≥0.6 keyword containment), suppressing false positives
  in long prose.

**Soft signals (→ ambiguous, never a hard fail):** **negation polarity**
(scope-blind: a correct "not a donor" or a T/F answer of "False" is
indistinguishable from a real flip) and **conditional→universal** strengthening
(a universalization may be a correct restatement of a universally-true
conditional). Both block `pass` and route to the auditor, but never assert a
false contradiction.

**Citation reuse** is recorded as metadata only — it never downgrades an
otherwise-valid claim, so summary-heavy modules stay shippable.

**Report fields:** `claimsVerified` (all claims pass), `claimPassCount`,
`claimFailCount`, `claimAmbiguousCount`, `claimSkippedCount`,
`sourceDependencyHash`, `claimResults`.

**Source freshness.** Each report stores `sourceDependencyHash`, an aggregate of
every resolved claim citation's *current* source-passage hash. `build-course.py
--require-claim-support` recomputes it and skips the module if any cited source
changed after validation — closing the gap where the module bytes are unchanged
but a cited source was edited.

**Build gate (opt-in):** `scripts/build-course.py --require-claim-support` skips a
module when any claim failure exists, `claimsVerified` is not true, or the source
dependency hash no longer matches. Off by default; Gate 1/Gate 2 unchanged.

**Known blind spots:** prose entailment (most descriptive sentences are
`ambiguous`); paraphrased / derived numbers; negation and conditional scope;
synonyms the keyword overlap misses; equations beyond linear/single-division;
multi-sentence reasoning. These are the auditor-model phase's job.

**Does NOT guarantee:** pedagogical quality or MCAT exam relevance — only that
claims do not deterministically contradict, and are token-consistent with, their
cited sources.

---

## Current test results (2026-06-27)

- `tests/test_citations.py` (Gate 2 resolver): **8 passing**.
- `tests/test_migrate_citations.py` (migration converter): **4 passing**.
- `tests/test_claim_support.py` (Gate 3 deterministic): **22 passing**.
- `tests/test_claim_support_adversarial.py` (Gate 3 bypass probes): **20 passing**.
- `tests/test_validation_guard.py` (Gate 1 + Gate 2 + Gate 3 integration):
  **19 passing**.
- `benchmarks/production-pilot/tests/test_pipeline.py` (existing): **28 passing**,
  unaffected.
- **Total: 101 passing.**

**Gate 3 production dry-run (5 modules, 81 claims):** 18 pass · 0 fail ·
63 ambiguous · 0 skipped. (Contradiction-safe: no false contradictions; prose and
unconfirmable assertions route to the auditor, so no production module is
`claimsVerified` until the auditor phase lands.)
