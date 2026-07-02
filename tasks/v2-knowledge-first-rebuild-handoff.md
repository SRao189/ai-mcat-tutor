# MCAT Tutor V2 Knowledge-First Rebuild Handoff

Status: blocked before implementation until upstream URLs are exact.

## Archive state

- Current v1 failure state is preserved by tag `archive/v1-failed-product`.
- Tag exists locally and on origin at `cad0045618e569e4a2cd9ecdbbea17c18d6db134`.
- Active rebuild branch is `v2/knowledge-first-rebuild`, tracking `origin/v2/knowledge-first-rebuild`.
- Do not delete the current repository.
- Do not build v2 on the current chapter renderer, dashboard, or content-to-JSON-to-page pipeline.

## Confirmed upstreams

### Impeccable

- Repository: `https://github.com/pbakaus/impeccable.git`
- Local pin: `44c27a72af98394c32691ba79358811bff86bde6`
- Local path: `impeccable/`
- Role: design-system guidance, visual critique, interaction quality, accessibility, responsive review.
- Constraint: must guide the production design system and review loop, not merely exist as a vendored folder.

### Open Notebook

- Repository: `https://github.com/lfnovo/open-notebook`
- Branch: `main`
- Upstream pin: `14ba8f51e81f34855cd21c390f2576215d8808dd`
- Local path: `vendor/open-notebook`
- Provenance file: `vendor/open-notebook.UPSTREAM`
- Role: source collections, retrieval, citation candidates, study guides, FAQs, summaries, transformations, source-grounded synthesis.
- Constraint: Open Notebook is not the learner UI.

## Not yet confirmed

These cannot be treated as authorized exact upstreams until the manager/user confirms them.

### Karpathy-style LLM Wiki

- Candidate source found: `https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
- Reason not yet exact enough: this is a GitHub gist / idea file, while the directive says to use the exact Karpathy-style LLM Wiki repository supplied by the user.
- Risk: multiple similarly named community repositories exist; choosing one would violate the non-negotiable URL rule.

### Understand Anything

- Candidate source found: `https://github.com/Egonex-AI/Understand-Anything`
- Reason not yet exact enough: this was discovered externally, not supplied or pinned in the current repo.
- Risk: building against this without confirmation would let Codex guess a similarly named repository.

## Build gate

Before Codex creates the v2 monorepo structure or vendors additional systems, Claude must provide a review/task manifest with exact approved upstreams for:

- Karpathy-style LLM Wiki
- Understand Anything

The manifest must include, for each upstream:

- Repository URL or gist URL
- Commit SHA or immutable revision
- Expected vendored path under `vendor/`
- License/provenance note
- Whether Codex should vendor by submodule, subtree, or source copy

## Required architecture

The v2 system is knowledge-first:

```text
Raw PDFs / books / notes
-> document extraction
-> Karpathy-style LLM Wiki
-> NVIDIA Council ingestion verification
-> Understand Anything graph
-> Open Notebook
-> pedagogy engine
-> learner interface
-> NVIDIA Council verified tutor responses
```

The NVIDIA Council appears twice:

- PDF/source ingestion: verify wiki knowledge and citation support.
- Tutor response: verify retrieved-answer support before final output.

The AI does not change model weights. Durable knowledge lives in the verified wiki, graph, retrieval indexes, and learner memory.

## Claude-Codex contract

- Claude is manager and independent reviewer.
- Codex is implementer.
- Claude and Codex communicate through task manifests, commits, tests, screenshots, review JSON, and repair requests.
- Claude must not pretend to be Codex.
- Codex must not approve its own work.
- No simulated agent dialogue.
