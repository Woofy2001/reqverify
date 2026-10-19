from __future__ import annotations
from typing import Type, TypeVar, Dict, Any, List, Optional
from pydantic import BaseModel

from reqverify.llm.client import CallMeta

T = TypeVar("T", bound=BaseModel)

class FakeLLMClient:
    """Mock/Fixture LLM client enabling fast, deterministic, zero-cost offline testing."""

    def __init__(self, run_id: str = "test", model: str = "fake-claude-sonnet-5-5"):
        self.run_id = run_id
        self.model = model
        self.call_history: List[Dict[str, Any]] = []
        self._schema_responses: Dict[Type[BaseModel], Any] = {}
        self._prompt_responses: Dict[str, Any] = {}
        self.cumulative_cost_usd: float = 0.0

    def register_response(self, schema: Type[T], response: T | dict | str):
        """Register a fixture response to return whenever this schema is requested."""
        self._schema_responses[schema] = response

    def register_prompt_response(self, user_substring: str, response: Any):
        """Register a fixture response when the user prompt contains the given substring."""
        self._prompt_responses[user_substring] = response

    def parse(self, system: str, user: str, schema: Type[T], **kwargs) -> tuple[T, CallMeta]:
        """Return registered fixture response without making external network calls."""
        self.call_history.append({
            "system": system,
            "user": user,
            "schema": schema,
            "kwargs": kwargs
        })

        # 1. Check prompt-specific fixtures
        for sub, resp in self._prompt_responses.items():
            if sub in user:
                return self._resolve_response(resp, schema)

        # 2. Check schema-level fixtures
        if schema in self._schema_responses:
            return self._resolve_response(self._schema_responses[schema], schema)

        raise KeyError(
            f"No recorded response registered in FakeLLMClient for schema {schema.__name__} "
            f"or prompt snippet: '{user[:50]}...'"
        )

    def _resolve_response(self, raw_resp: Any, schema: Type[T]) -> tuple[T, CallMeta]:
        if isinstance(raw_resp, schema):
            output = raw_resp
        elif isinstance(raw_resp, dict):
            output = schema.model_validate(raw_resp)
        elif isinstance(raw_resp, str):
            output = schema.model_validate_json(raw_resp)
        else:
            raise TypeError(f"Unsupported fixture response type: {type(raw_resp)}")

        meta = CallMeta(
            response_id=f"fake-resp-{len(self.call_history)}",
            model=self.model,
            input_tokens=100,
            output_tokens=50,
            stop_reason="end_turn",
            latency_s=0.01,
            cache_hit=False
        )
        return output, meta
