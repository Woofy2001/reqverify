from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Type, TypeVar, Any, Optional

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
DEFAULT_MODEL = "claude-sonnet-5-5"

# Pricing per million tokens (Claude Sonnet 3.5 / 5.5 baseline)
INPUT_COST_PER_MILLION = 2.00
OUTPUT_COST_PER_MILLION = 10.00

class RefusalError(RuntimeError):
    """Raised when the LLM refuses to answer due to policy or guardrails."""
    pass

class TruncatedError(RuntimeError):
    """Raised when output is truncated due to max_tokens exhaustion."""
    pass

class BudgetExceededError(RuntimeError):
    """Raised when cumulative token expenditure breaches the safety limit."""
    pass

@dataclass
class CallMeta:
    response_id: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    latency_s: float
    cache_hit: bool

class LLMClient:
    """Production LLM client with SQLite caching, structured outputs, budget guard, and exponential retries."""

    def __init__(
        self,
        db_path: str = "cache/llm_cache.sqlite",
        model: str = DEFAULT_MODEL,
        run_id: str = "dev",
        use_cache: bool = True,
        max_tokens: int = 16_000,
        effort: str = "medium",
        max_budget_usd: float = 10.0,
        api_key: Optional[str] = None
    ):
        self.model = model
        self.run_id = run_id
        self.use_cache = use_cache
        self.max_tokens = max_tokens
        self.effort = effort
        self.max_budget_usd = max_budget_usd
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.cumulative_cost_usd: float = 0.0

        # Lazy initialize Anthropic client only when making network calls
        self._client: Optional[anthropic.Anthropic] = None

        # Setup SQLite caching database
        self.db_path = db_path
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        with self.db:
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS calls ("
                "key TEXT PRIMARY KEY, "
                "created REAL, "
                "run_id TEXT, "
                "request TEXT, "
                "response TEXT, "
                "meta TEXT)"
            )
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_calls_run_id ON calls(run_id)")

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set. Cannot dispatch live LLM call.")
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _key(self, system: str, user: str, schema: Type[BaseModel]) -> str:
        """Deterministic SHA-256 hash incorporating model, prompts, schema, and run_id."""
        payload = json.dumps(
            {
                "model": self.model,
                "system": system,
                "user": user,
                "schema": schema.model_json_schema(),
                "run_id": self.run_id
            },
            sort_keys=True
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_parameters(**kwargs):
        """Disallow invalid sampling parameters per Invariant D1."""
        disallowed = {"temperature", "top_p", "top_k", "prefill", "tool_choice"}
        found = disallowed.intersection(kwargs.keys())
        if found:
            raise ValueError(f"Parameters {found} are disallowed for {DEFAULT_MODEL} per Invariant D1.")

    @staticmethod
    def _check_stop_reason(stop_reason: str):
        if stop_reason == "refusal":
            raise RefusalError("Model refused to answer the prompt.")
        if stop_reason == "max_tokens":
            raise TruncatedError("Response truncated: max_tokens reached before schema completed.")

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000.0) * INPUT_COST_PER_MILLION
        output_cost = (output_tokens / 1_000_000.0) * OUTPUT_COST_PER_MILLION
        return input_cost + output_cost

    def _save_cache(self, key: str, run_id: str, request: dict, response_data: dict, meta: dict):
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO calls VALUES (?, ?, ?, ?, ?, ?)",
                (
                    key,
                    time.time(),
                    run_id,
                    json.dumps(request),
                    json.dumps(response_data),
                    json.dumps(meta)
                )
            )

    def parse(self, system: str, user: str, schema: Type[T], **kwargs) -> tuple[T, CallMeta]:
        """Parse prompt into Pydantic schema with caching, budget checking, and retries."""
        self._validate_parameters(**kwargs)

        if self.cumulative_cost_usd >= self.max_budget_usd:
            raise BudgetExceededError(
                f"Budget limit of ${self.max_budget_usd:.2f} exceeded. Current spend: ${self.cumulative_cost_usd:.4f}"
            )

        key = self._key(system, user, schema)

        # 1. Check cache
        if self.use_cache:
            cursor = self.db.cursor()
            cursor.execute("SELECT response, meta FROM calls WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                resp_json = row[0]
                meta_dict = json.loads(row[1])
                meta_dict["cache_hit"] = True
                call_meta = CallMeta(**meta_dict)
                return schema.model_validate_json(resp_json), call_meta

        # 2. Live dispatch with retry
        t0 = time.time()
        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                response = self.client.messages.parse(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_format=schema
                )
                break
            except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(backoff)
                backoff *= 2.0

        latency = time.time() - t0
        stop_reason = response.stop_reason or "end_turn"
        self._check_stop_reason(stop_reason)

        in_tok = response.usage.input_tokens
        out_tok = response.usage.output_tokens
        self.cumulative_cost_usd += self._calculate_cost(in_tok, out_tok)

        meta = CallMeta(
            response_id=response.id,
            model=self.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            stop_reason=stop_reason,
            latency_s=latency,
            cache_hit=False
        )

        parsed_output: T = response.parsed_output

        # 3. Store in cache
        if self.use_cache:
            self._save_cache(
                key,
                self.run_id,
                {"system": system, "user": user},
                parsed_output.model_dump(),
                asdict(meta)
            )

        return parsed_output, meta
