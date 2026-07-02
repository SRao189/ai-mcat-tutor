# Impeccable Integration

Record of the Impeccable dependency vendored for the UI/learner-experience
redesign. This is a design-guidance skill for AI coding agents (Claude Code,
Codex CLI, etc.) — it is a dev-tooling dependency for the agents building the
UI, not a runtime/production dependency of the app itself.

## What Impeccable actually is

Not a UI component library or asset pack. It ships as `/impeccable` — a slash
command (23 subcommands: `craft`, `critique`, `audit`, `polish`, `harden`,
`onboard`, etc.) plus 45 deterministic anti-pattern detector rules, installed
into an AI coding tool's own skill/config directory (`.claude/`, `.codex/`,
etc.). It gives the agent a shared design vocabulary and a set of checks to
run against generated frontend code — it does not supply components to import
into `app/`.

## Record

- **Upstream URL:** https://github.com/pbakaus/impeccable.git
- **Pinned commit:** `44c27a72af98394c32691ba79358811bff86bde6` (tag `skill-v3.9.1`, 2026-07-01)
- **Vendored as:** git submodule at `.impeccable` (see `.gitmodules`)
- **License:** Apache License 2.0 (`.impeccable/LICENSE`). No `NOTICE` file in
  upstream, so no additional attribution text is required beyond the standard
  Apache 2.0 obligation to preserve copyright/license/attribution notices in
  redistributed copies of the licensed source (satisfied automatically — the
  submodule carries its own `LICENSE` file verbatim).
- **Files/workflows adopted:** the skill itself (`skill/`), its CLI engine
  (`cli/engine/*.mjs` — deterministic anti-pattern detectors), and the
  provider-linking workflow (`cli/bin/cli.js link`). The marketing site
  (`site/`, `functions/`, `wrangler.toml`, `astro.config.mjs`), browser
  extension, demos, and screenshot/release tooling are **not** used — only
  the skill + CLI portions relevant to agent-assisted design work.
- **Attribution requirement:** none beyond LICENSE preservation (Apache 2.0,
  no NOTICE file, no trademark/attribution clause encountered).

## Activation status: NOT YET LINKED

The submodule is vendored and pinned, but the skill is **not yet installed**
into `.claude/` or `.codex/`. That requires running Impeccable's own `link`
CLI command, which either:

1. Fetches `impeccable` from the npm registry (`npx impeccable link ...`), or
2. Builds the CLI/skill dist directly from this vendored submodule
   (`node scripts/build.js --skip-root-sync` inside `.impeccable/`, using only
   the pinned commit's own source — no npm registry substitution).

Path 1 was rejected in this session: the latest npm-published version
(`3.2.0`) does not match the pinned commit's version (`skill-v3.9.1`), which
is exactly the kind of unverified-source substitution this integration was
told to avoid. Path 2 requires the `archiver` devDependency, and this
environment's npm registry access was too slow/unreliable (TLS interception
issue, `UNABLE_TO_VERIFY_LEAF_SIGNATURE`, and 6+ minute hangs on a single
package install) to complete it in this session.

**To finish activation** once npm access is reliable, from the repo root:

```bash
cd .impeccable
npm install archiver@^8.0.0 --no-save   # only dep build:skills needs beyond prod deps
node scripts/build.js --skip-root-sync   # builds dist/universal/<provider>/...
cd ..
node .impeccable/cli/bin/cli.js link --source=.impeccable --providers=claude,codex
git add .claude .codex
```

Codex will prompt to approve the installed project hook on its next run
(`/hooks`) — this was pre-approved by the user for this integration.

## Constraint carried forward

Per the redesign directive: Impeccable must inform/improve the real
production UI (via `/impeccable` commands run during implementation), not
just sit copied into a vendor folder. Activation (above) is required before
that value is realized — this doc exists so the implementer (Codex) doesn't
have to re-derive the above from scratch.
