"""Step 6.5: Agent 3 against the real TechStore SUT.

* ``test_prober_*`` need only a running TechStore (no API key): they prove FAIL vs ERROR classification
  (Spike S-4 / Guide §9 "Done when") using hand-written scripts against the real application.
* ``test_agent3_live_smoke_techstore`` is ``@pytest.mark.live``: one full generator-critic cycle with the real
  Claude API on a clean TechStore condition.
"""

from __future__ import annotations

import urllib.request

import pytest

from reqverify.agents.critic import TestCritic
from reqverify.agents.explorer import AppExplorerAgent
from reqverify.agents.generator import TestGenerator
from reqverify.agents.prober import TestProber
from reqverify.graph.agent3_subgraph import run_agent3
from reqverify.llm.client import LLMClient
from reqverify.schemas.contracts import ExtractedCondition

TECHSTORE_BASE_URL = "http://localhost:3000"


def _reachable(url: str = TECHSTORE_BASE_URL) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/login", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


requires_techstore = pytest.mark.skipif(not _reachable(), reason=f"TechStore not reachable at {TECHSTORE_BASE_URL}")

HEADING_PASS = '''
from playwright.sync_api import Page, expect

def test_heading(page: Page, base_url: str):
    page.goto(f"{base_url}/login")
    expect(page.get_by_role("heading", name="Sign in to TechStore", exact=True)).to_be_visible()
'''

HEADING_WRONG_EXPECTATION = '''
from playwright.sync_api import Page, expect

def test_heading(page: Page, base_url: str):
    page.goto(f"{base_url}/login")
    expect(page.get_by_role("heading", name="Sign in to TechStore", exact=True)).to_have_text("Totally different title")
'''

BAD_LOCATOR = '''
from playwright.sync_api import Page, expect

def test_heading(page: Page, base_url: str):
    page.goto(f"{base_url}/login")
    expect(page.get_by_role("button", name="Does not exist", exact=True)).to_be_visible()
'''

SELF_CONTAINED_LOGIN = '''
from playwright.sync_api import Page, expect

def test_login_with_seeded_user(page: Page, base_url: str, test_user):
    page.goto(f"{base_url}/login")
    page.get_by_role("textbox", name="Email address", exact=True).fill(test_user["email"])
    page.get_by_role("textbox", name="Password", exact=True).fill(test_user["password"])
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page).not_to_have_url(f"{base_url}/login")
'''


@pytest.fixture
def prober(tmp_path):
    return TestProber(TECHSTORE_BASE_URL, run_id="p06-sut", traces_root=tmp_path / "traces", timeout_s=60)


@requires_techstore
def test_prober_passes_correct_script_on_real_techstore(prober):
    assert prober.probe(HEADING_PASS, "C-LIVE-1").outcome == "passed"


@requires_techstore
def test_prober_classifies_wrong_expectation_as_fail_candidate(prober):
    r = prober.probe(HEADING_WRONG_EXPECTATION, "C-LIVE-2")
    assert r.outcome == "assertion_failed" and r.exception_type == "AssertionError"


@requires_techstore
def test_prober_classifies_unresolvable_locator_as_error_not_fail(prober):
    assert prober.probe(BAD_LOCATOR, "C-LIVE-3").outcome == "runtime_error"


@requires_techstore
def test_prober_self_contained_login_uses_config_credentials(prober):
    r = prober.probe(SELF_CONTAINED_LOGIN, "C-LIVE-4")
    assert r.outcome == "passed", r.stdout_tail
    assert r.trace_path and r.trace_path.endswith(".zip")


@pytest.mark.live
@requires_techstore
def test_agent3_live_smoke_techstore(tmp_path):
    """One real generator-critic cycle on a clean TechStore condition terminates with approval."""
    selector_map = AppExplorerAgent(base_url=TECHSTORE_BASE_URL).explore(routes=["/login"], headless=True)
    condition = ExtractedCondition(
        source_requirement_id="REQ-LIVE",
        source_span="The login page shows a Sign in button",
        predicate_text='The login page displays a button with the accessible name "Sign in"',
        is_testable=True,
        extraction_confidence=0.99,
        rationale="Single observable control on the login page.",
        condition_id="REQ-LIVE.1-00000000",
        document_hash="0" * 64,
    )
    llm = LLMClient(db_path=str(tmp_path / "cache.sqlite"), run_id="p06-live-smoke")
    result = run_agent3(
        condition,
        selector_map,
        generator=TestGenerator(llm),
        prober=TestProber(TECHSTORE_BASE_URL, run_id="p06-live-smoke", traces_root=tmp_path / "traces"),
        critic=TestCritic(llm),
    )
    assert result.final == "approved", (result.critic.critique_notes, result.probe.stdout_tail)
    assert result.iterations <= 3
    assert result.probe.outcome == "passed"
