# Third-Party Notices

## Open Notebook

- Upstream repository: https://github.com/lfnovo/open-notebook
- Pinned commit: 14ba8f51e81f34855cd21c390f2576215d8808dd (branch `main`)
- License: MIT (see `vendor/open-notebook/LICENSE`)
- Integration date: 2026-07-01
- Vendored via `git subtree --prefix=vendor/open-notebook --squash`
- Copyright (c) 2024 Luis Novo

Open Notebook is used as a source-ingestion, retrieval, and notebook-organization
subsystem. It is integrated behind `integrations/open_notebook_adapter/` and does not
replace or bypass the NVIDIA Council's citation gating, claim-support verification, or
approved-source enforcement — Open Notebook supplies retrieval candidates only; the
Council remains the final authority on what reaches a learner.

## Impeccable

- Upstream repository: https://github.com/pbakaus/impeccable.git
- Pinned commit: 44c27a72af98394c32691ba79358811bff86bde6 (tag `skill-v3.9.1`)
- License: Apache-2.0 (see `vendor/impeccable/LICENSE`)
- Integration date: 2026-07-02
- Vendored via `git subtree --prefix=vendor/impeccable --squash`

Impeccable is used as design guidance and visual-review tooling for later
learner-facing UI work. It is not treated as a component library.

## Understand Anything

- Upstream repository: https://github.com/Egonex-AI/Understand-Anything.git
- Pinned commit: 54754a6f97051d1d76c8758353d8ea41afe502a6
- License: MIT (see `vendor/understand-anything/LICENSE`)
- Integration date: 2026-07-02
- Vendored via `git subtree --prefix=vendor/understand-anything --squash`
- Copyright (c) 2026 Yuxiang Lin
- Copyright (c) 2026 Infinite Universe, Inc.

Understand Anything is vendored for the later graph-builder phase. Its default
entity/relation graph output will require adaptation before it can act as the
MCAT prerequisite, misconception, and remediation graph.

## Karpathy LLM Wiki

- Upstream gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Pinned revision: ac46de1ad27f92b28ac95459c782c07f6b8c964a
- License: none stated
- Integration date: 2026-07-02
- Vendored via plain source copy to `vendor/llm-wiki/llm-wiki.md`

This gist is a design-pattern reference document, not executable software.
Because no explicit license is stated, it must be kept as a provenance/reference
document and must not be described as MIT- or Apache-licensed. The MCAT Tutor v2
wiki compiler implements the architecture in project-owned code.
