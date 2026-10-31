import pytest
from pydantic import BaseModel, Field

from reqverify.llm.fake_client import FakeLLMClient
from reqverify.llm.client import CallMeta

class SampleContract(BaseModel):
    verdict: str
    rationale: str = Field(description="A one-sentence justification.")

def test_fake_client_returns_configured_response():
    client = FakeLLMClient(run_id="offline-test")
    expected = SampleContract(verdict="APPROVE", rationale="All assertions verified.")
    client.register_response(SampleContract, expected)
    
    result, meta = client.parse("system prompt", "user instruction", SampleContract)
    assert result.verdict == "APPROVE"
    assert result.rationale == "All assertions verified."
    assert meta.cache_hit is False
    assert meta.model == "fake-claude-sonnet-5-5"

def test_fake_client_records_call_history():
    client = FakeLLMClient()
    expected = SampleContract(verdict="REJECT", rationale="Missing timeout.")
    client.register_response(SampleContract, expected)
    
    client.parse("sys", "user-1", SampleContract)
    client.parse("sys", "user-2", SampleContract)
    
    assert len(client.call_history) == 2
    assert client.call_history[0]["user"] == "user-1"
    assert client.call_history[1]["user"] == "user-2"

def test_fake_client_unregistered_schema_raises_key_error():
    client = FakeLLMClient()
    with pytest.raises(KeyError, match="No recorded response registered"):
        client.parse("sys", "user", SampleContract)


def test_fake_client_sequence_returns_responses_in_order_then_repeats_last():
    class Out(BaseModel):
        n: int

    fake = FakeLLMClient()
    fake.register_sequence(Out, [Out(n=1), {"n": 2}])
    assert fake.parse("s", "u", Out)[0].n == 1
    assert fake.parse("s", "u", Out)[0].n == 2
    assert fake.parse("s", "u", Out)[0].n == 2  # exhausted: last response repeats
