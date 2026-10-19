# Phase 07 — Agent 4: Verification & Reports

## 1. Objective & Research Traceability
- **Primary Goal:** Implement Agent 4 (Verification & Reports) to synthesize telemetry from the pipeline into auditable verdicts across the 4 canonical statuses (`PASS`, `FAIL`, `ERROR`, `UNTESTED`), compute calibrated `overall_confidence` using a frozen deterministic formula (Invariant D12), and generate both machine-readable JSON reports and high-craft, accessible HTML audit reports containing direct links to Playwright trace archives (`.zip`), screenshots, and rationale explanations.
- **Traceability:**
  - Guides: §1 (Corrections 3, 4, 10: Status semantics, confidence formula, trace links), §3 (Decision D3: 4 statuses; Decision D5: `run_id` audit traceability; Decision D12: Frozen analysis plan), §7.1, §7.3, §12 (Agent 4 specification).
  - Blueprints: Section 3.4 (Explainability & Audit Reporting).
  - NFRs: NFR-07 (Explainability & Audit Trail), NFR-08 (Zero-leakage report generation).
  - RQs: RQ2 (Confidence calibration: ECE, Brier score, AUROC), RQ4 (End-to-end verification accuracy).

## 2. Entry Gate
- [ ] Phase 06 (Agent 3 Generator & Critic subgraph) outputting approved scripts and `ProbeResult` telemetry.
- [ ] Phase 04 (Agent 1) conditions and Phase 05 (Agent 2) `SelectorMap` available.
- [ ] Spike S-4 (Status classification verification) completed in Phase 00.

## 3. Inputs & Dependencies
- `CondState` results for all conditions in a run
- `jinja2` (template engine)
- `src/reqverify/schemas/contracts.py`
- Playwright trace artifacts stored in `traces/{run_id}/`

## 4. Deliverables
- `src/reqverify/schemas/reports.py` (Pydantic models: `VerificationSummary`, `RequirementVerificationResult`, `ReportManifest`)
- `src/reqverify/reports/status_mapper.py` (`derive_status`: programmatic mapping implementing Guide §7.3)
- `src/reqverify/reports/confidence.py` (`compute_overall_confidence`: frozen mathematical formula)
- `src/reqverify/reports/json_reporter.py` (JSON output serializer complying with data contracts)
- `src/reqverify/reports/html_reporter.py` (Jinja2 HTML report generator)
- `src/reqverify/reports/templates/report.html.jinja2` (Accessible, modern report template)
- `tests/test_status_mapper.py` (Unit tests verifying §7.3 status derivation rules)
- `tests/test_confidence.py` (Unit tests validating confidence formula bounds and properties)
- `tests/test_reporters.py` (Unit tests validating JSON and HTML report outputs)
- `tests/test_agent4_visual_smoke.py` (Playwright automated smoke test verifying HTML report layout, links, and accessibility)

## 5. context7 Lookups
- `context7:/pallets/jinja`:
  - `jinja2.Environment`, template loading, custom filters for formatting confidence percentages and status chips.
- `context7:/playwright/playwright`:
  - Validating trace viewer URL links: `https://trace.playwright.dev/?trace=...`.

## 6. Step-by-Step Tasks

### Step 7.1: Status Mapping Engine (Guide §7.3)
- **Goal:** Implement the deterministic status derivation engine mapping probe outcomes, critic decisions, and exploration findings to one of the 4 canonical statuses.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_status_mapper.py`
  - `test_pass_derivation()`: Probe `passed` + Critic `APPROVE` $\to$ `PASS`.
  - `test_fail_derivation()`: Probe `assertion_failed` (`AssertionError`) + Critic `APPROVE` $\to$ `FAIL`.
  - `test_error_derivation_timeout()`: Probe `runtime_error` or `timeout` $\to$ `ERROR`.
  - `test_untested_not_ui_observable()`: Condition flagged `ui_observable=False` (e.g., REQ-09) $\to$ `UNTESTED` (`untested_reason="not_ui_observable"`).
  - `test_untested_no_selector()`: Agent 2 returns `no_selector_found` $\to$ `UNTESTED` (`untested_reason="no_selector_found"`).
  - `test_untested_critic_not_converged()`: Subgraph terminates with `not_converged` $\to$ `UNTESTED` (`untested_reason="critic_not_converged"`, `needs_human_review=True`).
- **Implementation Spec:**
  - `src/reqverify/reports/status_mapper.py`: Enforce strict table in Guide §7.3 without ambiguity.
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_status_mapper.py -v
  ```

