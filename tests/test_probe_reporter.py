"""Step 6.2: pytest telemetry plugin + subprocess prober (Spike S-4, NFR-05).

These are real integration tests: the prober runs pytest in a subprocess with real Chromium against
inline HTML (``page.set_content``), so exception classification is verified against Playwright itself.
"""

from __future__ import annotations

import pytest

from reqverify.agents.prober import TestProber, build_child_env
from reqverify.safety.ast_validator import ScriptSafetyViolation

HTML = "<h1>Welcome</h1><button>Go</button>"

PASSING = f'''
from playwright.sync_api import Page, expect

def test_ok(page: Page):
    page.set_content("{HTML}")
    expect(page.get_by_role("heading", name="Welcome")).to_be_visible(timeout=2000)
'''

ASSERTION_FAILS = f'''
from playwright.sync_api import Page, expect

def test_mismatch(page: Page):
    page.set_content("{HTML}")
    expect(page.get_by_role("heading")).to_have_text("Goodbye", timeout=1000)
'''

LOCATOR_NEVER_RESOLVES_VIA_EXPECT = f'''
from playwright.sync_api import Page, expect

def test_missing(page: Page):
    page.set_content("{HTML}")
    expect(page.get_by_role("button", name="Nope", exact=True)).to_be_visible(timeout=1000)
'''

ACTION_TIMEOUT = f'''
from playwright.sync_api import Page

def test_click_missing(page: Page):
    page.set_content("{HTML}")
    page.get_by_role("button", name="Nope", exact=True).click(timeout=800)
'''

PYTHON_CRASH = f'''
from playwright.sync_api import Page

def test_crash(page: Page):
    page.set_content("{HTML}")
    x = None
    x.click()
'''

INFINITE_LOOP = '''
def test_hang(page):
    while True:
        pass
'''

USES_CREDENTIAL_FIXTURE = f'''
from playwright.sync_api import Page, expect

def test_cred(page: Page, test_user):
    page.set_content("<input aria-label='Email address'>")
    page.get_by_label("Email address").fill(test_user["email"])
    expect(page.get_by_label("Email address")).to_have_value("probe@example.com", timeout=1000)
'''


@pytest.fixture
def prober(tmp_path):
    return TestProber(
        base_url="http://localhost:3000",
        run_id="unit",
        traces_root=tmp_path / "traces",
        timeout_s=45,
        credentials={"test_user": {"email": "probe@example.com", "password": "x"}},
    )


def test_plugin_classifies_pass(prober):
    r = prober.probe(PASSING, "C-01.1-aaaa")
    assert r.outcome == "passed"
    assert r.exit_code == 0
    assert r.exception_type is None


def test_plugin_classifies_assertion_error(prober):
    r = prober.probe(ASSERTION_FAILS, "C-01.2-bbbb")
    assert r.outcome == "assertion_failed"
    assert r.exception_type == "AssertionError"
    assert "Goodbye" in r.stdout_tail


def test_expect_on_unresolvable_locator_is_runtime_error_not_defect(prober):
    """§7.3: FAIL requires that selectors resolved. expect() on a locator that never matched is a test bug."""
    r = prober.probe(LOCATOR_NEVER_RESOLVES_VIA_EXPECT, "C-01.3-cccc")
    assert r.outcome == "runtime_error"


def test_plugin_classifies_timeout_error(prober):
    r = prober.probe(ACTION_TIMEOUT, "C-01.4-dddd")
    assert r.outcome == "runtime_error"
    assert r.exception_type == "TimeoutError"


def test_plugin_classifies_python_crash(prober):
    r = prober.probe(PYTHON_CRASH, "C-01.5-eeee")
    assert r.outcome == "runtime_error"
    assert r.exception_type == "AttributeError"


def test_prober_timeout_guard(tmp_path):
    p = TestProber("http://localhost:3000", run_id="unit", traces_root=tmp_path / "t", timeout_s=4)
    r = p.probe(INFINITE_LOOP, "C-01.6-ffff")
    assert r.outcome == "timeout"
    assert r.duration_s < 20


def test_prober_saves_playwright_trace(prober, tmp_path):
    r = prober.probe(PASSING, "C-02.1-1111")
    assert r.trace_path is not None and r.trace_path.endswith(".zip")
    assert (tmp_path / "traces" / "unit" / "C-02.1-1111").exists()
    assert list((tmp_path / "traces" / "unit" / "C-02.1-1111").rglob("trace.zip"))


def test_prober_provides_credential_fixture_from_config_not_prompt(prober):
    r = prober.probe(USES_CREDENTIAL_FIXTURE, "C-02.2-2222")
    assert r.outcome == "passed", r.stdout_tail


def test_prober_rejects_unsafe_script_before_execution(prober):
    with pytest.raises(ScriptSafetyViolation):
        prober.probe("import os\n\ndef test_x(page):\n    pass\n", "C-03.1-3333")


def test_child_env_strips_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    env = build_child_env(credentials={})
    assert "ANTHROPIC_API_KEY" not in env
