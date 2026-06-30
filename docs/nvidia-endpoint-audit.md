# NVIDIA Endpoint Audit

## Status

Tests run in `NVIDIA_MOCK_MODE=true`.

One bounded live probe was attempted with the locally stored NVIDIA API key and candidate Phase 1 tutor configuration. The request failed safely before a model response was returned.

Live probe result:

- Request ID: `c0008c1db1444744890030f98fcb0ba4`
- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
- Tutor model candidate: `nvidia/nemotron-nano-9b-v2`
- Result status: `model_error`
- Observed error behavior: `SSLCertVerificationError`
- Verified answer returned: no
- Live model calls counted by the Council response: 1
- Secret exposure: none observed in command output

The active endpoint roster still must be audited against the actual NVIDIA Build account before production use.

## Required Audit Fields

For each configured endpoint, record:

- exact configured model ID
- provider
- endpoint URL
- availability in the account
- free-tier status
- rate limit
- context size
- input/output pricing
- timeout behavior
- streaming support
- structured-output support
- tested request ID
- observed latency
- observed error behavior

## Current Configuration Variables

The application reads these names only:

| Variable | Purpose | Tested live |
| --- | --- | --- |
| `NVIDIA_BASE_URL` | OpenAI-compatible base URL | no |
| `NVIDIA_TUTOR_MODEL` | Phase 1 live tutor reasoner | attempted; TLS verification failed before model response |
| `NVIDIA_EMBED_MODEL` | future embedding retriever | no |
| `NVIDIA_RERANK_MODEL` | future reranker | no |
| `NVIDIA_SAFETY_MODEL` | future safety role | no |

`NVIDIA_API_KEY` is required for live mode but must never be written in this document.

## Candidate Models

These are candidates only until verified in the account:

- Tutor: `nvidia/nemotron-nano-9b-v2` or another active Nemotron tutor model.
- Embedding: `nvidia/llama-nemotron-embed-1b-v2` or active NVIDIA embedding endpoint.
- Reranking: `nvidia/llama-nemotron-rerank-1b-v2` or active NVIDIA rerank endpoint.
- Safety: active NVIDIA safety endpoint.

## Live Test Procedure

1. Confirm `.env` exists locally and is ignored by Git.
2. Confirm startup status reports only missing/configured names, never values.
3. Run one harmless Chapter 7.1 question.
4. Record request ID, selected model, HTTP status, latency, and whether JSON output was returned.
5. Do not paste the API key, full raw prompt, or raw textbook corpus into logs.

Example:

```powershell
python scripts/run-nvidia-council.py "What are the pKas of phosphoric acid?"
```

## Blockers Before Production

- Verify exact active NVIDIA model IDs and quotas.
- Resolve local TLS certificate verification for NVIDIA API calls.
- Decide whether the existing local `.env` should be copied manually into this worktree or exported into the shell environment.
- Merge or port the repaired full Gate 3 implementation so Phase 1 can call the same production claim-support authority.
