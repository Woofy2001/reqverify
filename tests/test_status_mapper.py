"""Unit tests for Agent 4 deterministic status mapping engine (Guide §7.3)."""

from __future__ import annotations

import pytest

from reqverify.reports.status_mapper import StatusMappingResult, derive_status
from reqverify.schemas.contracts import CriticVerdict, ExtractedCondition, ProbeResult


def _make_condition(*, is_testable: bool = True, req_id: str = "REQ-01") -> ExtractedCondition:
    return ExtractedCondition(
        condition_id=f"{req_id}.1-12345678",
        document_hash="doc_sha256",
        source_requirement_id=req_id,
        source_span="When a user logs in with valid credentials, the catalog is shown.",
        predicate_text="Logging in with valid credentials redirects to the catalog.",
        is_testable=is_testable,
        untestable_reason=None if is_testable else "Backend-only database invariant",
        extraction_confidence=0.95,
        rationale="Atomic post-condition on login redirect behaviour.",
    )


def test_pass_derivation() -> None:
    """Probe passed + Critic APPROVE -> PASS."""
    cond = _make_condition(is_testable=True)
    probe = ProbeResult(
        exit_code=0,
        outcome="passed",
        exception_type=None,
        stdout_tail="1 passed in 1.20s",
        duration_s=1.2,
        trace_path="traces/run_1/REQ-01.1-12345678_iter1.zip",
    )
    critic = CriticVerdict(
        verdict="APPROVE",
        assertion_validity_score=0.95,
        critique_notes="Test accurately verifies the catalog redirect.",
    )

    res: StatusMappingResult = derive_status(
        condition=cond,
        probe=probe,
        critic=critic,
        final_state="approved",
    )

    assert res.execution_status == "PASS"
    assert res.untested_reason is None
    assert res.needs_human_review is False
    assert "passed" in res.audit_rationale.lower() or "held" in res.audit_rationale.lower()


def test_fail_derivation() -> None:
    """Probe assertion_failed (AssertionError) + Critic APPROVE -> FAIL."""
    cond = _make_condition(is_testable=True, req_id="REQ-03")
    probe = ProbeResult(
        exit_code=1,
        outcome="assertion_failed",
        exception_type="AssertionError",
        stdout_tail="AssertionError: Locator expected to have text '$85.50' Actual value: '$104.50'",
        duration_s=1.8,
        trace_path="traces/run_1/REQ-03.1-12345678_iter1.zip",
    )
    critic = CriticVerdict(
        verdict="APPROVE",
        assertion_validity_score=0.92,
        critique_notes="Locators resolved cleanly; application calculation violates discount predicate.",
    )

    res = derive_status(
        condition=cond,
        probe=probe,
        critic=critic,
        final_state="approved",
    )

    assert res.execution_status == "FAIL"
    assert res.untested_reason is None
    assert res.needs_human_review is False
    assert "assertion" in res.audit_rationale.lower()


def test_error_derivation_timeout() -> None:
    """Probe runtime_error or timeout -> ERROR."""
    cond = _make_condition(is_testable=True, req_id="REQ-04")
    probe_timeout = ProbeResult(
        exit_code=1,
        outcome="timeout",
        exception_type="TimeoutError",
        stdout_tail="TimeoutError: Locator.click: Timeout 5000ms exceeded.",
        duration_s=5.1,
    )
    critic = CriticVerdict(
        verdict="APPROVE",
        assertion_validity_score=0.80,
        critique_notes="Approved despite runtime timeout.",
    )

    res_timeout = derive_status(
        condition=cond,
        probe=probe_timeout,
        critic=critic,
        final_state="approved",
    )
    assert res_timeout.execution_status == "ERROR"
    assert res_timeout.untested_reason is None

    probe_runtime = ProbeResult(
        exit_code=1,
        outcome="runtime_error",
        exception_type="Error",
        stdout_tail="Error: strict mode violation: get_by_role('button') resolved to 3 elements",
        duration_s=0.9,
    )
    res_runtime = derive_status(
        condition=cond,
        probe=probe_runtime,
        critic=critic,
        final_state="approved",
    )
    assert res_runtime.execution_status == "ERROR"
    assert res_runtime.untested_reason is None


def test_untested_not_ui_observable() -> None:
    """Condition flagged ui_observable=False / is_testable=False (e.g. REQ-09) -> UNTESTED (not_ui_observable)."""
    cond = _make_condition(is_testable=False, req_id="REQ-09")

    res = derive_status(condition=cond)

    assert res.execution_status == "UNTESTED"
    assert res.untested_reason == "not_ui_observable"
    assert res.needs_human_review is False
    assert "backend" in res.audit_rationale.lower() or "observable" in res.audit_rationale.lower()


def test_untested_no_selector() -> None:
    """Agent 2 returns no_selector_found -> UNTESTED (untested_reason='no_selector_found')."""
    cond = _make_condition(is_testable=True, req_id="REQ-05")

    res = derive_status(
        condition=cond,
        no_selector_found=True,
    )

    assert res.execution_status == "UNTESTED"
    assert res.untested_reason == "no_selector_found"
    assert res.needs_human_review is False
    assert "selector" in res.audit_rationale.lower()


def test_untested_critic_not_converged() -> None:
    """Subgraph terminates with not_converged -> UNTESTED (critic_not_converged, needs_human_review=True)."""
    cond = _make_condition(is_testable=True, req_id="REQ-07")
    probe = ProbeResult(
        exit_code=1,
        outcome="runtime_error",
        exception_type="TimeoutError",
        stdout_tail="TimeoutError waiting for selector",
        duration_s=5.0,
    )
    critic = CriticVerdict(
        verdict="REJECT",
        assertion_validity_score=0.35,
        critique_notes="Locator still times out on step 2 after 3 iterations.",
        suggested_refinement="Use get_by_role('textbox', name='Address')",
    )

    res = derive_status(
        condition=cond,
        probe=probe,
        critic=critic,
        final_state="not_converged",
    )

    assert res.execution_status == "UNTESTED"
    assert res.untested_reason == "critic_not_converged"
    assert res.needs_human_review is True
    assert "converge" in res.audit_rationale.lower() or "human review" in res.audit_rationale.lower()
