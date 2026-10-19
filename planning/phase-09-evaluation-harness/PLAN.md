# Phase 09 — Evaluation Harness & Statistical Analysis

## 1. Objective & Research Traceability
- **Primary Goal:** Implement the rigorous empirical evaluation harness executing the frozen analysis plan (`eval/analysis_plan.md` per Invariant D12), running 5–10 independent replicates across clean and mutated SUT variants under Protocol P-B (separate Docker containers per mutant per Invariant D11), computing statistical metrics for RQ1–RQ4 (Precision/Recall/F1, ECE, Brier score, AUROC, fault-detection recall, false-alarm rate), running the zero-shot baseline, executing the critic ablation study, computing bootstrap 95% confidence intervals clustered over conditions, performing Wilcoxon signed-rank paired tests, and generating publication-ready calibration and comparison charts.
- **Traceability:**
  - Guides: §1 (Corrections 9, 11, 12: RQ metrics, bootstrap over conditions, P-B protocol), §3 (Decision D5: Replicates; Decision D6: Ground truth isolation; Decision D10(a): Zero-shot baseline; Decision D11: Protocol P-B; Decision D12: Frozen analysis plan), §11 (Evaluation protocol & statistics), §14, §15.
  - Blueprints: Section 5 (Empirical Evaluation Methodology & Statistical Framework).
  - NFRs: NFR-06 (Evaluation Provenance & Replicability), NFR-08 (Zero-leakage integrity).
  - RQs: RQ1 (Extraction quality), RQ2 (Confidence calibration), RQ3 (Critic ablation impact), RQ4 (Fault detection & false alarm rates).

## 2. Entry Gate
- [ ] Phase 03 (Ground truth `requirements.md`, `conditions.csv`, `mutants_expected.csv`, and Docker mutant images M01–M10) built and verified.
- [ ] Phase 08 (`reqverify` CLI and pipeline orchestrator) verified and passing end-to-end on clean TechStore.
- [ ] Frozen `eval/analysis_plan.md` drafted, reviewed, and committed to git **before** executing live evaluation runs (Invariant D12).

## 3. Inputs & Dependencies
- `techstore` Docker images (`techstore:clean`, `techstore:m01` ... `techstore:m10`)
- `eval/ground_truth/conditions.csv`
- `eval/ground_truth/mutants_expected.csv`
- Python scientific libraries: `numpy`, `scipy`, `scikit-learn`, `pandas`, `matplotlib`, `seaborn`
- `docker-py` or Docker CLI to start/stop containers

## 4. Deliverables
- `eval/analysis_plan.md` (Formal frozen pre-registration document: hypotheses, primary/secondary endpoints, statistical formulas, and protocol specifications)
- `eval/metrics.py` (Implementation of precision, recall, F1, ECE with bin counts, Brier score, AUROC, fault-detection recall)
- `eval/stats.py` (Clustered condition-level bootstrap 95% CIs, Wilcoxon signed-rank paired test)
- `eval/baselines/zero_shot.py` (Single-prompt zero-shot LLM verification baseline)
- `eval/run_eval.py` (Evaluation orchestrator managing Docker container lifecycle, replicate loops, and result logging)
- `eval/generate_charts.py` (Script generating publication-ready reliability diagrams, ROC curves, and ablation tables)
- `tests/test_eval_metrics.py` (Unit tests verifying metric calculations against synthetic test cases)
- `tests/test_eval_stats.py` (Unit tests verifying bootstrap sampling and Wilcoxon test correctness)
- `tests/test_zero_shot_baseline.py` (Unit tests verifying zero-shot baseline output schema)
- `tests/test_eval_run_dry_run.py` (Dry-run integration test verifying evaluation loop orchestration on mocked data)

## 5. context7 Lookups
- `context7:/scipy/scipy`:
  - `scipy.stats.bootstrap` with paired condition clusters.
  - `scipy.stats.wilcoxon` for paired non-parametric comparison.
- `context7:/scikit-learn/scikit-learn`:
  - `sklearn.metrics.roc_auc_score`, `sklearn.metrics.brier_score_loss`.

## 6. Step-by-Step Tasks

### Step 9.1: Author and Freeze the Analysis Plan (Invariant D12)
- **Goal:** Write `eval/analysis_plan.md` detailing every statistical test, metric formulation, matching protocol, and hypothesis before running benchmarks to uphold empirical research integrity.
- **Skill to invoke:** `test-driven-development`.
- **Implementation Spec:**
  - Define primary protocol: Protocol P-B (isolated Docker container per mutant).
  - Define matching protocol: condition ID matching via semantic/span mapping to ground truth `conditions.csv`.
  - Define statistical thresholds: $\alpha = 0.05$, bootstrap resamples $B = 2000$.
  - State explicit stopping rules and random seed policy.
  - Commit to git: `git add eval/analysis_plan.md; git commit -m "chore(eval): freeze analysis plan before benchmark execution (D12)"`.

