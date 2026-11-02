"""Unit tests for the frozen mathematical confidence formula (Invariant D12, Step 7.2)."""

from __future__ import annotations

import pytest

from reqverify.reports.confidence import (
    compute_overall_confidence,
    critic_iteration_score,
    extraction_tier_score,
    infer_locator_tier_from_script,
    locator_tier_score,
)


def test_confidence_bounds() -> None:
    """Asserts 0.0 <= confidence <= 1.0 across all tier combinations and edge cases."""
    for status in ("PASS", "FAIL", "ERROR", "UNTESTED"):
        for verbatim in (True, False):
            for loc_tier in ("exact", "parent_scoped", "nth"):
                for iters in (0, 1, 2, 3, 5):
                    score = compute_overall_confidence(
                        status=status,
                        verbatim_span_match=verbatim,
                        locator_tier=loc_tier,
                        critic_iterations=iters,
                    )
                    assert 0.0 <= score <= 1.0

    # Even if overridden component scores exceed 1.0 or are negative, clamp holds
    assert compute_overall_confidence(
        status="PASS",
        c_extraction=1.5,
        c_locator=1.2,
        c_critic=1.1,
    ) == 1.0
    assert compute_overall_confidence(
        status="PASS",
        c_extraction=-0.5,
        c_locator=1.0,
        c_critic=1.0,
    ) == 0.0


def test_critic_iteration_penalty() -> None:
    """Confidence decreases monotonically with increasing critic iterations (1 -> 2 -> 3)."""
    c1 = compute_overall_confidence(
        status="PASS",
        verbatim_span_match=True,
        locator_tier="exact",
        critic_iterations=1,
    )
    c2 = compute_overall_confidence(
        status="PASS",
        verbatim_span_match=True,
        locator_tier="exact",
        critic_iterations=2,
    )
    c3 = compute_overall_confidence(
        status="PASS",
        verbatim_span_match=True,
        locator_tier="exact",
        critic_iterations=3,
    )

    assert c1 > c2 > c3 > 0.0
    assert c1 == pytest.approx(0.95 * 1.0 * 1.0)
    assert c2 == pytest.approx(0.95 * 1.0 * 0.85)
    assert c3 == pytest.approx(0.95 * 1.0 * 0.70)


def test_untested_confidence_zero() -> None:
    """UNTESTED conditions always receive overall_confidence == 0.0 regardless of component scores."""
    score = compute_overall_confidence(
        status="UNTESTED",
        verbatim_span_match=True,
        locator_tier="exact",
        critic_iterations=1,
    )
    assert score == 0.0


def test_component_tier_values_and_script_inference() -> None:
    """Verify exact tier constants for extraction, locator, and critic iterations."""
    assert extraction_tier_score(True) == 0.95
    assert extraction_tier_score(False) == 0.70

    assert locator_tier_score("exact") == 1.0
    assert locator_tier_score("parent_scoped") == 0.85
    assert locator_tier_score("nth") == 0.70

    assert critic_iteration_score(1) == 1.0
    assert critic_iteration_score(2) == 0.85
    assert critic_iteration_score(3) == 0.70

    # Script inference
    script_exact = 'page.get_by_role("button", name="Sign in", exact=True).click()'
    script_scoped = 'page.get_by_role("region", name="Cart").get_by_role("button", name="Remove").click()'
    script_nth = 'page.get_by_role("button", name="Add to cart").nth(1).click()'

    assert infer_locator_tier_from_script(script_exact) == "exact"
    assert infer_locator_tier_from_script(script_scoped) == "parent_scoped"
    assert infer_locator_tier_from_script(script_nth) == "nth"
