# Phase 04 — Agent 1: Requirements Analyst

## 1. Objective & Research Traceability
- **Primary Goal:** Implement Agent 1 (Requirements Analyst) to ingest requirements documents (Markdown or PDF), split them deterministically by requirement identifier (`REQ-\d{2}`), extract atomic testable conditions via Claude structured outputs, execute strict programmatic post-processing, generate deterministic condition IDs, and evaluate extraction precision/recall on the development set (Invariant D13).
- **Traceability:**
  - Guides: §1 (Corrections 5, 6), §3 (Decisions D4, D13), §7.1, §7.2, §9 (Agent 1 spec).
  - RQs: RQ1 (Extraction Recall $\ge$ 0.80, Precision, F1).
  - NFRs: NFR-06 (Deterministic Hashed Condition IDs).

## 2. Entry Gate
- [ ] Phase 01 (`LLMClient` & `FakeLLMClient`) verified and operational.
- [ ] Phase 02 development requirements (`dev_app/requirements.md`) available.

## 3. Inputs & Dependencies
- Requirements documents (`.md` or `.pdf` via `pypdf`)
- `src/reqverify/schemas/contracts.py` (Pydantic v2 schemas)
- `src/reqverify/llm/client.py`

## 4. Deliverables
- `src/reqverify/schemas/contracts.py` (Full Pydantic v2 data contracts per Guide §7.1)
- `src/reqverify/agents/analyst.py` (`RequirementsAnalystAgent`, `ingest_document`, `split_requirements`)
- `src/reqverify/agents/postprocessor.py` (Post-processing validation, normalization, hashing per Guide §7.2)
- `tests/test_agent1_analyst.py` (Unit tests with recorded fixtures)
- `tests/test_agent1_postprocessor.py` (Unit tests for span validation, deduplication, ID generation)
- `tests/test_agent1_dev_evaluation.py` (RQ1 extraction precision/recall baseline on dev set)

## 5. context7 Lookups
- `context7:/pydantic/pydantic`: Schema validation methods (`model_validate_json`, custom root validators).
- `context7:/anthropics/anthropic-sdk-python`: Structured parsing with Pydantic classes.

## 6. Step-by-Step Tasks

### Step 4.1: Implement Data Contracts & Deterministic ID Generator
- **Goal:** Author immutable Pydantic v2 schemas and the canonical `make_condition_id` helper.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_contracts.py`
  - `test_make_condition_id_determinism()`: Asserts identical input produces exact same 8-char SHA-256 hash.
  - `test_condition_schema_validation()`: Verifies `LLMCondition`, `ExtractedCondition`, and `CoverageMatrix` parse valid JSON.
  - `test_rationale_field_constraints()`: Verifies short NL justification accepted without refusal.
- **Implementation Spec:**
  - Follow Guide §7.1:
    ```python
    def normalize(s: str) -> str:
        return " ".join(s.lower().split())

    def make_condition_id(req_id: str, source_span: str, ordinal: int) -> str:
        h = hashlib.sha256(f"{req_id}|{normalize(source_span)}|{ordinal}".encode()).hexdigest()[:8]
        return f"{req_id}.{ordinal}-{h}"
    ```
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_contracts.py -v
  ```

### Step 4.2: Ingestion & Deterministic Requirement Splitting
- **Goal:** Ingest Markdown or PDF files and segment them into individual `REQ-xx` chunks.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_ingestion.py`
  - `test_markdown_splitter()`: Splits markdown on `## REQ-\d+` headings.
  - `test_pdf_ingestion_pypdf()`: Extracts text and SHA-256 hash from sample PDF.
- **Implementation Spec:**
  - Compute overall document SHA-256 hash to attach to `CoverageMatrix`.
  - Split text deterministically so each LLM call only processes a single requirement chunk (smaller context, higher cache hit rate).
- **Verification Command:**
  ```powershell
  pytest tests/test_ingestion.py -v
  ```

### Step 4.3: Extraction Prompt Engineering & Programmatic Post-Processing
- **Goal:** Dispatch single-requirement extraction calls and enforce the 4 post-processing rules in code.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_agent1_postprocessor.py`
  - `test_span_validation_rejects_hallucinations()`: Rejects condition if `source_span` is not a verbatim substring.
  - `test_duplicate_condition_dropping()`: Drops exact duplicate conditions and logs near-duplicates.
  - `test_metrics_tracking()`: Increments schema failure counters on malformed outputs.
- **Implementation Spec:**
  - Prompt: Instruct model to extract atomic, observable conditions with a single-sentence rationale (avoid "step-by-step reasoning" wording to prevent refusals per Guide §1 Item 6).
  - Code-side post-processing per Guide §7.2:
    1. Verify `normalize(source_span) in normalize(document_text)`.
    2. Assign IDs via `make_condition_id`.
    3. Filter exact duplicates.
- **Verification Command:**
  ```powershell
  pytest tests/test_agent1_postprocessor.py -v
  ```

### Step 4.4: Development Set Extraction Tuning (Invariant D13)
- **Goal:** Evaluate extraction precision, recall, and F1 on `dev_app/requirements.md` only.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_agent1_dev_evaluation.py`
  - `test_dev_set_extraction_recall()`: Asserts Recall $\ge 0.80$ against `dev_app` ground truth answer key.
- **Implementation Spec:**
  - Run Agent 1 over `dev_app/requirements.md`.
  - Assert zero evaluation requirement text is leaked or touched during this tuning pass.
- **Verification Command:**
  ```powershell
  pytest tests/test_agent1_dev_evaluation.py -v
  ```

## 7. Test Suite for this Phase

| Test File | What it Proves | Mode |
|---|---|---|
| `tests/test_contracts.py` | Pydantic v2 schemas and deterministic hashing helper | Offline Unit |
| `tests/test_ingestion.py` | Markdown and PDF ingestion with SHA-256 integrity | Offline Unit |
| `tests/test_agent1_postprocessor.py` | Verbatim span validation, ID generation, deduplication | Offline Fixture |
| `tests/test_agent1_dev_evaluation.py` | Extraction Recall $\ge 0.80$ on development requirements | Offline Fixture |
| `tests/test_agent1_live_smoke.py` | Agent 1 live extraction on 1 dev requirement | Live Smoke (`live`) |

## 8. Exit Gate
- [ ] 100% of extracted conditions on dev set have valid, verifiable `source_span` substrings.
- [ ] 100% schema validation pass rate.
- [ ] Extraction Recall on dev requirements $\ge 0.80$.
- [ ] Code review completed (`requesting-code-review`).
- [ ] Logged in `docs/decision-log.md`.

## 9. Pitfalls & Risks
- **Pitfall:** Model paraphrasing `source_span` instead of copying verbatim.
  - *Mitigation:* Rule 1 post-processor automatically rejects or flags non-substring spans.
- **Pitfall:** `reasoning_extraction` refusal trigger.
  - *Mitigation:* Rationale prompt wording asks strictly for "one short justification sentence".

## 10. Unverified Items (⚠️) Resolved in this Phase
- §7.2: Verification of whitespace normalization resilience during span matching.

## 11. Handoff to Next Phase
- Delivers validated `CoverageMatrix` data structure to **Phase 05 (Agent 2)** and **Phase 06 (Agent 3)**.
