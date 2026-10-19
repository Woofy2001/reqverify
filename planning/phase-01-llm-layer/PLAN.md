# Phase 01 — LLM Layer & Deterministic Caching

## 1. Objective & Research Traceability
- **Primary Goal:** Implement the robust, production-grade `LLMClient` with SQLite request/response caching keyed by `run_id`, structured outputs parsing, token budget protection, transient error retries with exponential backoff, run manifest generation, and offline test fixture recording/playback.
- **Traceability:**
  - Guides: §1 (Corrections 1, 2, 5, 6), §3 (Decisions D1, D5), §6.1, §6.3, §6.4, §6.5, §13 (Risks R-01, R-07), §15.
  - NFRs: NFR-02 (Reproducibility & Model Pinning).

## 2. Entry Gate
- [ ] Phase 00 exit gate passed (`pytest -m "not live"` 100% green).
- [ ] Spike S-1 findings integrated into `LLMClient` calling convention.
- [ ] Spike S-5 SQLite schema verified.

## 3. Inputs & Dependencies
- `tests/spikes/test_spike_s1_parse_effort.py` findings
- SQLite3 standard library
- `anthropic` SDK v1.0+
- `pydantic>=2.13,<3`

## 4. Deliverables
- `src/reqverify/llm/client.py` (`LLMClient`, `CallMeta`, `RefusalError`, `TruncatedError`, `BudgetExceededError`)
- `src/reqverify/llm/manifest.py` (`RunManifest`, `write_manifest`)
- `src/reqverify/llm/fake_client.py` (Mock/Fixture client for zero-cost offline tests)
- `tests/test_llm_client.py` (Unit tests covering caching, budget, retries, parsing)
- `tests/test_manifest.py` (Unit tests verifying manifest schema completeness)

## 5. context7 Lookups
- `context7:/anthropics/anthropic-sdk-python`: Error classes (`APIError`, `RateLimitError`, `APIConnectionError`, `InternalServerError`), retry handler options.

## 6. Step-by-Step Tasks

### Step 1.1: Core `LLMClient` with Structured Parsing & SQLite Cache
- **Goal:** Implement `LLMClient.parse()` using Pydantic schema contracts and SQLite persistence.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_llm_client.py`
  - `test_cache_hit_identical_call()`: Proves second call returns cached response with `cache_hit=True`.
  - `test_cache_key_includes_run_id()`: Proves different `run_id` creates fresh row.
  - `test_refusal_raises_refusal_error()`: Asserts `stop_reason == "refusal"` raises `RefusalError`.
  - `test_truncation_raises_truncated_error()`: Asserts `stop_reason == "max_tokens"` raises `TruncatedError`.
- **Implementation Spec:**
  - Path: `src/reqverify/llm/client.py`.
  - Class: `LLMClient(db_path, model="claude-sonnet-5-5", run_id="dev", use_cache=True, max_tokens=16000, effort="high", max_budget_usd=10.0)`.
  - Cache table: `calls(key TEXT PRIMARY KEY, created REAL, run_id TEXT, request TEXT, response TEXT, meta TEXT)`.
  - Key hash: SHA-256 over `{"model": ..., "system": ..., "user": ..., "schema": schema.model_json_schema(), "run_id": ...}`.
  - Reject/strip `temperature`, `top_p`, `top_k`, or assistant prefill.
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_llm_client.py -k "test_cache or test_refusal" -v
  ```

### Step 1.2: Token Budget Guard & Exponential Backoff Retries
- **Goal:** Protect against runaway loops and API transient connection errors.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_llm_budget.py`
  - `test_budget_guard_trips()`: Verifies that cumulative spend exceeding `max_budget_usd` halts execution immediately.
  - `test_transient_error_retries_with_backoff()`: Verifies rate limit (429) and 5xx errors retry up to `max_retries=3`.
- **Implementation Spec:**
  - Token cost accounting per guide §6.5: Input \$2/MTok, Output \$10/MTok, Cache read \$0.10/MTok.
  - Track `cumulative_cost_usd` on `LLMClient` instance; raise `BudgetExceededError` before dispatch if budget exceeded.
- **Verification Command:**
  ```powershell
  pytest tests/test_llm_budget.py -v
  ```

### Step 1.3: Audit Run Manifest Writer
- **Goal:** Write immutable `runs/<run_id>/manifest.json` recording full experimental provenance.
- **Skill to invoke:** `testing-for-sensitive-data-exposure`.
- **Test file written FIRST:** `tests/test_manifest.py`
  - `test_manifest_schema_completeness()`: Validates that all fields specified in guide §6.4 are present.
  - `test_manifest_scrubs_api_keys()`: Verifies `ANTHROPIC_API_KEY` never appears in manifest.
- **Implementation Spec:**
  - Path: `src/reqverify/llm/manifest.py`.
  - Required fields: `run_id`, `model`, `effort`, `sdk_versions` (`anthropic`, `langgraph`, `playwright`, `pydantic`), `playwright_browser_build`, `reqverify_commit`, `sut_commit`, `mutant_id`, `document_sha256`, `response_ids`, `total_input_tokens`, `total_output_tokens`, `cost_estimate_usd`, `cache_hit_ratio`, `timestamp_iso`.
- **Verification Command:**
  ```powershell
  pytest tests/test_manifest.py -v
  ```

### Step 1.4: Fixture Recording & Fake Client for Offline Testing
- **Goal:** Enable deterministic zero-cost unit and integration testing across all agent phases.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_fake_client.py`
  - `test_fake_client_returns_recorded_fixture()`: Verifies schema validation and mock dispatch without external API.
- **Implementation Spec:**
  - Path: `src/reqverify/llm/fake_client.py`.
  - Provides `FakeLLMClient` pre-loaded with recorded responses or rule-based deterministic replies.
- **Verification Command:**
  ```powershell
  pytest tests/test_fake_client.py -v
  ```

## 7. Test Suite for this Phase

| Test File | What it Proves | Mode |
|---|---|---|
| `tests/test_llm_client.py` | Cache hit/miss, `run_id` isolation, schema parse, exception raising | Offline SQLite |
| `tests/test_llm_budget.py` | Token budget trip guard & exponential backoff | Offline Mock |
| `tests/test_manifest.py` | Manifest schema completeness & sensitive data exclusion | Offline Unit |
| `tests/test_fake_client.py` | Offline deterministic fixture replay capability | Offline Unit |
| `tests/test_llm_live_smoke.py` | Live Claude Sonnet 5.5 parse call returns valid object | Live Smoke (`live`) |

## 8. Exit Gate
- [ ] `pytest -m "not live"` 100% green.
- [ ] `pytest -m live` passes when `ANTHROPIC_API_KEY` is present.
- [ ] SQLite cache schema verified with index on `key`.
- [ ] Code review completed (`requesting-code-review`).
- [ ] Logged in `docs/decision-log.md`.

## 9. Pitfalls & Risks
- **Pitfall:** `Optional` field explosion violating Claude structured output limit ($\le 24$ optional params).
  - *Mitigation:* Keep schemas compact per guide §6.2.
- **Pitfall:** API key leaked into SQLite database `meta` column.
  - *Mitigation:* Explicit payload sanitizer before DB insert.

## 10. Unverified Items (⚠️) Resolved in this Phase
- §16.3 Item 7: Installed Anthropic SDK 1.x version recorded in manifest.

## 11. Handoff to Next Phase
- Delivers `LLMClient` and `FakeLLMClient` to **Phase 04 (Agent 1)** and **Phase 06 (Agent 3)**.
