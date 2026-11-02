"""Agent 4 — Verification & Report Synthesis Engine (Guide §7.3, §9 Agent 4)."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Union

from reqverify.graph.agent3_subgraph import Agent3Result
from reqverify.reports.confidence import LocatorTier, compute_overall_confidence
from reqverify.reports.status_mapper import derive_status
from reqverify.schemas.contracts import (
    CriticVerdict,
    ExtractedCondition,
    ProbeResult,
    RequirementVerificationResult,
)
from reqverify.schemas.reports import ReportManifest, VerificationSummary


def synthesize_condition_result(
    condition: Union[ExtractedCondition, dict],
    *,
    agent3_result: Optional[Union[Agent3Result, dict]] = None,
    no_selector_found: bool = False,
    verbatim_span_match: bool = True,
    locator_tier: Optional[LocatorTier] = None,
    test_script_ref: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    prober: Optional[Any] = None,
    reexecute_approved: bool = False,
) -> RequirementVerificationResult:
    """Synthesize a final RequirementVerificationResult for a single condition."""
    cond = (
        condition
        if isinstance(condition, ExtractedCondition)
        else ExtractedCondition.model_validate(condition)
    )

    probe_obj: Optional[ProbeResult] = None
    critic_obj: Optional[CriticVerdict] = None
    final_state: Optional[str] = None
    iterations: int = 0
    script_text: Optional[str] = None

    if isinstance(agent3_result, Agent3Result):
        final_state = agent3_result.final
        iterations = agent3_result.iterations
        script_text = agent3_result.script or None
        probe_obj = agent3_result.probe
        critic_obj = agent3_result.critic
    elif isinstance(agent3_result, dict):
        final_state = agent3_result.get("final")
        iterations = int(agent3_result.get("iterations", agent3_result.get("iteration", 0)))
        script_text = agent3_result.get("script") or None
        if agent3_result.get("probe") is not None:
            p = agent3_result["probe"]
            probe_obj = p if isinstance(p, ProbeResult) else ProbeResult.model_validate(p)
        if agent3_result.get("critic") is not None:
            c = agent3_result["critic"]
            critic_obj = c if isinstance(c, CriticVerdict) else CriticVerdict.model_validate(c)

    # Optional fresh-context re-execution for approved scripts (Guide §9 Agent 4)
    if (
        reexecute_approved
        and prober is not None
        and final_state == "approved"
        and script_text
        and cond.is_testable
        and not no_selector_found
    ):
        probe_obj = prober.probe(script_text, cond.condition_id, iterations or 1)

    mapping = derive_status(
        condition=cond,
        probe=probe_obj,
        critic=critic_obj,
        final_state=final_state,
        no_selector_found=no_selector_found,
    )

    confidence = compute_overall_confidence(
        status=mapping.execution_status,
        verbatim_span_match=verbatim_span_match,
        locator_tier=locator_tier,
        script=script_text,
        critic_iterations=max(1, iterations) if mapping.execution_status != "UNTESTED" else 0,
    )

    return RequirementVerificationResult(
        requirement_id=cond.source_requirement_id,
        condition_id=cond.condition_id,
        execution_status=mapping.execution_status,
        untested_reason=mapping.untested_reason,
        test_script_ref=test_script_ref,
        critic_iterations=iterations,
        overall_confidence=confidence,
        audit_rationale=mapping.audit_rationale,
        needs_human_review=mapping.needs_human_review,
        predicate_text=cond.predicate_text,
        source_span=cond.source_span,
        trace_path=probe_obj.trace_path if probe_obj else None,
        screenshot_path=screenshot_path,
        test_script=script_text,
        probe_outcome=probe_obj.outcome if probe_obj else None,
        exception_type=probe_obj.exception_type if probe_obj else None,
        stdout_tail=probe_obj.stdout_tail if probe_obj else "",
        critic_notes=critic_obj.critique_notes if critic_obj else "",
        duration_s=probe_obj.duration_s if probe_obj else 0.0,
    )


class VerificationAgent:
    """Agent 4: Orchestrates per-condition verdict synthesis and summary construction."""

    def __init__(self, run_id: str, prober: Optional[Any] = None) -> None:
        self.run_id = run_id
        self.prober = prober

    def verify_condition(
        self,
        condition: Union[ExtractedCondition, dict],
        *,
        agent3_result: Optional[Union[Agent3Result, dict]] = None,
        no_selector_found: bool = False,
        verbatim_span_match: bool = True,
        locator_tier: Optional[LocatorTier] = None,
        test_script_ref: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        reexecute_approved: bool = False,
    ) -> RequirementVerificationResult:
        """Synthesize verification verdict for one condition."""
        return synthesize_condition_result(
            condition,
            agent3_result=agent3_result,
            no_selector_found=no_selector_found,
            verbatim_span_match=verbatim_span_match,
            locator_tier=locator_tier,
            test_script_ref=test_script_ref,
            screenshot_path=screenshot_path,
            prober=self.prober,
            reexecute_approved=reexecute_approved,
        )

    def build_summary(
        self,
        results: Sequence[RequirementVerificationResult],
        manifest: Optional[ReportManifest] = None,
    ) -> VerificationSummary:
        """Assemble the complete VerificationSummary for JSON and HTML reporters."""
        effective_manifest = manifest or ReportManifest(
            run_id=self.run_id,
            total_duration_s=round(sum(r.duration_s for r in results), 3),
        )
        return VerificationSummary(
            run_id=self.run_id,
            manifest=effective_manifest,
            results=list(results),
        )
