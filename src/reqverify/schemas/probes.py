"""Pydantic contracts private to Agent 3 (generator/critic loop).

``ProbeResult`` and ``CriticVerdict`` live in :mod:`reqverify.schemas.contracts` (Guide §7.1) and are
re-exported here so Agent 3 code has a single import location.
"""

from __future__ import annotations

from pydantic import Field

from reqverify.safety.ast_validator import ScriptSafetyViolation
from reqverify.schemas.contracts import CriticVerdict, ProbeResult
from pydantic import BaseModel


class GeneratedTest(BaseModel):
    """What the Generator LLM returns: one complete, self-contained pytest-playwright module."""

    script: str = Field(description="Complete Python source of one pytest-playwright test module")
    notes: str = Field(default="", description="Optional one-line note on locator/wait choices")


class CriticDecision(CriticVerdict):
    """What the Critic LLM returns: the Guide's CriticVerdict plus the test-bug / app-defect dichotomy."""

    is_test_bug: bool = Field(
        description=(
            "True if the failure is caused by the test itself (bad locator, missing wait, wrong navigation); "
            "False if the test is sound and the application genuinely violates the condition, or the test passed"
        )
    )


__all__ = ["CriticDecision", "CriticVerdict", "GeneratedTest", "ProbeResult", "ScriptSafetyViolation"]
