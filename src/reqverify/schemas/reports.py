"""Pydantic v2 report schemas for Agent 4 (Verification & Reports)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, computed_field

from reqverify.schemas.contracts import (
    RequirementVerificationResult,
    Status,
    UntestedReason,
)


class ReportManifest(BaseModel):
    """Run metadata and token/timing provenance embedded in verification reports."""

    run_id: str
    model: str = "claude-sonnet-5-5"
    effort: str = "medium"
    app_url: str = "http://localhost:3000"
    mutant_id: str = "clean"
    document_hash: str = "unknown"
    reqverify_commit: str = "unknown"
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cost_estimate_usd: float = 0.0
    total_duration_s: float = 0.0
    generated_at_iso: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class VerificationSummary(BaseModel):
    """Complete machine-readable verification report output by Agent 4."""

    run_id: str
    manifest: ReportManifest
    results: List[RequirementVerificationResult] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_conditions(self) -> int:
        return len(self.results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"PASS": 0, "FAIL": 0, "ERROR": 0, "UNTESTED": 0}
        for r in self.results:
            counts[r.execution_status] = counts.get(r.execution_status, 0) + 1
        return counts

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mean_confidence(self) -> float:
        tested = [r.overall_confidence for r in self.results if r.execution_status != "UNTESTED"]
        if not tested:
            return 0.0
        return round(sum(tested) / len(tested), 4)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def human_review_count(self) -> int:
        return sum(1 for r in self.results if r.needs_human_review)


__all__ = [
    "ReportManifest",
    "RequirementVerificationResult",
    "Status",
    "UntestedReason",
    "VerificationSummary",
]
