# Phase 06 — Agent 3: Test Generator & Critic

## 1. Objective & Research Traceability
- **Primary Goal:** Implement Agent 3 as an isolated LangGraph subgraph pairing a Test Generator and a Test Critic. The Generator produces self-contained Python `pytest-playwright` scripts for each extracted condition using locators exclusively from the `SelectorMap`. The Critic evaluates probe execution results to distinguish application defects from test bugs, orchestrating up to 3 repair iterations. Crucially, asserted expectations remain strictly immutable across all iterations (Invariant D7) to prevent prompt degradation or false passes.
- **Traceability:**
  - Guides: §1 (Correction 7: Subgraph loop, iteration cap), §3 (Decision D7: Immutable assertions; Decision D8: One subgraph per condition), §10 (LangGraph wiring), §11 (Agent 3 specification).
  - Blueprints: Section 3.3 (Generator & Critic iterative convergence).
  - NFRs: NFR-03 (Strict loop bound), NFR-04 (AST script validation), NFR-05 (Subprocess probe sandboxing).
  - RQs: RQ3 (Critic ablation: first-pass vs final-pass accuracy, reduction in spurious errors).

## 2. Entry Gate
- [ ] Phase 01 (`LLMClient` with structured parsing and SQLite cache) operational.
- [ ] Phase 04 (Agent 1: extracted `ExtractedCondition` objects with valid hashes) operational.
- [ ] Phase 05 (Agent 2: `SelectorMap` with verified role-and-accessible-name locators) operational.
- [ ] Spike S-4 (Playwright `AssertionError` vs `TimeoutError` classification hook) verified in Phase 00.

## 3. Inputs & Dependencies
- `ExtractedCondition` (from Agent 1)
- `SelectorMap` (from Agent 2)
- Target application running URL (`http://localhost:3000`)
- `pytest-playwright` and Playwright browser binaries
- `langgraph` ($\ge 0.2.70$)

## 4. Deliverables
- `src/reqverify/schemas/probes.py` (Pydantic v2 schemas: `ProbeResult`, `CriticVerdict`, `ScriptSafetyViolation`)
- `src/reqverify/safety/ast_validator.py` (`validate_script_ast`: AST inspection blocking forbidden imports and builtins)
- `src/reqverify/plugins/probe_reporter.py` (Custom `pytest` plugin hook writing JSON test execution telemetry)
- `src/reqverify/agents/generator.py` (`TestGenerator`: prompt engineering with immutable assertions)
- `src/reqverify/agents/prober.py` (`TestProber`: subprocess execution, timeout guard, Playwright trace collector)
- `src/reqverify/agents/critic.py` (`TestCritic`: structured critic prompts enforcing defect vs test-bug dichotomy)
- `src/reqverify/graph/agent3_subgraph.py` (StateGraph wiring `generate` $\to$ `probe` $\to$ `critic` $\to$ `route`)
- `tests/test_ast_validator.py` (Unit tests verifying rejection of unsafe Python constructs)
- `tests/test_probe_reporter.py` (Unit tests verifying JSON telemetry and exception classification)
- `tests/test_agent3_assertion_immutability.py` (Unit tests ensuring assertions are not modified during repairs)
- `tests/test_agent3_subgraph.py` (Unit tests testing iteration bounding and convergence using `FakeLLMClient`)
- `tests/test_agent3_live_smoke.py` (`@pytest.mark.live` smoke test running one full Generator-Critic cycle on live TechStore)

## 5. context7 Lookups
- `context7:/langchain-ai/langgraph`:
  - `StateGraph(CondState)` initialization, `add_node`, `add_edge`, `add_conditional_edges`.
  - Managing subgraph state and iteration recursion limits (`recursion_limit=25`).
- `context7:/pytest-dev/pytest`:
  - `pytest_runtest_makereport` hook implementation and exception serialization.

## 6. Step-by-Step Tasks

### Step 6.1: AST Safety Validator
- **Goal:** Implement an AST visitor inspecting LLM-generated test code before execution, rejecting any scripts attempting forbidden imports, filesystem access, system commands, or dynamic code evaluation.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_ast_validator.py`
  - `test_valid_playwright_script_passes()`: Accepts standard `pytest-playwright` code using `page.goto()`, `expect(page.get_by_role(...))`.
  - `test_forbidden_imports_rejected()`: Rejects `import os`, `import sys`, `import subprocess`, `import socket`, `import requests`, `import urllib`.
  - `test_eval_exec_rejected()`: Rejects calls to `eval()`, `exec()`, `__import__()`.
  - `test_file_io_rejected()`: Rejects `open()`, `pathlib.Path.write_text()`.
- **Implementation Spec:**
  - `src/reqverify/safety/ast_validator.py`:
    - Parse with `ast.parse(script_text)`.
    - Walk AST nodes: `ast.Import`, `ast.ImportFrom`, `ast.Call`.
    - Whitelist permitted imports: `pytest`, `re`, `playwright.sync_api`, `playwright.async_api`.
    - Raise `ScriptSafetyViolation` if violations are found.
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_ast_validator.py -v
  ```

