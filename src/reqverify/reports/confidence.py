"""Frozen mathematical confidence formula (Invariant D12, Step 7.2).

Formula:
    overall_confidence = 0.0                                              if status == "UNTESTED"
    overall_confidence = min(1.0, max(0.0, c_extraction * c_locator * c_critic))  otherwise

Component tiers:
    - c_extraction: 0.95 (verbatim span match) or 0.70 (fuzzy match)
    - c_locator:    1.00 (unique exact role+name), 0.85 (parent-scoped), 0.70 (.nth index)
    - c_critic:     1.00 (iteration 1 approval), 0.85 (iteration 2), 0.70 (iteration >= 3)
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from reqverify.schemas.contracts import Status

LocatorTier = Literal["exact", "parent_scoped", "nth"]

_CHAINED_GET_BY_ROLE_RE = re.compile(r"get_by_role\([^)]*\)\s*\.\s*get_by_role\(")


def extraction_tier_score(verbatim_span_match: bool = True) -> float:
    """Return deterministic extraction confidence factor (0.95 verbatim, 0.70 fuzzy)."""
    return 0.95 if verbatim_span_match else 0.70


def locator_tier_score(locator_tier: LocatorTier = "exact") -> float:
    """Return deterministic locator disambiguation confidence factor."""
    if locator_tier == "exact":
        return 1.0
    if locator_tier == "parent_scoped":
        return 0.85
    if locator_tier == "nth":
        return 0.70
    raise ValueError(f"Unknown locator_tier: {locator_tier!r}")


def critic_iteration_score(critic_iterations: int = 1) -> float:
    """Return deterministic critic iteration penalty factor."""
    if critic_iterations <= 0:
        return 0.0
    if critic_iterations == 1:
        return 1.0
    if critic_iterations == 2:
        return 0.85
    return 0.70


def infer_locator_tier_from_script(script: Optional[str]) -> LocatorTier:
    """Inspect a generated pytest-playwright script to determine its weakest locator tier."""
    if not script:
        return "exact"
    if ".nth(" in script:
        return "nth"
    if _CHAINED_GET_BY_ROLE_RE.search(script) or ".filter(" in script:
        return "parent_scoped"
    return "exact"


def compute_overall_confidence(
    status: Status,
    *,
    verbatim_span_match: bool = True,
    locator_tier: Optional[LocatorTier] = None,
    script: Optional[str] = None,
    critic_iterations: int = 1,
    c_extraction: Optional[float] = None,
    c_locator: Optional[float] = None,
    c_critic: Optional[float] = None,
) -> float:
    """Compute calibrated overall_confidence in [0.0, 1.0] using the frozen D12 formula."""
    if status == "UNTESTED":
        return 0.0

    resolved_tier: LocatorTier = (
        locator_tier
        if locator_tier is not None
        else infer_locator_tier_from_script(script)
    )

    ext_val = c_extraction if c_extraction is not None else extraction_tier_score(verbatim_span_match)
    loc_val = c_locator if c_locator is not None else locator_tier_score(resolved_tier)
    crit_val = c_critic if c_critic is not None else critic_iteration_score(critic_iterations)

    if ext_val < 0.0 or loc_val < 0.0 or crit_val < 0.0:
        return 0.0

    product = ext_val * loc_val * crit_val
    clamped = min(1.0, max(0.0, product))
    return round(clamped, 4)
