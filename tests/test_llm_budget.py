import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
import anthropic

from reqverify.llm.client import LLMClient, BudgetExceededError

class SampleSchema(BaseModel):
    value: str

def test_budget_guard_trips():
    """Asserts that client with exceeded cumulative spend rejects subsequent calls."""
    client = LLMClient(db_path=":memory:", max_budget_usd=0.01)
    # Artificially set cumulative cost above budget
    client.cumulative_cost_usd = 0.02
    
    with pytest.raises(BudgetExceededError, match="Budget limit"):
        client.parse("sys", "user", SampleSchema)

def test_cost_calculation():
    """Asserts input and output token pricing conforms to specifications."""
    client = LLMClient(db_path=":memory:")
    # 1,000,000 input tokens = $2.00, 500,000 output tokens = $5.00 -> total $7.00
    cost = client._calculate_cost(1_000_000, 500_000)
    assert pytest.approx(cost, 0.001) == 7.00

def test_retry_on_rate_limit_transient():
    """Verifies that transient RateLimitError retries before succeeding."""
    client = LLMClient(db_path=":memory:", api_key="mock-key", use_cache=False)
    
    mock_response = MagicMock()
    mock_response.id = "resp-123"
    mock_response.stop_reason = "end_turn"
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.parsed_output = SampleSchema(value="repaired")
    
    mock_messages = MagicMock()
    # First call raises RateLimitError, second call succeeds
    mock_response_err = MagicMock()
    mock_response_err.status_code = 429
    rate_err = anthropic.RateLimitError("Rate limit exceeded", response=mock_response_err, body=None)
    mock_messages.parse.side_effect = [rate_err, mock_response]
    
    mock_anthropic = MagicMock()
    mock_anthropic.messages = mock_messages
    client._client = mock_anthropic
    
    with patch("time.sleep", return_value=None):
        res, meta = client.parse("sys", "user", SampleSchema)
        assert res.value == "repaired"
        assert meta.input_tokens == 100
        assert mock_messages.parse.call_count == 2