### Step 6.2: Pytest Telemetry Plugin & Subprocess Prober
- **Goal:** Implement a lightweight pytest plugin (`pytest_runtest_makereport`) that outputs structured JSON telemetry, and a subprocess runner (`TestProber`) that executes the probe under strict timeouts and gathers Playwright trace archives.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_probe_reporter.py`
  - `test_plugin_classifies_assertion_error()`: Asserts failed `expect(...)` outputs outcome `assertion_failed` and exception type `AssertionError`.
  - `test_plugin_classifies_timeout_error()`: Asserts locator timeout outputs outcome `runtime_error` and exception type `TimeoutError`.
  - `test_prober_timeout_guard()`: Subprocess killed cleanly if runtime exceeds 60 seconds, returning outcome `timeout`.
  - `test_prober_saves_playwright_trace()`: Verifies `.zip` trace archive is saved in `traces/{run_id}/{condition_id}/`.
- **Implementation Spec:**
  - `src/reqverify/plugins/probe_reporter.py`:
    ```python
    import json, pytest

    def pytest_runtest_makereport(item, call):
        if call.when == "call":
            rep = {
                "outcome": "passed" if not call.excinfo else (
                    "assertion_failed" if call.excinfo.typename == "AssertionError" else "runtime_error"
                ),
                "exception_type": call.excinfo.typename if call.excinfo else None,
                "message": str(call.excinfo.value) if call.excinfo else None,
                "duration": call.duration,
            }
            with open("probe_result.json", "w") as f:
                json.dump(rep, f)
    ```
  - `src/reqverify/agents/prober.py`: Runs `pytest -p reqverify.plugins.probe_reporter probe_test.py` via `subprocess.run(timeout=60)`.
- **Verification Command:**
  ```powershell
  pytest tests/test_probe_reporter.py -v
  ```

### Step 6.3: Test Generator with Assertion Immutability (Invariant D7)
- **Goal:** Implement `TestGenerator` generating pytest scripts where the assertion check is locked to the requirement's `predicate_text`, and verify that subsequent repair iterations cannot alter this assertion.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_agent3_assertion_immutability.py`
  - `test_initial_generation_includes_condition_docstring()`: Docstring includes `condition_id`.
  - `test_assertion_statement_remains_invariant_across_refinements()`: Verifies that even when given a critic refinement suggestion, the generated AST assertion node is structurally identical to the initial iteration.
- **Implementation Spec:**
  - `src/reqverify/agents/generator.py`:
    - Prompt extracts exact assertion constraint from `ExtractedCondition.predicate_text`.
    - Stores `canonical_assertion_code` during iteration 1.
    - On iteration > 1, the prompt enforces: *"You may only repair locators, waits, and navigation actions. You MUST NOT modify or loosen the following assertion: {canonical_assertion_code}."*
    - Programmatic check in code: compare AST of assertion statement between iterations; reject and revert if modified.
- **Verification Command:**
  ```powershell
  pytest tests/test_agent3_assertion_immutability.py -v
  ```

### Step 6.4: Test Critic & Subgraph StateGraph (Invariant D8)
- **Goal:** Implement `TestCritic` and compile the LangGraph `CondState` subgraph, executing the `generate` $\to$ `probe` $\to$ `critic` $\to$ `route` cycle with an explicit 3-iteration cap.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_agent3_subgraph.py`
  - `test_subgraph_approves_on_first_pass()`: Single pass exits with status `approved` in 1 iteration.
  - `test_subgraph_repairs_test_bug()`: Locator error triggers repair in iteration 2 and terminates `approved`.
  - `test_subgraph_stops_at_max_iterations()`: Forced rejections terminate at iteration 3 with status `not_converged`.
  - `test_critic_distinguishes_app_defect_from_test_bug()`: If probe fails with `AssertionError` and valid locators, critic sets `is_test_bug=False` and APPROVES verdict as legitimate defect detection.
- **Implementation Spec:**
  - Follow Guide §10 specification verbatim.
  - Subgraph `CondState`: `condition`, `selectors`, `script`, `probe`, `critic`, `iteration`, `final`.
  - Router:
    ```python
    def route(state: CondState) -> Literal["generate", "approved", "not_converged"]:
        if state["critic"]["verdict"] == "APPROVE":
            return "approved"
        if state["iteration"] >= 3:
            return "not_converged"
        return "generate"
    ```
- **Verification Command:**
  ```powershell
  pytest tests/test_agent3_subgraph.py -v
  ```

## 7. Test Suite for this Phase

### Offline Replay Suite
Fast unit tests using `FakeLLMClient` and mock probe execution:
```powershell
pytest tests/test_ast_validator.py tests/test_probe_reporter.py tests/test_agent3_assertion_immutability.py tests/test_agent3_subgraph.py -v
```

### Live Smoke Test
Executes one condition against running TechStore with live Claude API:
```powershell
pytest tests/test_agent3_live_smoke.py -v -m live
```

## 8. Exit Gate
- [ ] AST validator rejects all dangerous imports (`os`, `subprocess`, etc.) and builtins.
- [ ] Pytest telemetry plugin accurately classifies `AssertionError` (defect) vs `TimeoutError` (runtime error).
- [ ] Assertion immutability invariant (D7) is programmatically enforced across iterations.
- [ ] Agent 3 LangGraph subgraph caps iterations at exactly 3 and returns `not_converged` when unresolvable.
- [ ] All offline tests pass 100%.
- [ ] Live smoke test runs a full generator-critic loop on a clean TechStore condition and terminates with approval.
