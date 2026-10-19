import os
import pytest
from pydantic import BaseModel, Field

class SampleCondition(BaseModel):
    condition_id: str
    predicate: str
    ui_observable: bool
    rationale: str = Field(description="A one-sentence justification.")

def test_spike_s1_offline_schema_transforms():
    """Verify Pydantic model transforms to valid JSON schema suitable for Claude structured outputs."""
    schema = SampleCondition.model_json_schema()
    assert schema["type"] == "object"
    assert "condition_id" in schema["properties"]
    assert "predicate" in schema["properties"]
    assert "ui_observable" in schema["properties"]
    assert "rationale" in schema["properties"]

    # Test JSON deserialization
    raw_json = '{"condition_id": "C-01.1", "predicate": "Login works", "ui_observable": true, "rationale": "Directly visible."}'
    parsed = SampleCondition.model_validate_json(raw_json)
    assert parsed.condition_id == "C-01.1"
    assert parsed.ui_observable is True

@pytest.mark.live
def test_spike_s1_live_parse():
    """Verify live Claude Sonnet 5.5 parsing with Pydantic model (requires ANTHROPIC_API_KEY)."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.parse(
        model="claude-sonnet-5-5",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": "Extract requirement: The login button must be enabled when credentials are valid."}
        ],
        output_format=SampleCondition
    )
    assert response.parsed_output is not None
    assert isinstance(response.parsed_output, SampleCondition)
