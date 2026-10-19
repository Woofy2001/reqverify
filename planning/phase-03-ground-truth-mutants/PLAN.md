# Phase 03 — Ground Truth, Seeded Mutants & Containerization

## 1. Objective & Research Traceability
- **Primary Goal:** Formalize the evaluation ground truth (`requirements.md`, `conditions.csv`, `mutants_expected.csv`), author the 10 seeded defect mutants (`M01`–`M10`), implement the runtime `MUTANT=` environment switch, package all 11 variants as hardened Docker containers, and ensure the mutant registry is strictly isolated from pipeline discovery (Invariant D6).
- **Traceability:**
  - Guides: §3 (Decisions D6, D9), §8.2, §8.3, §13 (Risk R-02).
  - RQs: Foundation for RQ1 (Extraction Recall), RQ2 (Calibration), RQ3 (Ablation), and RQ4 (Fault Detection Recall).

## 2. Entry Gate
- [ ] Phase 02 clean TechStore passes all E2E verification tests.
- [ ] Docker engine active and authenticated with local daemon.

## 3. Inputs & Dependencies
- `techstore/` source code from Phase 02
- Ground truth specifications schema (Guide §8.2)
- Docker Desktop with Buildx plugin

## 4. Deliverables
- `eval/ground_truth/requirements.md` (15–20 functional requirements, with backend-only REQ-09)
- `eval/ground_truth/conditions.csv` (~24 atomic conditions, source spans, testability flags)
- `eval/ground_truth/mutants_expected.csv` (Answer key: condition × mutant expected verdicts)
- `techstore/mutants/registry.yaml` (Defect catalog: M01–M10 descriptions & flags)
- `techstore/Dockerfile` & `techstore/docker-compose.yml` (Parameterized container builds)
- `techstore/src/lib/mutants.ts` (Runtime defect injection switch driven by `process.env.MUTANT`)
- `tests/eval/test_oracle_mutants.py` (Oracle test suite verifying each mutant triggers its exact defect)
- `tests/eval/test_registry_isolation.py` (Asserts registry is inaccessible from pipeline)

## 5. context7 Lookups
- `context7:/websites/reference_langchain_python_langgraph`: Security best practices for isolated sandboxes.

## 6. Step-by-Step Tasks

### Step 3.1: Author Ground Truth Requirements & Decomposed Conditions
- **Goal:** Draft the comprehensive evaluation requirements document and ground truth answer key before any agent execution.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/eval/test_ground_truth_integrity.py`
  - `test_requirements_id_format()`: Verifies all requirements match `REQ-\d{2}`.
  - `test_source_spans_exist_in_document()`: Verifies 100% of `source_span` values in `conditions.csv` are exact verbatim substrings of `requirements.md`.
  - `test_untested_ground_truth_case()`: Proves `REQ-09` is designated with `ui_observable=False`.
- **Implementation Spec:**
  - Path: `eval/ground_truth/requirements.md` (15–20 requirements).
  - Path: `eval/ground_truth/conditions.csv` with columns: `req_id`, `condition_id`, `predicate`, `ui_observable`, `expected_clean`, `source_span`.
  - Path: `eval/ground_truth/mutants_expected.csv` with matrix of expected `PASS` / `FAIL` per variant.
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/eval/test_ground_truth_integrity.py -v
  ```
- **HUMAN-ONLY GATE:** Provide sample of `requirements.md` and `conditions.csv` to academic supervisor (**Mr. Asanjay Fernando**) for signed review to eliminate author-bias critique.

