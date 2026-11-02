"""Playwright visual & accessibility smoke tests for Agent 4 HTML Audit Report (Step 7.5)."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from reqverify.reports.html_reporter import write_html_report
from tests.test_html_reporter import _build_mixed_summary


def test_report_opens_in_browser(page: Page, tmp_path: Path) -> None:
    """Opens report.html via file:// URI in headless browser and asserts title, H1, and summary cards."""
    summary = _build_mixed_summary("test_run")
    report_path = write_html_report(summary, base_dir=tmp_path)
    file_uri = report_path.resolve().as_uri()

    page.goto(file_uri)

    assert "ReqVerify Audit Report — test_run" in page.title()
    assert page.locator("h1").count() == 1
    assert page.locator("h1").inner_text() == "Requirements Verification Report"

    # Verify summary cards
    assert page.get_by_test_id("card-total").inner_text().endswith("4")
    assert page.get_by_test_id("card-pass").inner_text().endswith("1")
    assert page.get_by_test_id("card-fail").inner_text().endswith("1")
    assert page.get_by_test_id("card-untested").inner_text().endswith("2")


def test_accordion_expansion_and_filtering(page: Page, tmp_path: Path) -> None:
    """Clicks condition summary row and asserts test script and trace links become visible, plus filter buttons."""
    summary = _build_mixed_summary("test_run_interactive")
    report_path = write_html_report(summary, base_dir=tmp_path)
    file_uri = report_path.resolve().as_uri()

    page.goto(file_uri)

    first_accordion = page.locator('details.condition-accordion[data-condition-id="REQ-01.1-11111111"]')
    details_panel = first_accordion.locator(".condition-details-panel")
    assert not details_panel.is_visible()

    # Click summary row to expand accordion
    first_accordion.locator("summary.condition-summary-row").click()
    assert details_panel.is_visible()

    # Verify test script code and trace links are visible inside expanded accordion
    code_block = first_accordion.locator("pre.code-block").first
    assert code_block.is_visible()
    assert "def test_req01(page):" in code_block.inner_text()

    trace_zip = first_accordion.get_by_test_id("trace-zip-link")
    trace_viewer = first_accordion.get_by_test_id("trace-viewer-link")
    assert trace_zip.is_visible()
    assert trace_viewer.is_visible()
    assert "traces/test_run_interactive/REQ-01.1-11111111_iter1.zip" in (trace_zip.get_attribute("href") or "")
    assert "https://trace.playwright.dev/?trace=" in (trace_viewer.get_attribute("href") or "")

    # Verify interactive status filter buttons
    fail_btn = page.locator('button.filter-btn[data-filter="FAIL"]')
    fail_btn.click()
    assert fail_btn.get_attribute("aria-pressed") == "true"
    assert not first_accordion.is_visible()
    fail_accordion = page.locator('details.condition-accordion[data-condition-id="REQ-03.2-22222222"]')
    assert fail_accordion.is_visible()

    # Verify Needs Human Review filter
    review_btn = page.locator('button.filter-btn[data-filter="REVIEW"]')
    review_btn.click()
    review_accordion = page.locator('details.condition-accordion[data-condition-id="REQ-07.1-33333333"]')
    assert review_accordion.is_visible()
    assert not fail_accordion.is_visible()
