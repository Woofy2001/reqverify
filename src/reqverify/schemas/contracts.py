# src/reqverify/schemas/contracts.py
"""Immutable Pydantic v2 data contracts for ReqVerify multi-agent pipeline (Guide §7.1)."""

from __future__ import annotations

import hashlib
from typing import Literal, Optional
from pydantic import BaseModel, Field


def normalize(s: str) -> str:
    """Normalize text by collapsing whitespace and lowercasing."""
    return " ".join(s.lower().split())


def make_condition_id(req_id: str, source_span: str, ordinal: int) -> str:
    """Generate deterministic SHA-256 8-character hashed condition ID (Invariant D4)."""
    h = hashlib.sha256(f"{req_id}|{normalize(source_span)}|{ordinal}".encode("utf-8")).hexdigest()[:8]
    return f"{req_id}.{ordinal}-{h}"


# ---- Agent 1: what the LLM returns -------------------------------------------------
class LLMCondition(BaseModel):
    """Atomic testable condition extracted by Agent 1 from requirements text."""
    source_requirement_id: str = Field(
        description="ID of the requirement, exactly as written in the document, e.g. REQ-01"
    )
    source_span: str = Field(
        description="Verbatim text copied from the requirement that this condition comes from"
    )
    predicate_text: str = Field(
        description="One atomic, verifiable assertion about observable behaviour"
    )
    is_testable: bool = Field(
        description="True if a user can observe this through the web UI alone"
    )
    untestable_reason: Optional[str] = Field(
        default=None,
        description="Short reason if not testable"
    )
    extraction_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in this extraction, 0 to 1"
    )
    rationale: str = Field(
        min_length=10,
        description="One short sentence saying why this is a separate atomic condition"
    )


class LLMExtraction(BaseModel):
    """Container for conditions extracted by Agent 1 from a single requirement chunk."""
    conditions: list[LLMCondition]


# ---- After post-processing in code -------------------------------------------------
class ExtractedCondition(LLMCondition):
    """Post-processed condition enriched with deterministic ID and document hash."""
    condition_id: str
    document_hash: str


class CoverageMatrix(BaseModel):
    """Global matrix of all validated extracted conditions across a requirements document."""
    document_hash: str            # SHA-256 of the ingested document
    model: str
    conditions: list[ExtractedCondition]


# ---- Agent 2 -----------------------------------------------------------------------
class UIElementSelector(BaseModel):
    """Semantic UI element selector mapped by Agent 2 from ARIA snapshot."""
    element_id: str
    role: str                     # ARIA role from aria_snapshot, e.g. button, textbox
    accessible_name: str
    locator_code: str             # e.g. page.get_by_role("button", name="Add to cart")
    page_url: str


# ---- Agent 3: execution evidence vs LLM judgement ----------------------------------
class ProbeResult(BaseModel):
    """Sandboxed test execution evidence produced by running generated pytest script."""
    exit_code: int
    outcome: Literal["passed", "assertion_failed", "runtime_error", "timeout"]
    exception_type: Optional[str] = None
    stdout_tail: str = ""
    duration_s: float
    trace_path: Optional[str] = None


class CriticVerdict(BaseModel):
    """LLM critic evaluation of test script alignment with predicate text."""
    verdict: Literal["APPROVE", "REJECT"]
    assertion_validity_score: float = Field(ge=0.0, le=1.0)
    critique_notes: str
    suggested_refinement: Optional[str] = None


# ---- Agent 4 -----------------------------------------------------------------------
Status = Literal["PASS", "FAIL", "ERROR", "UNTESTED"]
UntestedReason = Literal["not_ui_observable", "no_selector_found", "critic_not_converged"]


class RequirementVerificationResult(BaseModel):
    """Final explainable verification verdict for a single condition (Guide §7.1, §7.3)."""
    requirement_id: str
    condition_id: str
    execution_status: Status
    untested_reason: Optional[UntestedReason] = None
    test_script_ref: Optional[str] = None
    critic_iterations: int = 0
    overall_confidence: float = Field(ge=0.0, le=1.0)
    audit_rationale: str
    needs_human_review: bool = False
