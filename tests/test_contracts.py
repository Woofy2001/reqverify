"""Tests verifying Pydantic v2 data contracts and deterministic condition ID generation (Guide §7.1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_contracts_importable():
    """Verify contracts and utility functions can be imported."""
    from reqverify.schemas.contracts import (
        normalize,
        make_condition_id,
        LLMCondition,
        LLMExtraction,
        ExtractedCondition,
        CoverageMatrix,
        UIElementSelector,
        ProbeResult,
        CriticVerdict,
        RequirementVerificationResult,
    )
    assert callable(normalize)
    assert callable(make_condition_id)


def test_normalize_whitespace_and_casing():
    """Verify whitespace normalization and lowercasing."""
    from reqverify.schemas.contracts import normalize
    assert normalize("  Valid   Email   Address \n\t ") == "valid email address"
    assert normalize("HELLO   WORLD") == "hello world"


def test_make_condition_id_determinism():
    """Verify deterministic SHA-256 8-character hashed condition ID generation."""
    from reqverify.schemas.contracts import make_condition_id

    id1 = make_condition_id("REQ-01", "Valid email format required", 1)
    id2 = make_condition_id("REQ-01", "  Valid   email   format required \n ", 1)
    id3 = make_condition_id("REQ-01", "valid email format required", 1)

    # Identical across calls and whitespace-insensitive
    assert id1 == id2 == id3
    assert id1.startswith("REQ-01.1-")
    assert len(id1.split("-")[-1]) == 8


def test_make_condition_id_differentiation():
    """Verify different ordinals, requirements, or spans produce unique IDs."""
    from reqverify.schemas.contracts import make_condition_id

    base_id = make_condition_id("REQ-01", "Valid email format required", 1)
    diff_ordinal = make_condition_id("REQ-01", "Valid email format required", 2)
    diff_req = make_condition_id("REQ-02", "Valid email format required", 1)
    diff_span = make_condition_id("REQ-01", "Password must have 6 chars", 1)

    assert base_id != diff_ordinal
    assert base_id != diff_req
    assert base_id != diff_span


def test_llm_condition_validation():
    """Verify LLMCondition parses valid inputs and rejects out-of-bound values."""
    from reqverify.schemas.contracts import LLMCondition

    cond = LLMCondition(
        source_requirement_id="REQ-01",
        source_span="The system shall validate email address format.",
        predicate_text="Email without @ or domain extension is rejected with an error message.",
        is_testable=True,
        extraction_confidence=0.95,
        rationale="Separates syntactic email validation from password security criteria.",
    )
    assert cond.is_testable is True
    assert cond.untestable_reason is None
    assert cond.extraction_confidence == 0.95

    # Out-of-bounds confidence (must be between 0.0 and 1.0)
    with pytest.raises(ValidationError):
        LLMCondition(
            source_requirement_id="REQ-01",
            source_span="Span",
            predicate_text="Predicate",
            is_testable=True,
            extraction_confidence=1.5,
            rationale="Rationale with min length",
        )

    # Rationale too short (< 10 chars)
    with pytest.raises(ValidationError):
        LLMCondition(
            source_requirement_id="REQ-01",
            source_span="Span",
            predicate_text="Predicate",
            is_testable=True,
            extraction_confidence=0.8,
            rationale="Too short",
        )


def test_llm_extraction_and_coverage_matrix():
    """Verify LLMExtraction and CoverageMatrix contracts."""
    from reqverify.schemas.contracts import (
        LLMCondition,
        LLMExtraction,
        ExtractedCondition,
        CoverageMatrix,
    )

    llm_cond = LLMCondition(
        source_requirement_id="REQ-02",
        source_span="Password must contain at least 6 characters.",
        predicate_text="Password shorter than 6 characters prevents submission.",
        is_testable=True,
        extraction_confidence=0.9,
        rationale="Independent password length constraint check.",
    )

    extraction = LLMExtraction(conditions=[llm_cond])
    assert len(extraction.conditions) == 1

    extracted = ExtractedCondition(
        **llm_cond.model_dump(),
        condition_id="REQ-02.1-a1b2c3d4",
        document_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    assert extracted.condition_id == "REQ-02.1-a1b2c3d4"

    matrix = CoverageMatrix(
        document_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        model="claude-sonnet-5-5",
        conditions=[extracted],
    )
    assert len(matrix.conditions) == 1
    assert matrix.model == "claude-sonnet-5-5"


def test_agent2_to_4_contracts():
    """Verify Agent 2, 3, and 4 contracts validate correctly."""
    from reqverify.schemas.contracts import (
        UIElementSelector,
        ProbeResult,
        CriticVerdict,
        RequirementVerificationResult,
    )

    selector = UIElementSelector(
        element_id="btn_submit",
        role="button",
        accessible_name="Sign in",
        locator_code='page.get_by_role("button", name="Sign in")',
        page_url="http://127.0.0.1:3000/login",
    )
    assert selector.role == "button"

    probe = ProbeResult(
        exit_code=0,
        outcome="passed",
        duration_s=1.25,
    )
    assert probe.outcome == "passed"
    assert probe.exception_type is None

    verdict = CriticVerdict(
        verdict="APPROVE",
        assertion_validity_score=0.95,
        critique_notes="Precise assertion checking visible error message.",
    )
    assert verdict.verdict == "APPROVE"

    result = RequirementVerificationResult(
        requirement_id="REQ-01",
        condition_id="REQ-01.1-a1b2c3d4",
        execution_status="PASS",
        overall_confidence=0.92,
        audit_rationale="Critic approved test passed with 0 exit code.",
    )
    assert result.execution_status == "PASS"
    assert result.untested_reason is None
