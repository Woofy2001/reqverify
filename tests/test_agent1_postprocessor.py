"""Tests verifying Agent 1 programmatic post-processing rules (Guide §7.2)."""

from __future__ import annotations

import pytest
from reqverify.schemas.contracts import LLMCondition, ExtractedCondition


def test_postprocessor_module_importable():
    """Verify post-processor exports postprocess_conditions and PostProcessorMetrics."""
    from reqverify.agents.postprocessor import postprocess_conditions, PostProcessorMetrics
    assert callable(postprocess_conditions)
    assert PostProcessorMetrics is not None


def test_postprocess_valid_conditions():
    """Rule 1 & 2: Valid verbatim spans receive deterministic condition IDs."""
    from reqverify.agents.postprocessor import postprocess_conditions

    doc_text = (
        "## REQ-01: User Authentication\n"
        "Registered users shall be able to log in by providing their email and password. "
        "Upon submitting valid credentials, the system shall authenticate the user and redirect to the catalog."
    )
    doc_hash = "abc12345" * 8

    raw_conditions = [
        LLMCondition(
            source_requirement_id="REQ-01",
            source_span="Registered users shall be able to log in by providing their email and password.",
            predicate_text="Valid email and password permits user authentication.",
            is_testable=True,
            extraction_confidence=0.95,
            rationale="Covers basic credential submission and verification.",
        ),
        LLMCondition(
            source_requirement_id="REQ-01",
            source_span="Upon submitting valid credentials, the system shall authenticate the user and redirect to the catalog.",
            predicate_text="Successful login redirects browser to /products catalog page.",
            is_testable=True,
            extraction_confidence=0.90,
            rationale="Verifies post-authentication navigation target.",
        ),
    ]

    valid_conditions, metrics = postprocess_conditions(
        raw_conditions=raw_conditions,
        document_text=doc_text,
        document_hash=doc_hash,
        req_id="REQ-01",
    )

    assert len(valid_conditions) == 2
    assert metrics.total_received == 2
    assert metrics.valid_count == 2
    assert metrics.dropped_hallucinated_spans == 0
    assert metrics.dropped_duplicates == 0

    c1, c2 = valid_conditions
    assert c1.condition_id.startswith("REQ-01.1-")
    assert c2.condition_id.startswith("REQ-01.2-")
    assert c1.document_hash == doc_hash
    assert c2.document_hash == doc_hash


def test_postprocess_rejects_hallucinated_span():
    """Rule 1: Rejects condition if source_span is not a substring of the document."""
    from reqverify.agents.postprocessor import postprocess_conditions

    doc_text = "## REQ-01: User Login\nUsers enter their credentials to sign in."
    doc_hash = "abc12345" * 8

    hallucinated_cond = LLMCondition(
        source_requirement_id="REQ-01",
        source_span="System requires retinal scan before granting access.",  # Hallucinated!
        predicate_text="Retinal scan must match biometric database.",
        is_testable=True,
        extraction_confidence=0.99,
        rationale="Biometric security requirement.",
    )

    valid_conditions, metrics = postprocess_conditions(
        raw_conditions=[hallucinated_cond],
        document_text=doc_text,
        document_hash=doc_hash,
        req_id="REQ-01",
    )

    assert len(valid_conditions) == 0
    assert metrics.total_received == 1
    assert metrics.valid_count == 0
    assert metrics.dropped_hallucinated_spans == 1


def test_postprocess_whitespace_tolerance():
    """Rule 1: Tolerates line breaks and extra whitespace in source_span."""
    from reqverify.agents.postprocessor import postprocess_conditions

    doc_text = "Users enter their credentials\n   to sign in to the application."
    doc_hash = "abc12345" * 8

    cond = LLMCondition(
        source_requirement_id="REQ-01",
        source_span="Users   enter their credentials to   sign in to the application.",
        predicate_text="Sign in accepts credentials.",
        is_testable=True,
        extraction_confidence=0.88,
        rationale="Validates credentials entry.",
    )

    valid_conditions, metrics = postprocess_conditions(
        raw_conditions=[cond],
        document_text=doc_text,
        document_hash=doc_hash,
        req_id="REQ-01",
    )

    assert len(valid_conditions) == 1
    assert metrics.valid_count == 1
    assert metrics.dropped_hallucinated_spans == 0


def test_postprocess_drops_exact_duplicate_predicates():
    """Rule 3: Drops exact duplicate conditions with identical predicate text."""
    from reqverify.agents.postprocessor import postprocess_conditions

    doc_text = "The password must be at least 6 characters long."
    doc_hash = "abc12345" * 8

    cond1 = LLMCondition(
        source_requirement_id="REQ-02",
        source_span="The password must be at least 6 characters long.",
        predicate_text="Password shorter than 6 characters is rejected.",
        is_testable=True,
        extraction_confidence=0.95,
        rationale="First extraction of minimum password rule.",
    )
    cond2 = LLMCondition(
        source_requirement_id="REQ-02",
        source_span="The password must be at least 6 characters long.",
        predicate_text="  Password shorter than 6 characters is rejected.  ",  # Duplicate!
        is_testable=True,
        extraction_confidence=0.92,
        rationale="Duplicate extraction of minimum password rule.",
    )

    valid_conditions, metrics = postprocess_conditions(
        raw_conditions=[cond1, cond2],
        document_text=doc_text,
        document_hash=doc_hash,
        req_id="REQ-02",
    )

    assert len(valid_conditions) == 1
    assert metrics.total_received == 2
    assert metrics.valid_count == 1
    assert metrics.dropped_duplicates == 1
