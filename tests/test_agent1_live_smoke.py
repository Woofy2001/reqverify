"""Live smoke test for Agent 1 (Requirements Analyst).

Auto-skips when ANTHROPIC_API_KEY is not set in environment.
When executed, performs 1 live extraction on REQ-DEV-01 to verify Claude Sonnet 5.5 structured output.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from reqverify.schemas.contracts import CoverageMatrix
from reqverify.agents.analyst import RequirementsAnalystAgent
from reqverify.llm.client import LLMClient

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_REQS_PATH = REPO_ROOT / "dev_app" / "requirements.md"


@pytest.mark.live
def test_agent1_live_extraction_smoke():
    """Live smoke test verifying real Claude 3.5/5.5 API structured parsing on dev requirement."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Skipping live test: ANTHROPIC_API_KEY environment variable is not set")

    single_req = (
        "## REQ-DEV-01: Task Creation\n"
        'The user interface shall provide an input field with the accessible name "Task title" and an "Add Task" button. '
        'When the user enters a non-empty task description and activates the "Add Task" button, the system shall append the task to the active tasks list.'
    )

    client = LLMClient(run_id="live-smoke-agent1")
    agent = RequirementsAnalystAgent(llm_client=client)

    matrix = agent.analyze_document(single_req)

    assert isinstance(matrix, CoverageMatrix)
    assert len(matrix.conditions) >= 1
    for cond in matrix.conditions:
        assert cond.source_requirement_id == "REQ-DEV-01"
        assert len(cond.source_span) > 0
        assert cond.condition_id.startswith("REQ-DEV-01.")
        assert cond.extraction_confidence > 0.0
