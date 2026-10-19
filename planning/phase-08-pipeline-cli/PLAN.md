# Phase 08 — Pipeline CLI & End-to-End Integration

## 1. Objective & Research Traceability
- **Primary Goal:** Construct the unified ReqVerify parent LangGraph pipeline integrating all four agents, bind execution state to a persistent SQLite checkpointer (`thread_id=f"{run_id}:{condition_id}"`), enforce runtime token and cost budget guards, implement the production CLI interface (`reqverify run`), generate complete run manifests, and validate the complete pipeline end-to-end against the clean TechStore SUT.
- **Traceability:**
  - Guides: §1 (Correction 8: Parent graph architecture), §3 (Decision D1: Claude Sonnet 3.5; Decision D5: `run_id` audit trace; Decision D8: Subgraph per condition; Decision D9: Token budget guard), §6 (LLM layer & caching), §10 (LangGraph wiring), §13 (Execution commands).
  - Blueprints: Section 4 (System Architecture & Pipeline Flow).
  - NFRs: NFR-01 (End-to-End Autonomy), NFR-06 (Auditable Run Manifests), NFR-08 (Resource and Budget Safety).
  - RQs: RQ4 (Clean-app baseline verification, 0 false alarms on clean SUT).

## 2. Entry Gate
- [ ] Phase 04 (Agent 1), Phase 05 (Agent 2), Phase 06 (Agent 3), Phase 07 (Agent 4) fully implemented and passing unit suites.
- [ ] Phase 02 (TechStore clean SUT) operational.
- [ ] SQLite checkpointer dependency (`langgraph-checkpoint-sqlite`) verified in Spike S-5.

## 3. Inputs & Dependencies
- `requirements.md` (e.g., `eval/ground_truth/requirements.md`)
- Target web application URL (`http://localhost:3000`)
- `langgraph` and `langgraph-checkpoint-sqlite`
- `click` (CLI framework)
- `src/reqverify/` components from previous phases

## 4. Deliverables
- `src/reqverify/cli/main.py` (`reqverify` CLI with `run`, `inspect`, and `version` commands)
- `src/reqverify/graph/parent_graph.py` (Parent LangGraph linking Agent 1 $\to$ Agent 2 $\to$ Agent 3 per-condition loop $\to$ Agent 4)
- `src/reqverify/checkpointer/sqlite_store.py` (`SqliteSaver` setup managing `thread_id=f"{run_id}:{condition_id}"`)
- `src/reqverify/orchestrator/pipeline.py` (`ReqVerifyPipeline`: orchestrator coordinating budget guard, execution, and manifest generation)
- `src/reqverify/schemas/manifest.py` (Pydantic model for `RunManifest`)
- `tests/test_cli.py` (Unit tests testing CLI commands, options, and error handling)
- `tests/test_budget_guard.py` (Unit tests verifying pipeline aborts gracefully when token threshold breached)
- `tests/test_parent_graph_replay.py` (Integration test executing the full graph offline using `FakeLLMClient`)
- `tests/test_e2e_clean_techstore_live.py` (`@pytest.mark.live` full end-to-end run against live clean TechStore)

## 5. context7 Lookups
- `context7:/langchain-ai/langgraph`:
  - `langgraph.checkpoint.sqlite.SqliteSaver` initialization and context manager usage.
  - Subgraph invocation inside parent nodes with thread configuration: `{"configurable": {"thread_id": ...}}`.
- `context7:/pallets/click`:
  - Subcommand design, progress bars, and exit code conventions.

## 6. Step-by-Step Tasks

### Step 8.1: SQLite Checkpointer & Run Manifest Engine
- **Goal:** Implement persistent state saving for crash resilience and auditable `manifest.json` generation capturing all run parameters.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_sqlite_checkpointer.py`
  - `test_checkpointer_saves_and_resumes_state()`: Verifies condition state is persisted to SQLite and reloaded upon resumption.
  - `test_manifest_schema_validation()`: Validates that `manifest.json` records git commit, model ID, effort level, requirements document SHA-256, token usage, and latency.
- **Implementation Spec:**
  - `src/reqverify/checkpointer/sqlite_store.py`:
    ```python
    from langgraph.checkpoint.sqlite import SqliteSaver

    def get_checkpointer(db_path: str = "checkpoints.db") -> SqliteSaver:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return SqliteSaver(conn)
    ```
  - `src/reqverify/schemas/manifest.py`: Captures complete environment provenance.
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_sqlite_checkpointer.py -v
  ```