### Step 9.2: Implement Mathematical Metrics Engine
- **Goal:** Author `eval/metrics.py` implementing calibration and classification metrics with zero ambiguity.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_eval_metrics.py`
  - `test_ece_perfect_calibration()`: Confidences matching empirical accuracy yield ECE = 0.0.
  - `test_ece_complete_miscalibration()`: Maximum confidence on incorrect predictions yields ECE $\to 1.0$.
  - `test_brier_score()`: Matches known mean squared error calculation.
  - `test_auroc_metric()`: Evaluates ranking quality of confidence scores.
  - `test_fault_detection_recall()`: Computes proportion of 10 mutants correctly identified with `FAIL` status.
- **Implementation Spec:**
  - `eval/metrics.py`:
    - ECE calculation per Guide §11.3:
      $$\text{ECE} = \sum_{b=1}^{B} \frac{|B_b|}{N} |\text{acc}(B_b) - \text{conf}(B_b)|$$
    - Uses 5–10 quantile or uniform bins, outputting per-bin sample counts.
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_eval_metrics.py -v
  ```

### Step 9.3: Statistical Testing & Bootstrap Engine
- **Goal:** Implement `eval/stats.py` computing bootstrap 95% confidence intervals clustered over conditions and Wilcoxon signed-rank paired tests for critic ablation (RQ3).
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_eval_stats.py`
  - `test_bootstrap_clustered_over_conditions()`: Verifies that resampling units are conditions (24 conditions), not independent rows, preserving within-condition replicate correlation.
  - `test_wilcoxon_paired_test()`: Verifies paired comparison of critic ON vs critic OFF pass rates across conditions.
- **Implementation Spec:**
  - `eval/stats.py`:
    - Resamples index of unique conditions with replacement.
    - Computes empirical 2.5th and 97.5th percentiles.
- **Verification Command:**
  ```powershell
  pytest tests/test_eval_stats.py -v
  ```

### Step 9.4: Zero-Shot Baseline Implementation (Decision D10a)
- **Goal:** Implement the zero-shot baseline script (`eval/baselines/zero_shot.py`) providing a single Claude Sonnet 3.5 prompt with the requirement and clean DOM snapshot to predict pass/fail without multi-agent exploration or code execution.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_zero_shot_baseline.py`
  - `test_zero_shot_output_conforms_to_schema()`: Validates that baseline produces matching `RequirementVerificationResult` entries.
- **Implementation Spec:**
  - `eval/baselines/zero_shot.py`: Simple prompt asking the model to infer if the requirement holds on the supplied DOM.
- **Verification Command:**
  ```powershell
  pytest tests/test_zero_shot_baseline.py -v
  ```

### Step 9.5: Evaluation Orchestrator (Protocol P-B)
- **Goal:** Implement `eval/run_eval.py` to automate running the 5–10 replicates on clean TechStore and mutants M01–M10 in isolated Docker containers, recording full JSON results.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_eval_run_dry_run.py`
  - `test_eval_runner_handles_replicates()`: Executes 2 replicates across clean + 2 mutants on mock pipeline, verifying output structure in `eval/results/`.
- **Implementation Spec:**
  - `eval/run_eval.py`:
    1. For each SUT variant (Clean, M01...M10):
       a. Spin up Docker container: `docker run -d -p 3000:3000 techstore:<variant>`.
       b. Wait for health check (`/api/health`).
       c. Execute ReqVerify for $N$ replicates, each with unique `run_id`.
       d. Stop container and remove.
    2. Run Zero-Shot baseline under identical conditions.
    3. Run Critic-OFF ablation (Generator without Critic repair loop).
    4. Save unified dataset to `eval/results/eval_dataset.json`.
- **Verification Command:**
  ```powershell
  pytest tests/test_eval_run_dry_run.py -v
  ```

### Step 9.6: Publication Chart & Table Generator
- **Goal:** Author `eval/generate_charts.py` to produce dissertation-ready figures:
  - Figure 1: Calibration curve / Reliability diagram (observed accuracy vs mean confidence with 10 bins).
  - Figure 2: AUROC curves comparing ReqVerify confidence vs baseline.
  - Figure 3: Fault detection matrix across M01–M10 mutants.
  - Figure 4: Critic ablation impact (first-pass vs final-pass pass rate).
- **Skill to invoke:** `verification-before-completion`.
- **Verification Command:**
  ```powershell
  python eval/generate_charts.py --dry-run
  ```

## 7. Test Suite for this Phase

### Offline Unit & Statistical Suite
```powershell
pytest tests/test_eval_metrics.py tests/test_eval_stats.py tests/test_zero_shot_baseline.py tests/test_eval_run_dry_run.py -v
```

### Dry-Run Chart Generation
```powershell
python eval/generate_charts.py --sample-data
```

## 8. Exit Gate
- [ ] `eval/analysis_plan.md` is frozen and committed to git before benchmarks execute.
- [ ] Statistical metrics (ECE, Brier, AUROC, P/R/F1) thoroughly tested on known analytical cases.
- [ ] Bootstrap sampling strictly clusters over conditions (not pooled observations).
- [ ] Protocol P-B container management runs cleanly without orphaned Docker containers.
- [ ] Zero-shot baseline and Critic-OFF ablation pipelines run without errors.
- [ ] All tests pass 100%.
