import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def classify_probe_exception(exc_type_name: str | None, exc_message: str | None = None) -> str:
    """Classify probe exception into outcome categories matching Guide §7.3."""
    if exc_type_name is None:
        return "passed"
    if exc_type_name == "AssertionError":
        return "assertion_failed"
    if exc_type_name in ("TimeoutError", "PlaywrightTimeoutError"):
        return "timeout"
    return "runtime_error"

def test_spike_s4_assertion_failure_classified_as_defect():
    """AssertionError (from expect(...) mismatch) is classified as assertion_failed."""
    outcome = classify_probe_exception("AssertionError", "Expected 'Login' but received 'Welcome'")
    assert outcome == "assertion_failed"

def test_spike_s4_timeout_failure_classified_as_runtime_error():
    """Playwright TimeoutError (selector not found / network timeout) is classified as timeout."""
    outcome = classify_probe_exception("TimeoutError", "Timeout 30000ms exceeded waiting for locator")
    assert outcome == "timeout"

def test_spike_s4_playwright_specific_timeout():
    """PlaywrightTimeoutError exception typename correctly classifies as timeout."""
    outcome = classify_probe_exception(PlaywrightTimeoutError.__name__, "Timeout 5000ms exceeded")
    assert outcome == "timeout"

def test_spike_s4_runtime_error_classified():
    """Uncaught syntax or type errors classify as runtime_error."""
    outcome = classify_probe_exception("TypeError", "NoneType has no attribute 'click'")
    assert outcome == "runtime_error"

def test_spike_s4_successful_execution():
    """Absence of exception classifies as passed."""
    outcome = classify_probe_exception(None)
    assert outcome == "passed"
