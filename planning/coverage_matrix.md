# ReqVerify: Traceability & Coverage Matrix

This matrix provides 100% bidirectional traceability between the authoritative requirements in `implementation-guide.md` (and blueprint PDF), the locked technical decisions (D1–D13), spikes (S-1–S-5), research questions (RQ1–RQ4), mutants (M01–M10), and the executable phase plans.

---

## 1. Guide Sections Traceability (§1 – §16)

| Guide Section | Description / Core Requirement | Target Phase | Implementation Task(s) |
|---|---|---|---|
| **§1 Item 1** | Use model ID `claude-sonnet-5-5`, never pass disallowed sampling params | `phase-01` | Step 1.1, Step 1.2 |
| **§1 Item 2** | `page.aria_snapshot()` replaces removed `page.accessibility` | `phase-00`, `phase-05` | Step 0.4 (Spike S-3), Step 5.2 |
| **§1 Item 3** | Exactly 4 statuses (`PASS`, `FAIL`, `ERROR`, `UNTESTED`) | `phase-07` | Step 7.1 (`status_mapper.py`) |
| **§1 Item 4** | Frozen `overall_confidence` mathematical formula | `phase-07`, `phase-09` | Step 7.2 (`confidence.py`), Step 9.1 |
| **§1 Item 5** | Deterministic SHA-256 condition IDs in code | `phase-04` | Step 4.1 (`make_condition_id`) |
| **§1 Item 6** | Prompt rationale discipline: "one-sentence justification" | `phase-01`, `phase-04`, `phase-06` | Prompt templates across agents |
| **§1 Item 7** | Subgraph for Generator-Critic loop with max 3 iterations | `phase-06` | Step 6.4 (`agent3_subgraph.py`) |
| **§1 Item 8** | Parent LangGraph architecture connecting all 4 agents | `phase-08` | Step 8.2 (`parent_graph.py`) |
| **§1 Item 9** | RQ metrics: ECE, Brier score, AUROC, bootstrap over conditions | `phase-09` | Step 9.2 (`metrics.py`), Step 9.3 (`stats.py`) |
| **§1 Item 10** | Trace links to Playwright `.zip` archives and snapshots in HTML report | `phase-07` | Step 7.4 (`report.html.jinja2`) |
| **§1 Item 11** | Zero-shot baseline implementation for comparative evaluation | `phase-09` | Step 9.4 (`zero_shot.py`) |
| **§1 Item 12** | Primary protocol P-B (separate Docker container per mutant) | `phase-03`, `phase-09` | Step 3.3, Step 9.5 (`run_eval.py`) |
| **§1 Item 13** | Prompts tuned strictly on `dev_app`, never on TechStore eval set | `phase-02`, `phase-04` | Step 2.4 (`dev_app`), Step 4.4 |
| **§2** | Senior Lecturer Defense Guide: viva objections and empirical answers | `planning/00_research_brief.md`, `phase-09` | Section 4 of brief, analysis plan |
| **§3** | Locked Technical Decisions (D1 to D13) | All phases | Section 2 of this matrix |
| **§4** | Workspace and directory structure | `phase-00` | Step 0.2 (directory scaffolding) |
| **§5** | Environment and dependency verification | `phase-00` | Step 0.1, Step 0.2 (`pyproject.toml`) |
| **§6** | LLM Layer: `LLMClient`, parsing, SQLite cache, retries, budget | `phase-01` | Step 1.1, Step 1.2, Step 1.3, Step 1.4 |
| **§7.1** | Pydantic v2 data contracts | `phase-04` | Step 4.1 (`schemas/contracts.py`) |
| **§7.2** | Post-processing rules for Agent 1 | `phase-04` | Step 4.3 (`postprocessor.py`) |
| **§7.3** | Status derivation semantics table | `phase-07` | Step 7.1 (`status_mapper.py`) |
| **§8.1** | TechStore SUT (5 pages, seeded users, ARIA compliance) | `phase-02` | Step 2.1, Step 2.2, Step 2.3 |
| **§8.2** | Requirements document, conditions.csv, ground truth answer key | `phase-03` | Step 3.1 (`requirements.md`, `conditions.csv`) |
| **§8.3** | Mutants M01–M10, Docker builds, and environment switch | `phase-03` | Step 3.2, Step 3.3 |
| **§9** | Agent 1: Requirements Analyst specification | `phase-04` | Step 4.1, Step 4.2, Step 4.3 |
| **§10** | Agent 2: App Explorer specification | `phase-05` | Step 5.1, Step 5.2, Step 5.3, Step 5.4 |
| **§11** | Agent 3: Test Generator + Critic specification | `phase-06` | Step 6.1, Step 6.2, Step 6.3, Step 6.4 |
| **§12** | Agent 4: Execution & Verification specification | `phase-07` | Step 7.1, Step 7.2, Step 7.3, Step 7.4 |
| **§13** | LangGraph wiring and execution CLI commands | `phase-08` | Step 8.2, Step 8.4 (`reqverify run`) |
| **§14** | Empirical evaluation methodology & run design | `phase-09` | Step 9.1, Step 9.5 (`run_eval.py`) |
| **§15** | Academic dissertation alignment, decision log, Appendix L | `phase-00`, `phase-09` | Step 0.5 (`docs/decision-log.md`), Step 9.6 |
| **§16.1** | Phase-00 setup tasks and spikes S-1 to S-5 | `phase-00` | Steps 0.1 to 0.5 |
| **§16.2** | Immediate week-by-week implementation sequence | `master_plan.md` | Section 3 |
| **§16.3** | Resolution of 4 blocking library warnings (checkpointer, etc.) | `phase-00` | Step 0.1, Step 0.4, Step 0.5 |
| **§16.4** | Stretch goals (WebTestPilot, poor-ARIA page study) | `phase-10` | Step 10.1, Step 10.2, Step 10.3 |

