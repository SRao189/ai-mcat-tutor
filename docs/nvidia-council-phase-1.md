# NVIDIA Council Phase 1

## Scope

This is the first narrow Council layer for the private MCAT platform:

`student question -> retrieve approved Chapter 7.1 passages -> rerank -> one tutor reasoner -> Gate 2 -> Gate 3-compatible support check -> verified answer or insufficient evidence`

It is not the full multi-agent Council. Phase 1 does not include a Chair, voting, parallel agent fan-out, ingestion of new textbooks, or deployment.

## Runtime Roles

- Retriever: deterministic keyword retrieval over approved Chapter 7.1 passages.
- Reranker: deterministic lexical fallback. It ranks evidence; it does not verify support.
- Tutor reasoner: one NVIDIA OpenAI-compatible chat completion when mock mode is off.
- Safety role: interface placeholder only.
- Chair role: interface placeholder only.

## Environment

The code reads only these configuration keys:

- `NVIDIA_API_KEY`
- `NVIDIA_BASE_URL`
- `NVIDIA_TUTOR_MODEL`
- `NVIDIA_EMBED_MODEL`
- `NVIDIA_RERANK_MODEL`
- `NVIDIA_SAFETY_MODEL`
- `NVIDIA_MOCK_MODE`

Secrets are not printed or logged. `.env`, `.env.*`, key files, token files, and secret folders are gitignored. `.env.example` contains placeholders only.

## Mock Mode

Use mock mode for tests and offline development:

```powershell
$env:NVIDIA_MOCK_MODE = "true"
python -m tests.test_nvidia_council_phase1
```

Mock mode makes zero NVIDIA API calls.

## Live Mode

Live mode requires:

```text
NVIDIA_API_KEY
NVIDIA_BASE_URL
NVIDIA_TUTOR_MODEL
```

The client uses:

- OpenAI-compatible `/chat/completions`
- 30 second timeout
- max 1 retry
- JSON response format request
- max 900 output tokens
- one live tutor model call per request

## Verification Policy

Gate 2:

- Every claim must cite an approved source ID.
- The source ID must resolve to the Chapter 7.1 passage store.
- The stored source hash must match the current passage text.

Gate 3-compatible check:

- Empty claims fail.
- Claims without citations fail.
- Unsupported numeric values fail.
- Unsupported units fail.
- Equation-like unsupported relationships fail.
- Directly supported claims pass.
- High-overlap lexical support can pass for non-numeric, non-equation claims.

Current caveat: this branch does not contain the full repaired Gate 3 implementation from the separate `agent/claude` worktree. Phase 1 therefore uses a conservative deterministic support checker and should be wired to the full Gate 3 module after it lands.

## Response Statuses

- `verified`: citation and support checks passed.
- `ambiguous`: relevant material was retrieved, but generated claims failed verification.
- `insufficient_evidence`: retrieval or tutor output did not support an answer.
- `model_error`: configuration, timeout, or model failure.

## Example Commands

Mock:

```powershell
$env:NVIDIA_MOCK_MODE = "true"
python scripts/run-nvidia-council.py "What are the pKas of phosphoric acid?"
```

Live:

```powershell
python scripts/run-nvidia-council.py "What are the pKas of phosphoric acid?"
```

## Security Controls

- No secret values in startup status.
- No full environment logging.
- No raw source file path in learner-facing passage labels.
- No raw textbook file mounted or served.
- No full Council fan-out.
- No automatic batch calls.
- Reranking is not treated as verification.
