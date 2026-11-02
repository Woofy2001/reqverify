"""Unit tests for Agent 4 HTML Audit Report Generator (Step 7.4)."""

from __future__ import annotations

from pathlib import Path

from reqverify.agents.verifier import VerificationAgent, synthesize_condition_result
from reqverify.graph.agent3_subgraph import Agent3Result
from reqverify.reports.html_reporter import render_html_report, write_html_report
from reqverify.schemas.contracts import ExtractedCondition, ProbeResult
from reqverify.schemas.probes import CriticDecision
from reqverify.schemas.reports import ReportManifest, VerificationSummary


def _build_mixed_summary(run_id: str = "run_html_test") -> VerificationSummary:
    cond_pass = ExtractedCondition(
        condition_id="REQ-01.1-11111111",
        document_hash="doc_hash_01",
        source_requirement_id="REQ-01",
        source_span="Valid credentials sign the user in and display the product catalog.",
        predicate_text="Signing in with valid credentials navigates to the catalog page.",
        is_testable=True,
        extraction_confidence=0.95,
        rationale="Atomic login success condition.",
    )
    a3_pass = Agent3Result(
        final="approved",
        iterations=1,
        script='def test_req01(page):\n    """REQ-01.1-11111111"""\n    page.goto("http://localhost:3000/login")\n',
        probe=ProbeResult(
            exit_code=0,
            outcome="passed",
            exception_type=None,
            stdout_tail="1 passed in 1.05s",
            duration_s=1.05,
            trace_path=f"traces/{run_id}/REQ-01.1-11111111_iter1.zip",
        ),
        critic=CriticDecision(
            verdict="APPROVE",
            assertion_validity_score=0.96,
            critique_notes="Clean assertion on catalog heading.",
            is_test_bug=False,
        ),
        assertion_reverted=False,
        untested_reason=None,
        needs_human_review=False,
    )

    cond_fail = ExtractedCondition(
        condition_id="REQ-03.2-22222222",
        document_hash="doc_hash_01",
        source_requirement_id="REQ-03",
        source_span="Entering SAVE10 subtracts 10% from the cart subtotal.",
        predicate_text="Applying SAVE10 reduces the displayed total by 10%.",
        is_testable=True,
        extraction_confidence=0.95,
        rationale="Atomic discount calculation condition.",
    )
    a3_fail = Agent3Result(
        final="approved",
        iterations=2,
        script='def test_req03(page):\n    """REQ-03.2-22222222"""\n    expect(page.get_by_role("status")).to_have_text("$90.00")\n',
        probe=ProbeResult(
            exit_code=1,
            outcome="assertion_failed",
            exception_type="AssertionError",
            stdout_tail="AssertionError: expected '$90.00' but got '$110.00'",
            duration_s=1.62,
            trace_path=f"traces/{run_id}/REQ-03.2-22222222_iter2.zip",
        ),
        critic=CriticDecision(
            verdict="APPROVE",
            assertion_validity_score=0.92,
            critique_notes="Test is valid; SUT adds 10% instead of subtracting.",
            is_test_bug=False,
        ),
        assertion_reverted=False,
        untested_reason=None,
        needs_human_review=False,
    )

    cond_untested_review = ExtractedCondition(
        condition_id="REQ-07.1-33333333",
        document_hash="doc_hash_01",
        source_requirement_id="REQ-07",
        source_span="Checkout step 2 validates shipping postal code format.",
        predicate_text="Invalid postal code blocks transition to checkout step 3.",
        is_testable=True,
        extraction_confidence=0.95,
        rationale="Atomic checkout validation condition.",
    )
    a3_not_converged = Agent3Result(
        final="not_converged",
        iterations=3,
        script='def test_req07(page):\n    """REQ-07.1-33333333"""\n    pass\n',
        probe=ProbeResult(
            exit_code=1,
            outcome="timeout",
            exception_type="TimeoutError",
            stdout_tail="TimeoutError: waiting for step 2 form",
            duration_s=5.0,
            trace_path=f"traces/{run_id}/REQ-07.1-33333333_iter3.zip",
        ),
        critic=CriticDecision(
            verdict="REJECT",
            assertion_validity_score=0.30,
            critique_notes="Did not reach step 2 form within 3 repair iterations.",
            suggested_refinement="Complete step 1 fields first.",
            is_test_bug=True,
        ),
        assertion_reverted=False,
        untested_reason="critic_not_converged",
        needs_human_review=True,
    )

    cond_backend = ExtractedCondition(
        condition_id="REQ-09.1-44444444",
        document_hash="doc_hash_01",
        source_requirement_id="REQ-09",
        source_span="Passwords must be hashed with bcrypt cost factor 12 in SQLite.",
        predicate_text="Stored password hashes use bcrypt cost factor 12.",
        is_testable=False,
        untestable_reason="Backend database storage format is not UI-observable",
        extraction_confidence=0.95,
        rationale="Backend security requirement.",
    )

    agent4 = VerificationAgent(run_id=run_id)
    results = [
        synthesize_condition_result(
            cond_pass,
            agent3_result=a3_pass,
            screenshot_path=f"traces/{run_id}/REQ-01.1-11111111.png",
        ),
        synthesize_condition_result(
            cond_fail,
            agent3_result=a3_fail,
            screenshot_path=f"traces/{run_id}/REQ-03.2-22222222.png",
        ),
        synthesize_condition_result(cond_untested_review, agent3_result=a3_not_converged),
        synthesize_condition_result(cond_backend),
    ]
    manifest = ReportManifest(
        run_id=run_id,
        model="claude-sonnet-5-5",
        effort="medium",
        app_url="http://localhost:3000",
        mutant_id="M06",
        document_hash="doc_hash_01",
        reqverify_commit="1707f6a",
        total_input_tokens=18500,
        total_output_tokens=62000,
        cost_estimate_usd=0.099,
        total_duration_s=8.72,
    )
    return agent4.build_summary(results=results, manifest=manifest)


def test_html_renders_without_errors(tmp_path: Path) -> None:
    """Asserts Jinja2 renders valid HTML string and writes report.html cleanly."""
    summary = _build_mixed_summary("run_render_ok")
    html = render_html_report(summary)

    assert html.startswith("<!DOCTYPE html>")
    assert "<html lang=\"en\">" in html
    assert "run_render_ok" in html
    assert "REQ-01.1-11111111" in html
    assert "REQ-03.2-22222222" in html
    assert "REQ-07.1-33333333" in html
    assert "REQ-09.1-44444444" in html

    report_path = write_html_report(summary, base_dir=tmp_path)
    assert report_path.exists()
    assert report_path == tmp_path / "run_render_ok" / "report.html"


def test_html_contains_trace_links() -> None:
    """Asserts presence of clickable links to .zip traces, trace.playwright.dev, and screenshots."""
    summary = _build_mixed_summary("run_trace_links")
    html = render_html_report(summary)

    assert "traces/run_trace_links/REQ-01.1-11111111_iter1.zip" in html
    assert "traces/run_trace_links/REQ-03.2-22222222_iter2.zip" in html
    assert "https://trace.playwright.dev/?trace=" in html
    assert "traces/run_trace_links/REQ-01.1-11111111.png" in html


def test_html_highlights_untested_needs_human_review() -> None:
    """Asserts needs_human_review=True conditions are highlighted with amber review indicator."""
    summary = _build_mixed_summary("run_human_review")
    html = render_html_report(summary)

    assert 'data-needs-human-review="true"' in html
    assert "needs-human-review-amber" in html
    assert "Needs Human Review" in html
    assert "critic_not_converged" in html
