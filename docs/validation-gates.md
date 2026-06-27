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

## Gate 3 — Claim support / entailment (FUTURE)

**Question:** *Does the cited passage substantively support what the tutor says?*

Deterministic-first, model-last:
- deterministic: important-term overlap, equations present/derivable in source,
  numeric values match, negation/direction checks, and detection of citations
  reused indiscriminately across unrelated claims.
- only the genuinely ambiguous remainder goes to a small auditor model for
  entailment review.

**Does NOT guarantee:** pedagogical quality or MCAT exam relevance — only that
claims are supported by their cited sources.

---

## Current test results (2026-06-27)

- `tests/test_citations.py` (Gate 2 resolver): **8 passing**.
- `tests/test_migrate_citations.py` (migration converter): **4 passing**.
- `tests/test_validation_guard.py` (Gate 1 + Gate 2 integration): **12 passing**.
- `benchmarks/production-pilot/tests/test_pipeline.py` (existing): **28 passing**,
  unaffected.
