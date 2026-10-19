import os
import pytest
from pydantic import BaseModel, Field

from reqverify.llm.client import LLMClient

class LiveSmokeOutput(BaseModel):
    message: str
    rationale: str = Field(description="A one-sentence justification.")

@pytest.mark.live
def test_live_claude_smoke():
    """Verify live Claude Sonnet 5.5 connection and structured output parsing."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    client = LLMClient(db_path=":memory:", run_id="live-smoke", use_cache=False)
    res, meta = client.parse(
        system="You are an academic software verification assistant.",
        user="State that the connection test succeeded with a one-sentence rationale.",
        schema=LiveSmokeOutput
    )

    assert isinstance(res, LiveSmokeOutput)
    assert len(res.message) > 0
    assert meta.model == "claude-sonnet-5-5"
    assert meta.stop_reason == "end_turn"