### Step 7.2: Frozen Confidence Formula (Invariant D12)
- **Goal:** Implement the mathematical confidence engine combining component scores into a calibrated `overall_confidence` score $\in [0.0, 1.0]$.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_confidence.py`
  - `test_confidence_bounds()`: Asserts $0.0 \le \text{confidence} \le 1.0$ across edge cases.
  - `test_critic_iteration_penalty()`: Confidence decreases monotonically with increasing critic iterations.
  - `test_untested_confidence_zero()`: `UNTESTED` conditions receive confidence $0.0$.
- **Implementation Spec:**
  - `src/reqverify/reports/confidence.py`:
    $$\text{overall\_confidence} = \begin{cases} 0.0 & \text{if status is UNTESTED} \\ \min\left(1.0, c_{extraction} \cdot c_{locator} \cdot c_{critic}\right) & \text{otherwise} \end{cases}$$
    Where:
    - $c_{extraction} = 0.95$ (verbatim span match) or $0.70$ (fuzzy match).
    - $c_{locator} = 1.0$ (unique exact role+name), $0.85$ (parent-scoped), $0.70$ (.nth index).
    - $c_{critic} = 1.0$ (iteration 1 approval), $0.85$ (iteration 2), $0.70$ (iteration 3).
- **Verification Command:**
  ```powershell
  pytest tests/test_confidence.py -v
  ```

### Step 7.3: JSON Report Generator
- **Goal:** Serialize the verification summary into a standardized, machine-readable JSON format for evaluation scripts and research metrics.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_json_reporter.py`
  - `test_json_schema_compliance()`: Validates JSON against `VerificationSummary` Pydantic model.
  - `test_json_contains_all_conditions()`: Asserts all 24 conditions are present in output.
- **Implementation Spec:**
  - `src/reqverify/reports/json_reporter.py`: Outputs `reports/{run_id}/results.json` containing run metadata, timings, token expenditure, and individual condition verdicts.
- **Verification Command:**
  ```powershell
  pytest tests/test_json_reporter.py -v
  ```

### Step 7.4: HTML Audit Report Generator (Jinja2)
- **Goal:** Render a high-craft, accessible HTML report displaying the complete verification matrix, status badges, confidence bars, rationale explanations, and links to Playwright trace files.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_html_reporter.py`
  - `test_html_renders_without_errors()`: Asserts Jinja2 renders valid HTML string.
  - `test_html_contains_trace_links()`: Asserts presence of clickable links to `.zip` traces and screenshots.
  - `test_html_highlights_untested_needs_human_review()`: Highlights `needs_human_review=True` conditions in amber.
- **Implementation Spec:**
  - `src/reqverify/reports/templates/report.html.jinja2`:
    - Responsive layout with dark slate background, warm typography, and WCAG AA contrast.
    - Verification summary table with sorting/filtering by status (`PASS`, `FAIL`, `ERROR`, `UNTESTED`).
    - Accordion details per condition showing generated test script, probe exception, critic commentary, and audit trail.
- **Verification Command:**
  ```powershell
  pytest tests/test_html_reporter.py -v
  ```

### Step 7.5: Visual & Accessibility Smoke Test (Playwright MCP)
- **Goal:** Verify the rendered HTML report in a real browser using Playwright to confirm responsive layout, working accordion toggles, trace download links, and WCAG AA accessibility compliance.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_agent4_visual_smoke.py`
  - `test_report_opens_in_browser()`: Launches headless browser, navigates to `file://.../reports/test_run/report.html`, asserts page title and summary cards.
  - `test_accordion_expansion()`: Clicks condition row and asserts test script and trace links become visible.
- **Verification Command:**
  ```powershell
  pytest tests/test_agent4_visual_smoke.py -v
  ```

## 7. Test Suite for this Phase

### Offline Replay Suite
```powershell
pytest tests/test_status_mapper.py tests/test_confidence.py tests/test_json_reporter.py tests/test_html_reporter.py -v
```

### Visual Verification Suite (Playwright)
```powershell
pytest tests/test_agent4_visual_smoke.py -v
```

## 8. Exit Gate
- [ ] Status mapping engine strictly satisfies §7.3 definitions across all combinations.
- [ ] Confidence formula is deterministic, strictly bounded in $[0.0, 1.0]$, and penalizes repair loops.
- [ ] JSON report serializes all required telemetry without loss.
- [ ] HTML report renders cleanly with working trace links and zero accessibility violations.
- [ ] All tests pass 100%.