### Step 8.2: Parent LangGraph Architecture (Invariant D8)
- **Goal:** Build the overarching parent graph that coordinates the four agents cleanly without exceeding recursion limits.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_parent_graph_replay.py`
  - `test_parent_graph_node_transitions()`: Verifies execution flow: `ingest` $\to$ `explore` $\to$ `verify_conditions` $\to$ `report`.
  - `test_untested_conditions_bypass_agent3()`: Verifies conditions with `ui_observable=False` skip Agent 3 and directly receive `UNTESTED` status in Agent 4.
- **Implementation Spec:**
  - `src/reqverify/graph/parent_graph.py`:
    ```python
    class PipelineState(TypedDict):
        run_id: str
        requirements_path: str
        app_url: str
        coverage_matrix: dict
        selector_map: dict
        verification_results: list[dict]
        manifest: dict

    def verify_conditions_node(state: PipelineState) -> dict:
        agent3 = build_agent3()
        results = []
        for cond in state["coverage_matrix"]["conditions"]:
            if not cond.get("ui_observable", True):
                results.append({"condition_id": cond["condition_id"], "status": "UNTESTED", "untested_reason": "not_ui_observable"})
                continue
            config = {"configurable": {"thread_id": f"{state['run_id']}:{cond['condition_id']}"}, "recursion_limit": 25}
            res = agent3.invoke({"condition": cond, "selectors": state["selector_map"]}, config)
            results.append(res)
        return {"verification_results": results}
    ```
- **Verification Command:**
  ```powershell
  pytest tests/test_parent_graph_replay.py -v
  ```

### Step 8.3: Token Budget Guard
- **Goal:** Implement an interceptor tracking token usage across all agents and aborting execution cleanly if the run exceeds a configurable token threshold.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_budget_guard.py`
  - `test_budget_guard_permits_under_budget()`: Allows normal operations while token count < limit.
  - `test_budget_guard_raises_on_breach()`: Raises `TokenBudgetExceededError` when total tokens breach limit.
- **Implementation Spec:**
  - `src/reqverify/orchestrator/pipeline.py`:
    - Intercepts before calling `LLMClient`.
    - Cumulative counter in `LLMClient` checked on each request.
- **Verification Command:**
  ```powershell
  pytest tests/test_budget_guard.py -v
  ```

### Step 8.4: Production CLI Interface
- **Goal:** Implement the Click-based command-line interface `reqverify run` with flags for requirements file, target URL, output directory, and budget limits.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_cli.py`
  - `test_cli_help()`: Asserts CLI returns exit code 0 and usage documentation.
  - `test_cli_missing_args()`: Asserts exit code 2 when required `--requirements` or `--url` is omitted.
  - `test_cli_dry_run_offline()`: Runs pipeline with `--dry-run` or offline fixtures.
- **Implementation Spec:**
  - `src/reqverify/cli/main.py`:
    ```python
    @click.group()
    def cli():
        """ReqVerify: Multi-Agent Requirements Verification Framework."""
        pass

    @cli.command()
    @click.option("--requirements", "-r", required=True, type=click.Path(exists=True), help="Path to requirements doc.")
    @click.option("--url", "-u", required=True, help="Base URL of target application.")
    @click.option("--output", "-o", default="reports", help="Output directory for reports and traces.")
    @click.option("--max-tokens", default=100000, type=int, help="Token budget safety limit.")
    def run(requirements, url, output, max_tokens):
        """Execute requirements verification pipeline."""
        ...
    ```
- **Verification Command:**
  ```powershell
  pytest tests/test_cli.py -v
  ```

### Step 8.5: End-to-End Clean TechStore Verification (Gate)
- **Goal:** Run the full integrated pipeline on the clean TechStore SUT and assert 0 false alarms.
- **Skill to invoke:** `verification-before-completion`.
- **Test file written FIRST:** `tests/test_e2e_clean_techstore_live.py`
  - `test_full_pipeline_clean_techstore()`: Executes `reqverify run` against clean TechStore. Asserts:
    - 23 UI-observable conditions receive `PASS`.
    - 1 backend-only condition (REQ-09) receives `UNTESTED` (`not_ui_observable`).
    - 0 conditions receive `FAIL` (0 false alarms on clean app).
    - `results.json` and `report.html` are generated with valid data.
- **Verification Command:**
  ```powershell
  pytest tests/test_e2e_clean_techstore_live.py -v -m live
  ```

## 7. Test Suite for this Phase

### Offline Replay Suite
```powershell
pytest tests/test_sqlite_checkpointer.py tests/test_parent_graph_replay.py tests/test_budget_guard.py tests/test_cli.py -v
```

### Live End-to-End Gate
```powershell
pytest tests/test_e2e_clean_techstore_live.py -v -m live
```

## 8. Exit Gate
- [ ] SQLite checkpointer persists state per condition thread and allows seamless restart.
- [ ] Token budget guard stops execution cleanly before unexpected API costs occur.
- [ ] CLI runs smoothly and parses all command-line options.
- [ ] Clean TechStore run produces 0 false alarms across all UI-observable conditions.
- [ ] JSON and HTML reports are written with valid hashes and Playwright trace links.
- [ ] All tests pass 100%.
