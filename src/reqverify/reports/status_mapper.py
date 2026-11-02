"""Deterministic status derivation engine implementing Guide §7.3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from reqverify.schemas.contracts import (
    CriticVerdict,
    ExtractedCondition,
    ProbeResult,
    Status,
    UntestedReason,
)


@dataclass(frozen=True)
class StatusMappingResult:
    """Output of the deterministic Guide §7.3 status mapper."""

    execution_status: Status
    untested_reason: Optional[UntestedReason]
    needs_human_review: bool
    audit_rationale: str


def derive_status(
    condition: Union[ExtractedCondition, dict],
    probe: Optional[Union[ProbeResult, dict]] = None,
    critic: Optional[Union[CriticVerdict, dict]] = None,
    *,
    final_state: Optional[str] = None,
    no_selector_found: bool = False,
) -> StatusMappingResult:
    """Map condition observability, selector availability, probe outcome, and critic decision to one of the 4 canonical statuses (Guide §7.3).

    Rules (in strict priority order):
    1. Not UI-observable (`condition.is_testable == False` or `ui_observable == False`)
       -> `UNTESTED` (`untested_reason="not_ui_observable"`, `needs_human_review=False`)
    2. No usable selector discovered by Agent 2 (`no_selector_found=True`)
       -> `UNTESTED` (`untested_reason="no_selector_found"`, `needs_human_review=False`)
    3. Critic loop did not converge (`final_state == "not_converged"` or critic rejected / missing)
       -> `UNTESTED` (`untested_reason="critic_not_converged"`, `needs_human_review=True`)
    4. Critic approved (`verdict == "APPROVE"`) and Probe `passed`
       -> `PASS`
    5. Critic approved (`verdict == "APPROVE"`) and Probe `assertion_failed` with `exception_type == "AssertionError"`
       -> `FAIL`
    6. Probe `runtime_error`, `timeout`, or non-AssertionError failure
       -> `ERROR`
    """
    if isinstance(condition, dict):
        is_testable = bool(condition.get("is_testable", condition.get("ui_observable", True)))
        untestable_reason_text = condition.get("untestable_reason") or "Requirement is not observable through the web UI."
        predicate_text = condition.get("predicate_text") or condition.get("predicate") or ""
    else:
        is_testable = condition.is_testable
        untestable_reason_text = condition.untestable_reason or "Requirement is not observable through the web UI."
        predicate_text = condition.predicate_text

    # 1. Not UI-observable (Agent 1 classification, e.g., REQ-09)
    if not is_testable:
        return StatusMappingResult(
            execution_status="UNTESTED",
            untested_reason="not_ui_observable",
            needs_human_review=False,
            audit_rationale=f"Not UI-observable: {untestable_reason_text}",
        )

    # 2. No selector found on target pages (Agent 2)
    if no_selector_found:
        return StatusMappingResult(
            execution_status="UNTESTED",
            untested_reason="no_selector_found",
            needs_human_review=False,
            audit_rationale=(
                f"No accessible ARIA selector could be resolved for condition predicate: '{predicate_text}'."
            ),
        )

    probe_obj = (
        ProbeResult.model_validate(probe)
        if isinstance(probe, dict)
        else probe
    )
    critic_obj = (
        CriticVerdict.model_validate(critic)
        if isinstance(critic, dict)
        else critic
    )

    # 3. Critic did not converge within <= 3 iterations (Agent 3)
    if (
        final_state == "not_converged"
        or critic_obj is None
        or critic_obj.verdict != "APPROVE"
    ):
        notes = critic_obj.critique_notes if critic_obj is not None else "No critic approval obtained."
        return StatusMappingResult(
            execution_status="UNTESTED",
            untested_reason="critic_not_converged",
            needs_human_review=True,
            audit_rationale=(
                f"Critic did not converge within the 3-iteration bound (flagged for human review). "
                f"Last critique: {notes}"
            ),
        )

    if probe_obj is None:
        return StatusMappingResult(
            execution_status="ERROR",
            untested_reason=None,
            needs_human_review=False,
            audit_rationale="Probe telemetry missing despite critic approval.",
        )

    # 4. PASS: Critic-approved script ran and its assertion held
    if probe_obj.outcome == "passed":
        return StatusMappingResult(
            execution_status="PASS",
            untested_reason=None,
            needs_human_review=False,
            audit_rationale=(
                f"Critic-approved test script passed ({probe_obj.duration_s:.2f}s) and assertion held. "
                f"{critic_obj.critique_notes}"
            ).strip(),
        )

    # 5. FAIL: Critic-approved script ran, selectors resolved, and AssertionError was raised
    if probe_obj.outcome == "assertion_failed" and (
        probe_obj.exception_type in (None, "AssertionError")
    ):
        return StatusMappingResult(
            execution_status="FAIL",
            untested_reason=None,
            needs_human_review=False,
            audit_rationale=(
                f"Critic-approved test assertion did not hold (AssertionError). "
                f"{critic_obj.critique_notes}"
            ).strip(),
        )

    # 6. ERROR: Script could not complete due to timeout, locator error, or runtime crash
    exc_label = probe_obj.exception_type or probe_obj.outcome
    return StatusMappingResult(
        execution_status="ERROR",
        untested_reason=None,
        needs_human_review=False,
        audit_rationale=(
            f"Test execution failed to complete cleanly ({probe_obj.outcome}: {exc_label}). "
            f"{critic_obj.critique_notes}"
        ).strip(),
    )
