# MCAT Tutoring Production Pilot

Vertical slice: **raw chapter → normalized source → context packet → Gemma
session → Phi audit → (justified) Qwen additive patch → deterministic
validation → offline HTML**.

## Run

```bash
cd benchmarks/production-pilot
python -m pipeline.run                       # all chapters in config
python -m pipeline.run --chapters chapter-03 # one chapter
python -m tests.test_pipeline                # offline regression tests
```

Config lives in `config/chapters.json` (chapter source paths, section scope,
model names, output dir). All paths are **relative to the repo root** and
resolved at runtime — no absolute paths.

## Stages & checkpoints

Each chapter advances through explicit states written to
`output/<chapter>/checkpoint.json`:
`DISCOVERED → NORMALIZED → CONTEXT_READY → GENERATING → GENERATED →
STRUCTURE_VALIDATED → AUDITING → AUDITED → ENRICHING → ENRICHED → FINAL_AUDIT →
ACCEPTED` (or `QUARANTINED`). Stages are idempotent; a failed chapter is
quarantined with a report while the next chapter continues.

A model stage gets **one automatic retry**. Qwen only runs when Phi reports an
actionable concern; its patch is applied only if every addition is
source-grounded, non-duplicative, and deletes nothing — otherwise the Gemma
candidate is kept (`SAFE_NO_OP` / `enrichment_rejected_kept_candidate`).
Before structural validation, item-level `sourceRefs` are normalized by code to
the configured packet reference (or the matching subsection packet reference in
chapter mode), with citation repairs recorded in the cleaning/citation reports.

## Separation of concerns (and what changes for AWS)

| Component | File | Responsibility | Changes when... |
|-----------|------|----------------|-----------------|
| Model adapter | `pipeline/adapter.py` | the **only** Ollama-aware code (generate, canary, unload, availability) | swap to a hosted/containerized endpoint: reimplement these 4 fns; bearer auth + HTTPS replace localhost |
| Source processing | `pipeline/source.py` | deterministic normalize + compact packet | unchanged |
| Orchestration + validation | `pipeline/core.py`, `pipeline/run.py` | config, state machine, merge/grounding, validator bridge, retries, quarantine | storage swap: replace `resolve()`/`Path` reads/writes with object-storage (S3) get/put; replace the in-process loop with a queue/worker dispatch |
| Presentation | `pipeline/render.py` | offline self-contained HTML | swap for a web/React renderer; consumes the same `final-session.json` |
| Validation authority | `scripts/validate-module.py` | structural pass/fail | unchanged |

The content pipeline does not care about its environment. Only **storage**
(filesystem → object storage) and the **model adapter** (Ollama → hosted) differ
between the local app and an AWS worker. No AWS services are wired here.

## Known ceilings (ponytail)

- Grounding is bag-of-words overlap (`core.is_grounded`), not semantic
  entailment — upgrade to embeddings/NLI if false-accepts appear.
- Context packets are scoped to each chapter's **first major section** to stay
  compact and time-bounded; the full normalized chapter is preserved in
  `normalized-source.md`. Next step: iterate over all sections per chapter.
- Residual OCR intra-word spacing from PDF extraction (e.g. `t he`) is passed
  through, not "corrected" — repairing it would require outside knowledge the
  pipeline is forbidden from using.