---

## 2. Locked Technical Decisions Traceability (D1 – D13)

| Decision ID | Summary of Decision | Primary Phase | Verification Task |
|---|---|---|---|
| **D1** | Claude Sonnet 3.5 (`claude-sonnet-5-5`), strict parameter discipline | `phase-01` | `test_client_parameters_rejection()` |
| **D2** | Playwright Python only, `page.aria_snapshot()`, role+name locators | `phase-05` | `test_parse_real_techstore_snapshots()` |
| **D3** | Exactly 4 statuses (`PASS`, `FAIL`, `ERROR`, `UNTESTED`) | `phase-07` | `test_status_mapper.py` |
| **D4** | Deterministic SHA-256 condition IDs via `make_condition_id` | `phase-04` | `test_make_condition_id_determinism()` |
| **D5** | `run_id` audit trace identifying all logs, threads, reports, traces | `phase-01`, `phase-08` | `test_manifest_schema_validation()` |
| **D6** | Mutant registry unreachable by pipeline agents | `phase-03`, `phase-09` | `test_pipeline_isolation_from_mutants()` |
| **D7** | Assertions immutable across critic repair iterations | `phase-06` | `test_assertion_statement_remains_invariant()` |
| **D8** | Agent 3 isolated subgraph, max 3 iterations, recursion limit 25 | `phase-06` | `test_subgraph_stops_at_max_iterations()` |
| **D9** | Token budget and cost safety guard | `phase-01`, `phase-08` | `test_budget_guard_raises_on_breach()` |
| **D10(a)** | Zero-shot baseline implementation | `phase-09` | `test_zero_shot_output_conforms_to_schema()` |
| **D10(b)** | WebTestPilot feasibility audit (optional stretch) | `phase-10` | Step 10.1 feasibility report |
| **D11** | Protocol P-B primary (isolated containers), P-A secondary | `phase-09` | `test_eval_runner_handles_replicates()` |
| **D12** | Frozen analysis plan pre-registered before eval runs | `phase-09` | Step 9.1 (`eval/analysis_plan.md`) |
| **D13** | Prompts tuned strictly on `dev_app` development set | `phase-02`, `phase-04` | `test_dev_set_extraction_recall()` |

