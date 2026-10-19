"""Tests verifying Agent 1 RequirementsAnalystAgent end-to-end execution with fake/recorded client."""

from __future__ import annotations

from pathlib import Path
import pytest

from reqverify.schemas.contracts import LLMCondition, LLMExtraction, CoverageMatrix
from reqverify.llm.fake_client import FakeLLMClient

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_REQS_PATH = REPO_ROOT / "dev_app" / "requirements.md"


def test_analyst_agent_importable():
    """Verify RequirementsAnalystAgent is exportable."""
    from reqverify.agents.analyst import RequirementsAnalystAgent
    assert RequirementsAnalystAgent is not None


def test_analyst_agent_extracts_coverage_matrix():
    """Verify analyst agent processes dev requirements document and returns CoverageMatrix."""
    from reqverify.agents.analyst import RequirementsAnalystAgent

    # Configure FakeLLMClient with synthetic responses for the 5 dev requirements
    fake_client = FakeLLMClient()

    # Generic realistic responses for any dev requirement call
    mock_extraction = LLMExtraction(
        conditions=[
            LLMCondition(
                source_requirement_id="REQ-DEV-01",
                source_span='The user interface shall provide an input field with the accessible name "Task title" and an "Add Task" button.',
                predicate_text='Input field with name "Task title" and "Add Task" button exist on page.',
                is_testable=True,
                extraction_confidence=0.96,
                rationale="Validates existence of task creation controls.",
            ),
            LLMCondition(
                source_requirement_id="REQ-DEV-01",
                source_span='When the user enters a non-empty task description and activates the "Add Task" button, the system shall append the task to the active tasks list.',
                predicate_text="Adding a task appends it to the active task list.",
                is_testable=True,
                extraction_confidence=0.94,
                rationale="Validates task addition behavior upon button activation.",
            ),
        ]
    )
    fake_client.register_response(LLMExtraction, mock_extraction)

    agent = RequirementsAnalystAgent(llm_client=fake_client)
    matrix = agent.analyze_document(DEV_REQS_PATH)

    assert isinstance(matrix, CoverageMatrix)
    assert len(matrix.document_hash) == 64
    assert matrix.model == "claude-sonnet-5-5"
    assert len(matrix.conditions) > 0

    # Ensure all conditions have valid deterministic IDs and document hashes
    for cond in matrix.conditions:
        assert cond.condition_id.startswith("REQ-")
        assert cond.document_hash == matrix.document_hash
        assert cond.extraction_confidence > 0.0

    # Ensure LLM was called 5 times (once per requirement chunk in dev_app)
    assert len(fake_client.call_history) == 5


def test_analyst_agent_replays_recorded_fixtures():
    """Verify analyst agent faithfully replays all 5 dev requirements from recorded JSON fixture."""
    import json
    from reqverify.agents.analyst import RequirementsAnalystAgent

    fixture_path = REPO_ROOT / "tests" / "fixtures" / "agent1" / "dev_extractions.json"
    assert fixture_path.exists()
    fixture_data = json.loads(fixture_path.read_text(encoding="utf-8"))

    fake_client = FakeLLMClient()
    for req_id, conditions_raw in fixture_data.items():
        conditions = [LLMCondition(**c) for c in conditions_raw]
        fake_client.register_prompt_response(req_id, LLMExtraction(conditions=conditions))

    agent = RequirementsAnalystAgent(llm_client=fake_client)
    matrix = agent.analyze_document(DEV_REQS_PATH)

    # 5 requirements x 2 conditions = 10 atomic conditions
    assert len(matrix.conditions) == 10
    assert agent.last_metrics.valid_count == 10
    assert agent.last_metrics.dropped_hallucinated_spans == 0
    assert agent.last_metrics.dropped_duplicates == 0

    # Verify REQ-DEV-05 conditions are correctly flagged as non-testable
    req5_conds = [c for c in matrix.conditions if c.source_requirement_id == "REQ-DEV-05"]
    assert len(req5_conds) == 2
    for c in req5_conds:
        assert c.is_testable is False
        assert c.untestable_reason is not None