### Step 3.2: Implement 10 Seeded Defect Mutants in TechStore
- **Goal:** Implement clean, switchable defects in `techstore/` governed strictly by `process.env.MUTANT`.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/eval/test_oracle_mutants.py`
  - 10 targeted test cases (`test_mutant_m01_broken_email_regex`, ..., `test_mutant_m10_cart_not_cleared`).
  - Verifies that when `MUTANT=Mxx`, only the designated defect is activated while others remain clean.
- **Implementation Spec:**
  - Implement defects per Guide §8.3:
    - `M01` (Login email regex accepts `a@b`)
    - `M02` (Password min length skipped)
    - `M03` (Price filter `<` instead of $\le$)
    - `M04` (Stock badge missing for stock=0)
    - `M05` (Line total ignores quantity)
    - `M06` (Discount adds instead of subtracts)
    - `M07` (Step 2 checkout accepts empty address)
    - `M08` (Order total omits shipping cost)
    - `M09` (Admin shipped status update rejected)
    - `M10` (Cart persists after successful order)
  - Create `techstore/mutants/registry.yaml` containing metadata for evaluation grading only.
- **Verification Command:**
  ```powershell
  pytest tests/eval/test_oracle_mutants.py -v
  ```
- **Playwright MCP Action:** Launch browser against `MUTANT=M06` and visually confirm cart total increases when coupon is applied.

### Step 3.3: Docker Containerization & Image Tagging
- **Goal:** Build 11 immutable Docker image tags: `techstore:clean`, `techstore:m01`, ..., `techstore:m10`.
- **Skill to invoke:** `hardening-docker-containers-for-production`.
- **Test file written FIRST:** `tests/eval/test_docker_images.py`
  - `test_docker_containers_run_non_root()`: Confirms container user is `node` (non-root).
  - `test_docker_variant_spins_up()`: Boots each container and probes HTTP 200 on `/`.
- **Implementation Spec:**
  - Create multi-stage `techstore/Dockerfile` with pinned base `node:22.14-alpine`.
  - Build script `techstore/scripts/build_mutants.ps1` building tags `techstore:clean` and `techstore:m01`..`m10`.
- **Verification Command:**
  ```powershell
  pwsh techstore/scripts/build_mutants.ps1
  pytest tests/eval/test_docker_images.py -v
  ```

### Step 3.4: Enforce Black-Box Isolation (Invariant D6)
- **Goal:** Guarantee that the automated pipeline cannot inspect mutant definitions or cheat.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/eval/test_registry_isolation.py`
  - `test_registry_unreachable_by_pipeline()`: Asserts `registry.yaml` is not packaged in the SUT Docker image and not imported by any pipeline source file under `src/reqverify/`.
- **Implementation Spec:**
  - Exclude `techstore/mutants/registry.yaml` via `.dockerignore`.
  - Add AST/import scanning test ensuring no module in `src/reqverify/` imports from `techstore/mutants`.
- **Verification Command:**
  ```powershell
  pytest tests/eval/test_registry_isolation.py -v
  ```

## 7. Test Suite for this Phase

| Test File | What it Proves | Mode |
|---|---|---|
| `tests/eval/test_ground_truth_integrity.py` | 100% of condition source spans match verbatim text | Offline Unit |
| `tests/eval/test_oracle_mutants.py` | Each of the 10 mutants triggers its exact intended defect | Playwright E2E |
| `tests/eval/test_docker_images.py` | All 11 Docker image tags build and launch securely | Docker Local |
| `tests/eval/test_registry_isolation.py` | Pipeline has zero access to mutant answer key (D6) | Offline AST |

## 8. Exit Gate
- [ ] All ground-truth conditions verified against clean TechStore (100% PASS on observable conditions).
- [ ] All 10 mutant oracle tests pass.
- [ ] 11 Docker containers built and tagged locally.
- [ ] Supervisor review sample documented.
- [ ] Code review completed (`requesting-code-review`).
- [ ] Logged in `docs/decision-log.md`.

## 9. Pitfalls & Risks
- **Pitfall:** Mutant defect leaking into clean build.
  - *Mitigation:* Clean build explicitly sets `MUTANT=CLEAN` (or unset); oracle tests verify clean app never exhibits mutant flaws.
- **Pitfall:** Ground truth authoring bias.
  - *Mitigation:* Supervisor signed sign-off and pre-registered frozen protocol.

## 10. Unverified Items (⚠️) Resolved in this Phase
- §16.3 Item 3: Pinned Microsoft Playwright container tag and Node 22 Alpine verified.

## 11. Handoff to Next Phase
- Delivers ground truth datasets and verified SUT variants to **Phase 04 (Agent 1)** and **Phase 09 (Evaluation Harness)**.
