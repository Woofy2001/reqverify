"""Unit tests for Agent 4 JSON Report Generator and Verifier (Step 7.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reqverify.agents.verifier import VerificationAgent, synthesize_condition_result
from reqverify.graph.agent3_subgraph import Agent3Result
from reqverify.reports.json_reporter import load_json_report, serialize_json_report, write_json_report
from reqverify.schemas.contracts import ExtractedCondition, ProbeResult
from reqverify.schemas.probes import CriticDecision
from reqverify.schemas.reports import ReportManifest, RequirementVerificationResult, VerificationSummary


def _make_24_conditions() -> list[ExtractedCondition]:
    conditions: list[ExtractedCondition] = []
    for i in range(1, 25):
        req_id = "REQ-09" if i == 15 else f"REQ-{(i % 10) + 1:02d}"
        is_testable = i != 15
        conditions.append(
            ExtractedCondition(
                condition_id=f"{req_id}.{i}-abcdef{i:02d}",
                document_hash="sha256_doc_hash_24",
                source_requirement_id=req_id,
                source_span=f"Verbatim requirement sentence number {i} from specification.",
                predicate_text=f"Condition {i} observable behaviour holds in UI.",
                is_testable=is_testable,
                untestable_reason=None if is_testable else "Backend-only audit log persistence",
                extraction_confidence=0.95,
                rationale=f"Atomic condition {i} extracted from {req_id}.",
            )
        )
    return conditions


def _make_sample_summary(run_id: str = "run_test_json_01") -> VerificationSummary:
    conditions = _make_24_conditions()
    agent4 = VerificationAgent(run_id=run_id)
    results: list[RequirementVerificationResult] = []

    for idx, cond in enumerate(conditions):
        if not cond.is_testable:
            res = synthesize_condition_result(cond)
        elif idx == 3:
            # Simulate a FAIL verdict
            a3 = Agent3Result(
                final="approved",
                iterations=1,
                script='def test_cond(page):\n    page.get_by_role("button", name="Apply").click()\n',
                probe=ProbeResult(
                    exit_code=1,
                    outcome="assertion_failed",
                    exception_type="AssertionError",
                    stdout_tail="AssertionError: expected discount to subtract 10%",
                    duration_s=1.45,
                    trace_path=f"traces/{run_id}/{cond.condition_id}_iter1.zip",
                ),
                critic=CriticDecision(
                    verdict="APPROVE",
                    assertion_validity_score=0.94,
                    critique_notes="Test is sound; discount calculation is inverted.",
                    is_test_bug=False,
                ),
                assertion_reverted=False,
                untested_reason=None,
                needs_human_review=False,
            )
            res = synthesize_condition_result(cond, agent3_result=a3)
        else:
            # Simulate a PASS verdict
            a3 = Agent3Result(
                final="approved",
                iterations=1,
                script='def test_cond(page):\n    page.get_by_role("button", name="Sign in", exact=True).click()\n',
                probe=ProbeResult(
                    exit_code=0,
                    outcome="passed",
                    exception_type=None,
                    stdout_tail="1 passed in 0.95s",
                    duration_s=0.95,
                    trace_path=f"traces/{run_id}/{cond.condition_id}_iter1.zip",
                ),
                critic=CriticDecision(
                    verdict="APPROVE",
                    assertion_validity_score=0.96,
                    critique_notes="Assertion accurately verifies the predicate.",
                    is_test_bug=False,
                ),
                assertion_reverted=False,
                untested_reason=None,
                needs_human_review=False,
            )
            res = synthesize_condition_result(cond, agent3_result=a3)
        results.append(res)

    manifest = ReportManifest(
        run_id=run_id,
        model="claude-sonnet-5-5",
        effort="medium",
        app_url="http://localhost:3000",
        mutant_id="M06",
        document_hash="sha256_doc_hash_24",
        reqverify_commit="1707f6a",
        total_input_tokens=42000,
        total_output_tokens=15000,
        cost_estimate_usd=0.234,
        total_duration_s=28.4,
    )
    return agent4.build_summary(results=results, manifest=manifest)


def test_json_schema_compliance(tmp_path: Path) -> None:
    """Validates serialized JSON against VerificationSummary Pydantic model."""
    summary = _make_sample_summary("run_schema_check")
    out_path = write_json_report(summary, base_dir=tmp_path)

    assert out_path.exists()
    assert out_path == tmp_path / "run_schema_check" / "results.json"

    raw_text = out_path.read_text(encoding="utf-8")
    parsed_dict = json.loads(raw_text)

    reloaded = load_json_report(out_path)
    assert isinstance(reloaded, VerificationSummary)
    assert reloaded.run_id == "run_schema_check"
    assert reloaded.manifest.mutant_id == "M06"
    assert reloaded.manifest.total_input_tokens == 42000
    assert parsed_dict["status_counts"] == {"PASS": 22, "FAIL": 1, "ERROR": 0, "UNTESTED": 1}


def test_json_contains_all_conditions(tmp_path: Path) -> None:
    """Asserts all 24 conditions are present in output with intact IDs, statuses, and confidences."""
    summary = _make_sample_summary("run_24_conds")
    json_str = serialize_json_report(summary)
    data = json.loads(json_str)

    assert data["total_conditions"] == 24
    assert len(data["results"]) == 24

    untested = [r for r in data["results"] if r["execution_status"] == "UNTESTED"]
    assert len(untested) == 1
    assert untested[0]["requirement_id"] == "REQ-09"
    assert untested[0]["untested_reason"] == "not_ui_observable"
    assert untested[0]["overall_confidence"] == 0.0

    failed = [r for r in data["results"] if r["execution_status"] == "FAIL"]
    assert len(failed) == 1
    assert failed[0]["overall_confidence"] == pytest.approx(0.95)
    assert failed[0]["trace_path"].endswith(".zip")
