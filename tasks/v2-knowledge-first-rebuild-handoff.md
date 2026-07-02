# MCAT Tutor V2 Knowledge-First Rebuild Handoff

Status: upstream gate CLEARED by user-supplied exact URLs (2026-07-02). All
four upstreams below are now confirmed. Codex may vendor and begin Phase A/B
implementation against this manifest.

## Archive state

- Current v1 failure state is preserved by tag `archive/v1-failed-product`.
- Tag exists locally and on origin at `cad0045618e569e4a2cd9ecdbbea17c18d6db134`.
- Active rebuild branch is `v2/knowledge-first-rebuild`, tracking `origin/v2/knowledge-first-rebuild`.
- Do not delete the current repository.
- Do not build v2 on the current chapter renderer, dashboard, or content-to-JSON-to-page pipeline.

## Confirmed upstreams

### Impeccable

- Repository: `https://github.com/pbakaus/impeccable.git`
- Pinned commit: `44c27a72af98394c32691ba79358811bff86bde6` (tag `skill-v3.9.1`)
- Vendored path: `vendor/impeccable/` (CORRECTED — an earlier draft PR (#1,
  branch `worktree-impeccable-vendor`) vendored this as a git submodule at
  `.impeccable/` against the pre-rebuild base branch. That does not match
  the `vendor/<name>/` + subtree + `.UPSTREAM` convention established by
  Open Notebook, and that PR targets a superseded base. Re-vendor fresh
  against `v2/knowledge-first-rebuild`; treat PR #1 as superseded/closeable.)
- License: Apache License 2.0. No upstream `NOTICE` file — no attribution
  obligation beyond preserving `LICENSE` in the vendored copy.
- Vendoring method: `git subtree --prefix=vendor/impeccable --squash`
  (matches Open Notebook's pattern exactly).
- What it actually is: not a UI component library. It's a design-guidance
  skill for AI coding agents — installs as `/impeccable` (23 subcommands:
  `craft`, `critique`, `audit`, `polish`, `harden`, etc.) plus 45
  deterministic anti-pattern detector rules, into `.claude/`/`.codex/`
  config directories. Activation requires running its own CLI
  (`node vendor/impeccable/scripts/build.js --skip-root-sync` then
  `node vendor/impeccable/cli/bin/cli.js link --source=vendor/impeccable
  --providers=claude,codex` — build from the vendored source itself, not
  `npx impeccable@npm`, since the published npm version (3.2.0) does not
  match this pinned commit's version (3.9.1)). Not yet activated in any
  branch as of this handoff.
- Role: design-system guidance, visual critique, interaction quality,
  accessibility, responsive review.
- Constraint: must guide the production design system and review loop, not
  merely exist as a vendored folder.

### Open Notebook

- Repository: `https://github.com/lfnovo/open-notebook`
- Branch: `main`
- Upstream pin: `14ba8f51e81f34855cd21c390f2576215d8808dd`
- Local path: `vendor/open-notebook`
- Provenance file: `vendor/open-notebook.UPSTREAM`
- Role: source collections, retrieval, citation candidates, study guides, FAQs, summaries, transformations, source-grounded synthesis.
- Constraint: Open Notebook is not the learner UI.

### Karpathy-style LLM Wiki

- Exact source, supplied directly by the user (2026-07-02): gist
  `442a6bf555914893e9891c11519de94f`, reachable as either
  `https://gist.github.com/442a6bf555914893e9891c11519de94f.git` or
  `https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
  (same gist — gist IDs are globally unique regardless of the username
  segment in the URL).
- Pinned revision: `ac46de1ad27f92b28ac95459c782c07f6b8c964a`
- Vendored path: `vendor/llm-wiki/llm-wiki.md`
- What it actually is: **not a software repository.** One 12KB markdown
  file — a design-pattern/idea document (author's own words: "designed to
  be copy pasted to your own LLM Agent"). No code, no build tooling,
  nothing to submodule or build. Describes a three-layer pattern (raw
  sources → LLM-maintained wiki → a schema doc like CLAUDE.md/AGENTS.md
  telling the agent how to maintain it) and three operations (ingest,
  query, lint), plus `index.md` (content-oriented catalog) and `log.md`
  (append-only chronological record) conventions.
- License: **none stated.** GitHub gists default to all-rights-reserved
  absent an explicit license. The document's own text explicitly invites
  copy-paste use into an agent's context for exactly this purpose, which
  is a reasonable basis for this specific use — but it is not a clean
  Apache/MIT grant. Cite provenance wherever this pattern is used; do not
  present the compiled wiki architecture as original invention.
- Vendoring method: plain source copy (verbatim), not submodule/subtree —
  there is no repository structure to speak of. Add
  `vendor/llm-wiki.UPSTREAM` matching the Open Notebook provenance-file
  format, and a `THIRD_PARTY_NOTICES.md` entry that prominently states the
  no-license caveat above.
- Role: this is the design pattern Phase C (wiki-compiler) is built
  against — canonical concept pages, `index.md`/`log.md` conventions, the
  ingest/query/lint operations — adapted for MCAT source material using
  this repo's existing `raw/` → `wiki/` → schema (`CLAUDE.md`) convention,
  which already loosely follows this same shape.

### Understand Anything

- Exact source, supplied directly by the user (2026-07-02):
  `https://github.com/Egonex-AI/Understand-Anything.git`
- Pinned commit: `54754a6f97051d1d76c8758353d8ea41afe502a6`
- Vendored path: `vendor/understand-anything/`
- License: MIT (Copyright (c) 2026 Yuxiang Lin; Copyright (c) 2026 Infinite
  Universe, Inc.) — clean, permissive.
- Vendoring method: `git subtree --prefix=vendor/understand-anything
  --squash` (matches Open Notebook's pattern).
- Important scoping note: this ships `.claude-plugin/`, `.cursor-plugin/`,
  `.copilot-plugin/` — it is an AI-coding-agent plugin (the same one
  already installed in the Claude Code environment managing this repo),
  not a standalone graph database service. Its built-in skills (e.g.
  `understand-anything:understand-knowledge`, described as analyzing "a
  Karpathy-pattern LLM wiki knowledge base" to produce an entity/relation
  knowledge graph) are explicitly built to consume the exact LLM-wiki
  pattern above — the two upstreams are designed to compose. But its
  default output is a general entity/relationship graph for *understanding*
  a knowledge base (architecture/domain analysis), not a
  pedagogy-specific prerequisite/misconception/remediation graph. Phase D
  (`services/graph-builder`) will need to either (a) invoke its analyzer
  skills against the compiled MCAT wiki and post-process the output into
  MCAT-specific node/edge types (prerequisites, misconceptions,
  remediation routes), or (b) use its `cli/engine/*` graph-extraction code
  as a library and extend it with those pedagogy-specific types. It is not
  a drop-in prerequisite-graph engine out of the box — flag this explicitly
  when Phase D is scoped, don't assume it's a bigger lift than expected or
  a smaller one.

## Build gate

CLEARED. All four upstreams (Impeccable, Open Notebook, Karpathy LLM Wiki,
Understand Anything) have exact confirmed URLs, pinned revisions, target
`vendor/` paths, and vendoring methods above. Codex may now:

1. Vendor Impeccable, Karpathy LLM Wiki, and Understand Anything per the
   methods specified above (Open Notebook is already vendored).
2. Establish the v2 monorepo structure (`apps/`, `services/`, `packages/`,
   `knowledge/`, `agents/`, `tests/` — `vendor/` already exists).
3. Begin Phase B (ingestion) implementation.

Do not re-litigate these upstreams or substitute similarly named
alternatives — they were supplied directly by the user, not discovered or
guessed.

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

## Data contracts

Formalized as real JSON Schema files (draft 2020-12, matching this repo's
existing `schemas/module.schema.json` convention) at:

- `packages/schemas/wiki-concept-page.schema.json` — Phase C output
- `packages/schemas/graph-node.schema.json` — Phase D output
- `packages/schemas/tutor-request.schema.json` — Phase G input

All three share a `conceptId` id space (`^[a-z0-9]+(\.[a-z0-9-]+)+$`, e.g.
`biochem.amino-acid.isoelectric-point`) — a wiki page's `conceptId` must
resolve to a graph node with the same id, which the pedagogy engine uses to
populate `activeConcept` in a tutor request.

## Known state as of this handoff (2026-07-02)

- `local-multimodel-pm` has a merged UI rebuild (PR #3, "ui-khan-experience",
  commit `35ad0d6`) that consolidated the two old homepage surfaces and
  removed raw section IDs from the visible UI — done *after* the v1 archive
  tag and *not* present on `v2/knowledge-first-rebuild`. This is correct:
  v2 should not build on it (it's a patch to the old chapter-JSON-to-page
  pipeline this rebuild replaces). It isn't in the v1 archive tag either
  (tagged before it merged), so it currently exists only on
  `local-multimodel-pm`. No action needed unless something in it is later
  worth extracting once it "proves it fits the new architecture" per the
  master directive's own rule — flagging so it isn't mistaken for lost work.
- Two earlier draft PRs from the pre-rebuild phase are now superseded and
  candidates to close (user has not yet confirmed closing them):
  - PR #1 (`worktree-impeccable-vendor`) — Impeccable vendored as a
    submodule against the old base; superseded by the corrected
    `vendor/impeccable/` subtree manifest above.
  - PR #2 (`ui-visual-contract`) — a 3-screen UI reconstruction brief for
    the *old* renderer; moot now that v2 replaces that renderer entirely
    rather than restyling it.
