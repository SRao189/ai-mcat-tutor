# NVIDIA Endpoint Audit

## Status

Tests run in `NVIDIA_MOCK_MODE=true`.

Bounded live probes were attempted with the locally stored NVIDIA API key and candidate Phase 1 tutor configuration. The requests failed safely before a model response was returned.

Initial live probe result:

- Request ID: `c0008c1db1444744890030f98fcb0ba4`
- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
- Tutor model candidate: `nvidia/nemotron-nano-9b-v2`
- Result status: `model_error`
- Observed error behavior: `SSLCertVerificationError`
- Verified answer returned: no
- Live model calls counted by the Council response: 1
- Secret exposure: none observed in command output

Follow-up debug results:

- TLS verification was fixed locally by using Python `truststore`.
- `GET /models` returns `200` and 121 model IDs, but it also returns `200` without an API key; treat it as catalog discovery, not proof of authentication.
- Chat completions for active model IDs returned `401`.
- Sanitized provider body for one chat probe: `{"status":401,"title":"Unauthorized","detail":"Authentication failed"}`
- Conclusion: the invoke credential is not accepted by `POST /chat/completions`. The model roster can be loaded from the catalog, but live tutor generation is blocked until a valid NVIDIA Build invoke key/account scope is supplied.

The active endpoint roster still must be audited with a working invoke credential before production use.

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
| `NVIDIA_TUTOR_MODEL` | Phase 1 live tutor reasoner | active in catalog; chat invoke returned 401 with current key |
| `NVIDIA_EMBED_MODEL` | future embedding retriever | active in catalog; not invoked |
| `NVIDIA_RERANK_MODEL` | future reranker | no active rerank model found in catalog filter |
| `NVIDIA_SAFETY_MODEL` | future safety role | active in catalog; not invoked |

`NVIDIA_API_KEY` is required for live mode but must never be written in this document.

## Candidate Models

Catalog-visible candidates as of the latest local audit:

- Tutor: `nvidia/nvidia-nemotron-nano-9b-v2`, `nvidia/nemotron-3-nano-30b-a3b`, `nvidia/llama-3.1-nemotron-nano-8b-v1`, `nvidia/nemotron-mini-4b-instruct`
- Embedding: `nvidia/llama-nemotron-embed-1b-v2`
- Reranking: no active rerank endpoint found in the local catalog filter; keep deterministic rerank fallback for now.
- Safety: `nvidia/nemotron-content-safety-reasoning-4b`
- PII: `nvidia/gliner-pii`

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
- Supply a NVIDIA Build API key/account scope accepted by `POST /chat/completions`.
- Decide whether the existing local `.env` should be copied manually into this worktree or exported into the shell environment.
- Merge or port the repaired full Gate 3 implementation so Phase 1 can call the same production claim-support authority.