---

## 3. Spikes Traceability (S-1 – S-5)

| Spike ID | Subject | Phase | Deliverable / Verification File |
|---|---|---|---|
| **S-1** | Claude API structured parsing with Pydantic v2 | `phase-00` | `tests/spikes/test_spike_s1_structured_output.py` |
| **S-2** | SQLite prompt caching with `run_id` | `phase-00` | `tests/spikes/test_spike_s2_sqlite_cache.py` |
| **S-3** | `page.aria_snapshot()` formatting & parser spike | `phase-00` | `tests/spikes/test_spike_s3_aria_snapshot.py` |
| **S-4** | `AssertionError` vs `TimeoutError` pytest report plugin | `phase-00` | `tests/spikes/test_spike_s4_pytest_plugin.py` |
| **S-5** | LangGraph SQLite checkpointer integration | `phase-00` | `tests/spikes/test_spike_s5_langgraph_sqlite.py` |

---

## 4. Mutants Traceability (M01 – M10)

| Mutant ID | Targeted Flow & Bug Description | Expected Verdict | Phase Tested |
|---|---|---|---|
| **M01** | Login: Incorrect credentials accepted as valid login | `FAIL` (Security breach) | `phase-03`, `phase-09` |
| **M02** | Product Filtering: Price filter excludes items below threshold | `FAIL` (Filter defect) | `phase-03`, `phase-09` |
| **M03** | Cart: Quantity increment button decrements count | `FAIL` (State defect) | `phase-03`, `phase-09` |
| **M04** | Discount: Valid coupon returns "Invalid code" error | `FAIL` (Discount defect) | `phase-03`, `phase-09` |
| **M05** | Discount: Expired coupon code successfully applies discount | `FAIL` (Logic defect) | `phase-03`, `phase-09` |
| **M06** | Checkout: Shipping address validation omitted on empty submit | `FAIL` (Validation defect) | `phase-03`, `phase-09` |
| **M07** | Checkout: Multi-step step indicator shows step 1 on step 3 | `FAIL` (UI state defect) | `phase-03`, `phase-09` |
| **M08** | Checkout: Total charge excludes calculated shipping fee | `FAIL` (Calculation defect)| `phase-03`, `phase-09` |
| **M09** | Admin: Non-admin user permitted to access `/admin/orders` | `FAIL` (Access control) | `phase-03`, `phase-09` |
| **M10** | Admin: Order status toggle does not persist update in DB | `FAIL` (Persistence defect)| `phase-03`, `phase-09` |

---

## 5. Research Questions (RQ1 – RQ4)

| Research Question | Metric(s) & Success Criteria | Primary Plan | Statistical Validation |
|---|---|---|---|
| **RQ1: Extraction Quality** | Precision, Recall, F1 against ground truth. **Target:** Recall $\ge 0.80$. | `phase-04` | Bootstrap 95% CIs across conditions (`phase-09`) |
| **RQ2: Confidence Calibration** | ECE ($5\text{--}10$ bins), Brier Score, AUROC, Reliability Curves. | `phase-07` | Analytical ECE calculation, bin counts (`phase-09`) |
| **RQ3: Critic Repair Ablation** | First-pass vs final-pass pass rate, reduction in spurious errors. | `phase-06` | Paired Wilcoxon signed-rank test across conditions (`phase-09`) |
| **RQ4: End-to-End Fault Detection** | Fault-detection recall (mutants detected / 10), Clean-app false alarms = 0. | `phase-08` | Primary protocol P-B container runs (`phase-09`) |

---

## 6. Coverage Verification Summary
- Total Guide Sections (§1 – §16) Mapped: **16 of 16 (100%)**
- Total Locked Decisions (D1 – D13) Mapped: **13 of 13 (100%)**
- Total Spikes (S-1 – S-5) Mapped: **5 of 5 (100%)**
- Total Mutants (M01 – M10) Mapped: **10 of 10 (100%)**
- Total Research Questions (RQ1 – RQ4) Mapped: **4 of 4 (100%)**
- **Unmapped Items: 0**
