# Phase 00 — Setup & Spikes

## 1. Objective & Research Traceability
- **Primary Goal:** Establish the development environment, package dependencies, lockfile, test runner configurations, and execute Spikes S-1 through S-5 to resolve technical uncertainties prior to production component authoring.
- **Traceability:**
  - Guides: §1 (Corrections 1–3, 5, 10), §2 (Technology Baseline), §4 (Environment Setup), §6.1, §6.3, §7.3, §10, §16.3 (Items 3–6), §16.4.
  - Decisions: D1 (Model & Parameters), D2 (Python `pytest-playwright` only), D3 (4 Statuses), D5 (Cache key with `run_id`).
  - NFRs: NFR-02 (Reproducibility & Model Pinning), NFR-03 (Bounded Cyclic Graph).

## 2. Entry Gate
- [x] Python 3.11+ installed (`python --version` returns 3.11.9).
- [x] Node.js 20.9+ installed (`node --version` returns v22.14.0).
- [x] Docker Desktop installed, running, and verified (`docker ps` exits 0).
- [x] Git repository initialized and remote origin set (`origin` -> `https://github.com/Woofy2001/reqverify.git`).
- [x] Research brief verified (`planning/00_research_brief.md`).

## 3. Inputs & Dependencies
- `pyproject.toml`
- `.env.example`
- `.gitignore`
- Python standard libraries (`venv`, `subprocess`, `ast`, `sqlite3`, `hashlib`)

## 4. Deliverables
- `pyproject.toml` (standard packaging with pinned dependency ranges)
- `requirements.lock` (reproducible dependency tree)
- `.env.example` (template with `ANTHROPIC_API_KEY`, `REQVERIFY_MODEL`)
- `tests/conftest.py` (pytest markers: `live` vs default unit/integration)
- `tests/spikes/test_spike_s1_parse_effort.py` (Spike S-1)
- `tests/spikes/test_spike_s2_aria_snapshot.py` (Spike S-2)
- `tests/spikes/test_spike_s3_langgraph_loop.py` (Spike S-3)
- `tests/spikes/test_spike_s4_fail_vs_error.py` (Spike S-4)
- `tests/spikes/test_spike_s5_cache_replicates.py` (Spike S-5)
- `docs/decision-log.md` (decision log scaffolding)
- `docs/appendix_L_genai_log.md` (GenAI audit log scaffolding)

## 5. context7 Lookups
- `context7:/anthropics/anthropic-sdk-python`: Re-verify `client.messages.parse(output_format=Model)` signature and compatibility with `output_config`.
- `context7:/websites/reference_langchain_python_langgraph`: Re-verify `SqliteSaver` import from `langgraph.checkpoint.sqlite`.
- `context7:/microsoft/playwright-python`: Re-verify `page.aria_snapshot()` return structure and `pytest-playwright` default fixtures.

## 6. Step-by-Step Tasks

### Step 0.1: Initialize Python Virtual Environment & Install Base Toolchain
- **Goal:** Create isolated virtual environment `.venv` and install locked baseline dependencies.
- **Skill to invoke:** `using-git-worktrees` (or branch isolation).
- **Test file written FIRST:** `tests/test_toolchain.py`
  - `test_python_version()`: Asserts Python $\ge 3.11$.
  - `test_package_imports()`: Imports `anthropic`, `langgraph`, `playwright`, `pydantic`, `pytest`.
- **Implementation Spec:**
  - Create `pyproject.toml` per guide §2.1.
  - Install dependencies: `anthropic>=1.0,<2`, `langgraph>=1.2,<2`, `langgraph-checkpoint-sqlite`, `playwright>=1.59,<2`, `pydantic>=2.13,<3`, `pytest`, `pytest-playwright`, `fastapi`, `uvicorn`, `jinja2`, `pyyaml`, `pypdf`, `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`.
  - Install Playwright browser: `playwright install chromium`.
  - Freeze lockfile: `pip freeze > requirements.lock`.
