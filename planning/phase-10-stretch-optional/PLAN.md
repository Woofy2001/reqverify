# Phase 10 — Stretch Goals & Comparative Baselines (Optional)

## 1. Objective & Research Traceability
- **Primary Goal:** Investigate stretch research goals to strengthen the dissertation beyond standard requirements, specifically: (1) evaluating the feasibility and licensing of the WebTestPilot comparative baseline (Decision D10b); (2) conducting an empirical failure-mode study on accessibility degradation by evaluating ReqVerify against a deliberately degraded poor-ARIA SUT variant; and (3) analyzing the alignment between verbalized confidence scores and empirical cross-replicate consistency.
- **Traceability:**
  - Guides: §3 (Decision D10(b): WebTestPilot feasibility check), §8.1 (Controlled accessibility factor & poor-ARIA study), §11.1 (Confidence vs consistency across replicates), §16.4.
  - Blueprints: Section 5.3 (Comparative baseline & robustness extensions).
  - NFRs: NFR-02 (Resilient Selectors robustness boundaries).
  - RQs: RQ2 (Calibration extended to multi-sample consistency), RQ4 (Boundary condition exploration).

## 2. Entry Gate
- [ ] Phase 08 (Production pipeline) and Phase 09 (Core empirical evaluation harness and statistical figures) completed and verified.
- [ ] Core dissertation research questions (RQ1–RQ4) already answered with valid data.
- [ ] Explicit user confirmation to allocate additional tokens/compute for stretch studies.

## 3. Inputs & Dependencies
- Core ReqVerify pipeline (`src/reqverify/`)
- Running TechStore SUT and Docker environment
- `eval/ground_truth/conditions.csv`

## 4. Deliverables
- `eval/baselines/webtestpilot/` (License audit document, reproduction environment, or feasibility report)
- `techstore/variants/poor_aria/` (Code patches removing semantic ARIA roles and labels from select TechStore pages)
- `eval/experiments/poor_aria_study.py` (Benchmark script measuring pipeline degradation on poor-ARIA variant)
- `eval/experiments/confidence_consistency_study.py` (Script correlating verbalized confidence with cross-run verdict consistency)
- `docs/dissertation_notes/failure_modes_and_stretch.md` (Discussion notes for Chapter 5 / Chapter 6 of dissertation)
- `tests/test_poor_aria_study.py` (Unit tests verifying degradation handling and `no_selector_found` classification)

## 5. context7 Lookups
- `context7:/playwright/playwright`:
  - Inspecting ARIA snapshots on unlabelled and generic container elements (`div`, `span`).

## 6. Step-by-Step Tasks

### Step 10.1: WebTestPilot Baseline Feasibility & License Audit (Decision D10b)
- **Goal:** Investigate WebTestPilot open-source availability, repository licensing, dependency compatibility (Playwright/Python), and determine whether an automated head-to-head comparison is feasible.
- **Skill to invoke:** `test-driven-development`.
- **Implementation Spec:**
  - Review public WebTestPilot artifacts and licensing terms.
  - If reproducible within the project's Playwright/Node/Python stack without licensing conflicts: implement adapter in `eval/baselines/webtestpilot/adapter.py`.
  - If closed-source, unmaintained, or incompatible: document formal rationale in `eval/baselines/webtestpilot/feasibility_report.md` explaining why the Zero-Shot baseline serves as the primary comparative control.

### Step 10.2: Poor-ARIA Robustness & Failure Mode Study
- **Goal:** Construct a deliberately degraded variant of TechStore where semantic tags (`<button>`, `<input>`, `<nav>`) are replaced with unlabelled `<div>` and `<span>` elements with click handlers, and measure the graceful degradation of Agent 2 and Agent 3.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_poor_aria_study.py`
  - `test_poor_aria_produces_no_selector_found()`: Asserts that unlabelled clickable divs without accessible names correctly trigger `no_selector_found` rather than crashing.
  - `test_untested_status_assigned()`: Asserts condition gracefully classified as `UNTESTED` (`untested_reason="no_selector_found"`).
- **Implementation Spec:**
  - `techstore/variants/poor_aria/`:
    - Patch the Checkout page to strip ARIA attributes and labels.
    - Run ReqVerify against `http://localhost:3000/checkout` on the poor-ARIA variant.
    - Record drop in extraction/verification coverage and explain the failure modes in dissertation notes.
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_poor_aria_study.py -v
  ```

### Step 10.3: Verbalized Confidence vs Empirical Consistency Study
- **Goal:** Analyze whether conditions with high verbalized `overall_confidence` exhibit higher pass/fail agreement across 10 independent replicates than low-confidence conditions.
- **Skill to invoke:** `test-driven-development`.
- **Implementation Spec:**
  - `eval/experiments/confidence_consistency_study.py`:
    - Compute cross-run verdict entropy:
      $$H(C) = - \sum_{s \in \{\text{PASS}, \text{FAIL}\}} p(s) \log_2 p(s)$$
    - Correlate verbalized confidence with $1 - H(C)$ (predictability).
    - Generate scatter plot in `eval/charts/confidence_vs_entropy.png`.

## 7. Test Suite for this Phase

### Offline Unit Suite
```powershell
pytest tests/test_poor_aria_study.py -v
```

### Experiment Runner (Optional / Budget Permitting)
```powershell
python eval/experiments/poor_aria_study.py --dry-run
python eval/experiments/confidence_consistency_study.py --dry-run
```

## 8. Exit Gate
- [ ] Formal feasibility determination for WebTestPilot documented with license citations.
- [ ] Poor-ARIA study demonstrates graceful degradation to `UNTESTED` (`no_selector_found`) rather than pipeline crash.
- [ ] Failure mode analysis documented for inclusion in dissertation Chapter 5 / Discussion.
