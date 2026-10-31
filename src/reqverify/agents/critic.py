"""Agent 3 (part 2): Test Critic (Guide §9 Agent 3 Critic, Invariants D6/D7).

The critic judges a generated script using *execution evidence* (the probe) rather than re-reading its own
output (Huang et al., 2024; Gou et al., 2024). It must separate a **test bug** (bad locator, missing wait,
wrong navigation -> repairable) from an **application defect** (sound test, assertion legitimately failing ->
approved so Agent 4 reports FAIL). The LLM's verdict is then reconciled with the probe in code so that a
script which never completed can never be approved, and a low-validity assertion can never pass review.

The critic is never shown mutant metadata or any second SUT variant (D6).
"""

from __future__ import annotations

from typing import Optional, Union

from reqverify.llm.client import LLMClient
from reqverify.llm.fake_client import FakeLLMClient
from reqverify.schemas.contracts import ExtractedCondition, ProbeResult
from reqverify.schemas.probes import CriticDecision

ASSERTION_VALIDITY_THRESHOLD = 0.5
SNAPSHOT_EXCERPT_CHARS = 6000

CRITIC_SYSTEM_PROMPT = (
    "You are a strict QA reviewer of ONE generated pytest-playwright test.\n\n"
    "You receive the condition under test, the script, the real execution result (probe) and an excerpt of the "
    "page's accessibility snapshot. Decide:\n"
    "1. assertion_validity_score (0-1): does the script's final assertion check exactly what predicate_text "
    "states, no more and no less? Penalise partial matches, wrong elements, missing steps or vacuous checks.\n"
    "2. is_test_bug: TRUE if the failure is caused by the test (locator not found/ambiguous, missing wait, wrong "
    "navigation, unsafe code). FALSE if the test is sound and the application genuinely does not satisfy the "
    "condition, or the test passed.\n"
    "3. verdict: APPROVE only if the assertion is valid AND the outcome is trustworthy (a passing test, or a "
    "sound test whose assertion legitimately failed). Otherwise REJECT.\n"
    "4. suggested_refinement: when rejecting, say precisely how to repair locators, waits or navigation. "
    "NEVER suggest changing or loosening the expected value or matcher of the assertion.\n"
    "Keep critique_notes to one or two short sentences."
)


def build_critic_prompt(
    condition: ExtractedCondition, script: str, probe: ProbeResult, snapshot_excerpt: str
) -> str:
    return "\n".join(
        [
            f"condition_id: {condition.condition_id}",
            f'predicate_text: "{condition.predicate_text}"',
            f'source_span: "{condition.source_span}"',
            "",
            "Script:",
            "```python",
            script,
            "```",
            "",
            f"Probe result: outcome={probe.outcome} exception_type={probe.exception_type} "
            f"exit_code={probe.exit_code} duration_s={probe.duration_s:.2f}",
            f"Probe output tail:\n{probe.stdout_tail[-1500:]}",
            "",
            "Accessibility snapshot excerpt:",
            snapshot_excerpt[:SNAPSHOT_EXCERPT_CHARS],
        ]
    )


def reconcile(decision: CriticDecision, probe: ProbeResult) -> CriticDecision:
    """Deterministically align the LLM judgement with execution evidence."""
    verdict, is_bug, refine = decision.verdict, decision.is_test_bug, decision.suggested_refinement
    valid = decision.assertion_validity_score >= ASSERTION_VALIDITY_THRESHOLD

    if probe.outcome in ("runtime_error", "timeout"):
        verdict, is_bug = "REJECT", True  # a script that never completed is never trustworthy evidence
    elif probe.outcome == "assertion_failed":
        verdict = "APPROVE" if (not is_bug and valid and verdict == "APPROVE") else "REJECT"
    else:  # passed: approve only a valid, non-buggy assertion that the LLM also approved
        approved = valid and not is_bug and verdict == "APPROVE"
        verdict = "APPROVE" if approved else "REJECT"

    if verdict == "REJECT" and not refine:
        refine = (
            f"The probe ended with {probe.outcome} ({probe.exception_type or 'no exception'}). Repair locators, "
            "waits or navigation using only the listed locators; keep the assertion unchanged."
        )
    return decision.model_copy(update={"verdict": verdict, "is_test_bug": is_bug, "suggested_refinement": refine})


class TestCritic:
    """Execution-grounded critic producing a reconciled :class:`CriticDecision`."""

    __test__ = False  # not a pytest test class

    def __init__(self, llm_client: Union[LLMClient, FakeLLMClient]):
        self.llm_client = llm_client

    def review(
        self,
        condition: Union[ExtractedCondition, dict],
        script: str,
        probe: Union[ProbeResult, dict],
        snapshot_excerpt: str = "",
    ) -> CriticDecision:
        cond = condition if isinstance(condition, ExtractedCondition) else ExtractedCondition.model_validate(condition)
        probe_m = probe if isinstance(probe, ProbeResult) else ProbeResult.model_validate(probe)
        decision, _meta = self.llm_client.parse(
            system=CRITIC_SYSTEM_PROMPT,
            user=build_critic_prompt(cond, script, probe_m, snapshot_excerpt),
            schema=CriticDecision,
        )
        return reconcile(decision, probe_m)

    @staticmethod
    def reject_without_review(reason: str) -> CriticDecision:
        """Deterministic REJECT when there is nothing meaningful to send to the LLM (no script / unsafe script)."""
        return CriticDecision(
            verdict="REJECT",
            assertion_validity_score=0.0,
            critique_notes=reason[:500],
            suggested_refinement=f"{reason[:400]} Produce a single safe test that ends with an expect(...) assertion.",
            is_test_bug=True,
        )