- **Verification Command (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  pip install -e .
  playwright install chromium
  pytest tests/test_toolchain.py -v
  ```

### Step 0.2: Configure Pytest Markers & Governance Logs
- **Goal:** Set up pytest marker `@pytest.mark.live` and initialize audit logs.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_markers.py`
  - `test_default_test_skips_live()`: Verifies `pytest -m "not live"` excludes tests marked with `live`.
- **Implementation Spec:**
  - Create `pytest.ini` with:
    ```ini
    [pytest]
    markers =
        live: tests requiring active ANTHROPIC_API_KEY balance
    ```
  - Scaffold `docs/decision-log.md` with template table (`Date`, `Decision ID`, `Rationale`, `Evidence`).
  - Scaffold `docs/appendix_L_genai_log.md` following guide §15.
- **Verification Command:**
  ```powershell
  pytest -m "not live"
  ```

### Step 0.3: Spike S-1 — Structured Outputs & Effort Validation
- **Goal:** Empirically verify `client.messages.parse(output_format=Model)` behavior with Sonnet 5.5.
- **Skill to invoke:** `systematic-debugging` (if SDK syntax variance occurs).
- **Test file written FIRST:** `tests/spikes/test_spike_s1_parse_effort.py`
  - `test_spike_s1_schema_parse()`: Tests whether `client.messages.parse` accepts Pydantic v2 model.
  - `test_spike_s1_effort_param()`: Evaluates if `output_config={"effort": "medium"}` can be passed directly or via `messages.create()` fallback.
- **Implementation Spec:**
  - Guide §6.1 & §16.3 Item 5.
  - Document whether `parse()` or `create()` with `model_validate_json` is the standard for `LLMClient`.
- **Verification Command:**
  ```powershell
  pytest tests/spikes/test_spike_s1_parse_effort.py -v -m live
  ```

### Step 0.4: Spike S-2 — Playwright `aria_snapshot()` Parser Probe
- **Goal:** Capture 3 real YAML-like `aria_snapshot()` outputs and verify line parser robustness.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/spikes/test_spike_s2_aria_snapshot.py`
  - `test_spike_s2_real_snapshot_parsing()`: Parses 3 saved real `aria_snapshot()` fixtures into role and accessible name tuples.
  - `test_spike_s2_tolerant_regex()`: Validates whitespace, quotation variations, and nested hierarchy handling.
- **Implementation Spec:**
  - Guide §9 (Agent 2) & §16.4.
  - Save 3 snapshot fixtures to `tests/fixtures/snapshots/`.
- **Verification Command:**
  ```powershell
  pytest tests/spikes/test_spike_s2_aria_snapshot.py -v
  ```

### Step 0.5: Spike S-3 — LangGraph Cycle & Termination Guarantee
- **Goal:** Prove that a conditional cyclic graph terminates deterministically in $\le 3$ iterations.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/spikes/test_spike_s3_langgraph_loop.py`
  - `test_spike_s3_forced_reject_terminates_at_3()`: Enforces a mock critic that returns `REJECT` and verifies the graph halts at `not_converged` on iteration 3.
  - `test_spike_s3_approve_terminates_immediately()`: Verifies graph halts at `approved` when critic returns `APPROVE`.
- **Implementation Spec:**
  - Guide §10 `build_agent3()` starter code.
  - Validate that `recursion_limit=25` is not exceeded.
- **Verification Command:**
  ```powershell
  pytest tests/spikes/test_spike_s3_langgraph_loop.py -v
  ```

### Step 0.6: Spike S-4 — `FAIL` vs `ERROR` Pytest Outcome Classification
- **Goal:** Prove that Playwright `expect()` failures raise `AssertionError` (`FAIL`) while selector/timeout errors raise `TimeoutError` (`ERROR`).
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/spikes/test_spike_s4_fail_vs_error.py`
  - `test_spike_s4_assertion_failure_classified()`: Hand-written test expecting `AssertionError`.
  - `test_spike_s4_timeout_failure_classified()`: Hand-written test expecting Playwright `TimeoutError`.
  - `test_spike_s4_pass_classified()`: Hand-written test passing assertion.
- **Implementation Spec:**
  - Guide §7.3 status semantics & §16.4.
  - Write custom `pytest_runtest_makereport` hook to export exception type in test report JSON.
- **Verification Command:**
  ```powershell
  pytest tests/spikes/test_spike_s4_fail_vs_error.py -v
  ```

### Step 0.7: Spike S-5 — SQLite Cache Keying & `run_id` Isolation
- **Goal:** Verify cache hit on identical `run_id` and cache bypass on distinct `run_id`.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/spikes/test_spike_s5_cache_replicates.py`
  - `test_spike_s5_cache_hit_same_run_id()`: Verifies identical request returns stored response without network call.
  - `test_spike_s5_cache_miss_distinct_run_id()`: Verifies different `run_id` creates distinct row.
- **Implementation Spec:**
  - Guide §6.3 `_key()` hashing and `run_id` logic (Invariant D5).
- **Verification Command:**
  ```powershell
  pytest tests/spikes/test_spike_s5_cache_replicates.py -v
  ```

## 7. Test Suite for this Phase

| Test File | What it Proves | Mode |
|---|---|---|
| `tests/test_toolchain.py` | Python 3.11+ and dependency imports are operational | Offline Unit |
| `tests/test_markers.py` | Pytest markers cleanly isolate live API tests | Offline Unit |
| `tests/spikes/test_spike_s1_parse_effort.py` | Anthropic `client.messages.parse` & effort configuration | Live Smoke |
| `tests/spikes/test_spike_s2_aria_snapshot.py` | Robust parsing of real Playwright ARIA snapshots | Offline Fixture |
| `tests/spikes/test_spike_s3_langgraph_loop.py` | Deterministic cycle exit $\le 3$ super-steps (NFR-03) | Offline Unit |
| `tests/spikes/test_spike_s4_fail_vs_error.py` | Correct classification of `AssertionError` vs `TimeoutError` | Offline Fixture |
| `tests/spikes/test_spike_s5_cache_replicates.py` | Cache replay vs replicate isolation via `run_id` | Offline SQLite |

## 8. Exit Gate
- [ ] `pytest -m "not live"` passes 100% (green).
- [ ] Spike S-1 live test passes if `ANTHROPIC_API_KEY` is provided.
- [ ] `requirements.lock` generated and checked in.
- [ ] Code review completed (`requesting-code-review`).
- [ ] Phase 00 entry recorded in `docs/decision-log.md`.

## 9. Pitfalls & Risks
- **Pitfall:** `pip install` without constraints leading to LangGraph or Pydantic version churn.
  - *Mitigation:* Pin `langgraph>=1.2,<2`, `pydantic>=2.13,<3`.
- **Pitfall:** `output_config.effort` unsupported in helper method.
  - *Mitigation:* Spike S-1 determines whether to use `messages.create` + `model_validate_json`.

## 10. Unverified Items (⚠️) Resolved in this Phase
- §16.3 Item 4: `langgraph-checkpoint-sqlite` package name and import path verified.
- §16.3 Item 5: `messages.parse` combination with `output_config.effort` verified.
- §16.3 Item 6: Python 3.11.9 and Node v22.14.0 verified operational.

## 11. Handoff to Next Phase
- Delivers operational `LLMClient` prototype and cache database schema to **Phase 01 (LLM Layer)**.
