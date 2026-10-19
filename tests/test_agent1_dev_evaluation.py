"""Tests evaluating RQ1 baseline extraction metrics (Precision, Recall, F1) on the development set (Invariant D13).

Confirms:
- Extraction Recall >= 0.80 on dev_app requirements (RQ1 benchmark target).
- Precision >= 0.80 and F1 >= 0.80.
- Strict isolation: zero evaluation requirements are touched (Invariant D13).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from reqverify.schemas.contracts import LLMCondition, LLMExtraction, normalize
from reqverify.agents.analyst import RequirementsAnalystAgent
from reqverify.llm.fake_client import FakeLLMClient

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_REQS_PATH = REPO_ROOT / "dev_app" / "requirements.md"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "agent1" / "dev_extractions.json"


# Dev Ground Truth Answer Key (Expected 10 conditions across REQ-DEV-01..05)
DEV_GROUND_TRUTH = [
    {
        "req_id": "REQ-DEV-01",
        "span": 'The user interface shall provide an input field with the accessible name "Task title" and an "Add Task" button.',
    },
    {
        "req_id": "REQ-DEV-01",
        "span": 'When the user enters a non-empty task description and activates the "Add Task" button, the system shall append the task to the active tasks list.',
    },
    {
        "req_id": "REQ-DEV-02",
        "span": 'Each task item in the active list shall display a "Complete Task" button.',
    },
    {
        "req_id": "REQ-DEV-02",
        "span": 'Activating this button shall transition the task status from "Active" to "Completed" and update its status badge text accordingly.',
    },
    {
        "req_id": "REQ-DEV-03",
        "span": 'The application shall provide a filter combobox with the accessible name "Filter by priority" containing options for "All", "High", "Medium", and "Low".',
    },
    {
        "req_id": "REQ-DEV-03",
        "span": 'Selecting a priority option shall restrict the visible task items to those matching the selected priority.',
    },
    {
        "req_id": "REQ-DEV-04",
        "span": 'Each task item shall include a "Delete Task" button.',
    },
    {
        "req_id": "REQ-DEV-04",
        "span": 'Activating this button shall remove the item from the list and decrease the total task count displayed in the header.',
    },
    {
        "req_id": "REQ-DEV-05",
        "span": 'The task management service shall transmit encrypted audit telemetry to an internal enterprise logging cluster upon every state change.',
    },
    {
        "req_id": "REQ-DEV-05",
        "span": 'This process executes entirely in background workers and does not alter the user interface.',
    },
]


def test_dev_set_extraction_recall_precision_f1():
    """Verify Agent 1 meets RQ1 threshold targets: Recall >= 0.80, Precision >= 0.80, F1 >= 0.80."""
    assert FIXTURE_PATH.exists()
    fixture_data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    fake_client = FakeLLMClient()
    for req_id, conditions_raw in fixture_data.items():
        conditions = [LLMCondition(**c) for c in conditions_raw]
        fake_client.register_prompt_response(req_id, LLMExtraction(conditions=conditions))

    agent = RequirementsAnalystAgent(llm_client=fake_client)
    matrix = agent.analyze_document(DEV_REQS_PATH)

    extracted_conditions = matrix.conditions
    assert len(extracted_conditions) > 0

    # Matching protocol: Match on requirement ID and normalized source span overlap
    true_positives = 0
    matched_gt_indices = set()

    for extracted in extracted_conditions:
        norm_ext_span = normalize(extracted.source_span)
        found_match = False

        for i, gt in enumerate(DEV_GROUND_TRUTH):
            if i in matched_gt_indices:
                continue
            if extracted.source_requirement_id == gt["req_id"]:
                norm_gt_span = normalize(gt["span"])
                # Jaccard word token overlap or verbatim inclusion
                tokens_ext = set(norm_ext_span.split())
                tokens_gt = set(norm_gt_span.split())
                overlap = len(tokens_ext & tokens_gt) / max(1, len(tokens_ext | tokens_gt))

                if overlap >= 0.80 or norm_gt_span in norm_ext_span or norm_ext_span in norm_gt_span:
                    true_positives += 1
                    matched_gt_indices.add(i)
                    found_match = True
                    break

    false_positives = len(extracted_conditions) - true_positives
    false_negatives = len(DEV_GROUND_TRUTH) - len(matched_gt_indices)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print(f"\n[Dev Extraction Evaluation] TP={true_positives}, FP={false_positives}, FN={false_negatives}")
    print(f"[Dev Extraction Evaluation] Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

    # Invariant & RQ1 Criteria Check
    assert recall >= 0.80, f"Extraction Recall {recall:.2f} failed to meet RQ1 target (>= 0.80)"
    assert precision >= 0.80, f"Extraction Precision {precision:.2f} failed to meet target (>= 0.80)"
    assert f1 >= 0.80, f"Extraction F1 {f1:.2f} failed to meet target (>= 0.80)"


def test_no_eval_data_leaked_in_dev_evaluation():
    """Invariant D13: Evaluation ground truth must not be referenced during dev tuning."""
    import inspect
    from reqverify.agents import analyst, postprocessor, ingestion

    analyst_src = inspect.getsource(analyst)
    postprocessor_src = inspect.getsource(postprocessor)
    ingestion_src = inspect.getsource(ingestion)

    combined_code = analyst_src + postprocessor_src + ingestion_src
    # Assert neither the evaluation folder nor ground truth file is hardcoded
    assert "eval/ground_truth" not in combined_code
    assert "mutants_expected.csv" not in combined_code
    assert "conditions.csv" not in combined_code
