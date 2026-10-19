import os
import json
import sqlite3
import pytest
from pydantic import BaseModel, Field

from reqverify.llm.client import (
    LLMClient,
    CallMeta,
    RefusalError,
    TruncatedError,
    BudgetExceededError
)

class SampleSchema(BaseModel):
    title: str
    score: int
    rationale: str = Field(description="A one-sentence justification.")

def test_cache_hit_identical_call(tmp_path):
    """Proves that a second call with identical arguments and run_id returns cached response."""
    db_path = str(tmp_path / "cache.sqlite")
    client = LLMClient(db_path=db_path, run_id="run-001", use_cache=True)
    
    # Pre-populate cache directly or execute mock
    schema = SampleSchema
    key = client._key("system prompt", "user query", schema)
    fake_response = SampleSchema(title="Test Result", score=95, rationale="Valid test.")
    fake_meta = {
        "response_id": "resp-mock-1",
        "model": "claude-sonnet-5-5",
        "input_tokens": 50,
        "output_tokens": 20,
        "stop_reason": "end_turn",
        "latency_s": 0.25,
        "cache_hit": False
    }
    client._save_cache(key, "run-001", {"prompt": "user query"}, fake_response.model_dump(), fake_meta)
    
    # Call parse - should hit cache
    res, meta = client.parse("system prompt", "user query", SampleSchema)
    assert meta.cache_hit is True
    assert res.title == "Test Result"
    assert res.score == 95

def test_cache_key_includes_run_id(tmp_path):
    """Proves that different run_ids produce different keys and miss cache."""
    db_path = str(tmp_path / "cache.sqlite")
    client1 = LLMClient(db_path=db_path, run_id="replicate-1", use_cache=True)
    client2 = LLMClient(db_path=db_path, run_id="replicate-2", use_cache=True)
    
    key1 = client1._key("sys", "user", SampleSchema)
    key2 = client2._key("sys", "user", SampleSchema)
    assert key1 != key2

def test_refusal_raises_refusal_error():
    """Verify that a response with stop_reason='refusal' raises RefusalError."""
    with pytest.raises(RefusalError, match="Model refused"):
        LLMClient._check_stop_reason("refusal")

def test_truncation_raises_truncated_error():
    """Verify that a response with stop_reason='max_tokens' raises TruncatedError."""
    with pytest.raises(TruncatedError, match="Response truncated"):
        LLMClient._check_stop_reason("max_tokens")

def test_parameter_rejection():
    """Verify that attempting to pass temperature or top_p raises ValueError."""
    client = LLMClient(run_id="test")
    with pytest.raises(ValueError, match="temperature"):
        client._validate_parameters(temperature=0.7)
    with pytest.raises(ValueError, match="top_p"):
        client._validate_parameters(top_p=0.9)
