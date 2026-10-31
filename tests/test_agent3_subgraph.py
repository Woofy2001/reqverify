"""Step 6.4: Critic + Agent 3 LangGraph subgraph (Invariant D8, NFR-03, Guide §9-§10)."""

from __future__ import annotations

import pytest

from reqverify.agents.critic import TestCritic
from reqverify.agents.generator import TestGenerator
from reqverify.graph.agent3_subgraph import MAX_CRITIC_ITERS, build_agent3, route, run_agent3
from reqverify.llm.fake_client import FakeLLMClient
from reqverify.safety.ast_validator import ScriptSafetyViolation
from reqverify.schemas.contracts import ExtractedCondition, ProbeResult
from reqverify.schemas.probes import CriticDecision, GeneratedTest
from reqverify.schemas.selectors import PageSnapshot, SelectorMap, UIElementSelector

CID = "REQ-02.1-ab12cd34"
CONDITION = ExtractedCondition(
    source_requirement_id="REQ-02",
    source_span='an alert stating "Invalid credentials" must appear',
    predicate_text='Failed login displays an alert with text "Invalid credentials"',
    is_testable=True,
    extraction_confidence=0.95,
    rationale="Single observable error message after failed login.",
    condition_id=CID,
    document_hash="0" * 64,
)
SELECTOR_MAP = SelectorMap(
    base_url="http://localhost:3000",
    pages={
        "/login": PageSnapshot(
            route="/login", title="Login",
            raw_aria_tree='- heading "Sign in"\n- textbox "Email address"\n- alert',
            elements=[UIElementSelector(
                element_id="e1", role="alert", accessible_name="",
                locator_recipe='page.get_by_role("alert")', page_route="/login")],
        )
    },
)


def script(locator='page.get_by_role("alert")', expected="Invalid credentials"):
    return (
        "from playwright.sync_api import Page, expect\n\n"
        "def test_a(page: Page, base_url: str):\n"
        f'    """{CID}: alert."""\n'
        '    page.goto(f"{base_url}/login")\n'
        f'    expect({locator}).to_have_text("{expected}")\n'
    )


def probe_result(outcome="passed", exc=None, tail="") -> ProbeResult:
    return ProbeResult(exit_code=0 if outcome == "passed" else 1, outcome=outcome,
                       exception_type=exc, stdout_tail=tail, duration_s=0.5)


def decision(verdict="APPROVE", score=0.9, bug=False, refine=None, notes="ok") -> CriticDecision:
    return CriticDecision(verdict=verdict, assertion_validity_score=score, critique_notes=notes,
                          suggested_refinement=refine, is_test_bug=bug)


class StubProber:
    """Scripted prober: no browser, returns canned ProbeResults (or raises a canned exception)."""

    def __init__(self, *results):
        self.results = list(results)
        self.calls: list[tuple[str, int]] = []

    def probe(self, script_text, condition_id, iteration=1):
        self.calls.append((condition_id, iteration))
        item = self.results[min(len(self.calls) - 1, len(self.results) - 1)]
        if isinstance(item, Exception):
            raise item
        return item


def wire(gen_scripts, probes, decisions, max_iters=MAX_CRITIC_ITERS):
    fake = FakeLLMClient()
    fake.register_sequence(GeneratedTest, [GeneratedTest(script=s) for s in gen_scripts])
    fake.register_sequence(CriticDecision, decisions)
    prober = StubProber(*probes)
    gen, critic = TestGenerator(fake), TestCritic(fake)
    return fake, prober, gen, critic


def run(gen_scripts, probes, decisions):
    fake, prober, gen, critic = wire(gen_scripts, probes, decisions)
    result = run_agent3(CONDITION, SELECTOR_MAP, generator=gen, prober=prober, critic=critic)
    return result, fake, prober


def count(fake, schema):
    return sum(1 for c in fake.call_history if c["schema"] is schema)


# ------------------------------------------------------------------------------------ router ----
def test_route_approve_wins_even_at_cap():
    assert route({"critic": {"verdict": "APPROVE"}, "iteration": 3}) == "approved"


def test_route_regenerates_below_cap_and_stops_at_cap():
    assert route({"critic": {"verdict": "REJECT"}, "iteration": 2}) == "generate"
    assert route({"critic": {"verdict": "REJECT"}, "iteration": 3}) == "not_converged"


# ------------------------------------------------------------------------------------ critic ----
def _review(probe, dec):
    fake = FakeLLMClient()
    fake.register_response(CriticDecision, dec)
    return TestCritic(fake).review(CONDITION, script(), probe, "snapshot excerpt"), fake


def test_critic_distinguishes_app_defect_from_test_bug():
    out, _ = _review(probe_result("assertion_failed", "AssertionError", "Expected Invalid credentials"),
                     decision("APPROVE", 0.9, bug=False))
    assert out.verdict == "APPROVE" and out.is_test_bug is False


def test_critic_rejects_assertion_failure_diagnosed_as_test_bug():
    out, _ = _review(probe_result("assertion_failed", "AssertionError"), decision("APPROVE", 0.9, bug=True))
    assert out.verdict == "REJECT"
    assert out.suggested_refinement


@pytest.mark.parametrize("outcome", ["runtime_error", "timeout"])
def test_critic_cannot_approve_a_script_that_never_completed(outcome):
    out, _ = _review(probe_result(outcome, "TimeoutError"), decision("APPROVE", 0.95, bug=False))
    assert out.verdict == "REJECT" and out.is_test_bug is True
    assert out.suggested_refinement


def test_critic_rejects_low_validity_even_if_probe_passed():
    out, _ = _review(probe_result("passed"), decision("APPROVE", 0.3))
    assert out.verdict == "REJECT"


def test_critic_keeps_llm_rejection_when_assertion_does_not_match_predicate():
    out, _ = _review(probe_result("passed"), decision("REJECT", 0.2, refine="assert the alert text"))
    assert out.verdict == "REJECT"


def test_critic_prompt_has_condition_script_probe_snapshot_and_no_mutant_info():
    _, fake = _review(probe_result("passed"), decision())
    call = fake.call_history[0]
    text = call["system"] + call["user"]
    for needle in (CID, "Invalid credentials", "outcome=passed", "snapshot excerpt", "to_have_text"):
        assert needle in text
    for banned in ("mutant", "MUTANT", "registry"):
        assert banned not in text


# ---------------------------------------------------------------------------------- subgraph ----
def test_subgraph_approves_on_first_pass():
    r, fake, prober = run([script()], [probe_result("passed")], [decision("APPROVE")])
    assert r.final == "approved" and r.iterations == 1
    assert r.probe.outcome == "passed"
    assert r.untested_reason is None and r.needs_human_review is False


def test_subgraph_repairs_test_bug():
    r, fake, prober = run(
        [script(locator='page.get_by_role("status")'), script()],
        [probe_result("runtime_error", "TimeoutError", "locator timeout"), probe_result("passed")],
        [decision("REJECT", 0.9, bug=True, refine="use the alert locator"), decision("APPROVE")],
    )
    assert r.final == "approved" and r.iterations == 2
    assert [c[1] for c in prober.calls] == [1, 2]
    assert 'page.get_by_role("alert")' in r.script
    # the repair prompt carried the critic's refinement
    assert "use the alert locator" in fake.call_history[2]["user"]


def test_subgraph_stops_at_max_iterations():
    """NFR-03 evidence: forced REJECT forever -> exactly 3 generate/probe/critic cycles, then not_converged."""
    r, fake, prober = run(
        [script()],
        [probe_result("runtime_error", "TimeoutError")],
        [decision("REJECT", 0.9, bug=True, refine="try again")],
    )
    assert r.final == "not_converged"
    assert r.iterations == MAX_CRITIC_ITERS == 3
    assert count(fake, GeneratedTest) == 3
    assert len(prober.calls) == 3
    assert r.untested_reason == "critic_not_converged"
    assert r.needs_human_review is True


def test_subgraph_defect_detection_is_approved_not_repaired():
    r, _, prober = run(
        [script()], [probe_result("assertion_failed", "AssertionError", "Expected Invalid credentials")],
        [decision("APPROVE", 0.9, bug=False)],
    )
    assert r.final == "approved" and r.iterations == 1
    assert r.probe.outcome == "assertion_failed"  # Agent 4 will map this to FAIL


def test_subgraph_never_lets_the_loop_weaken_the_assertion():
    weakened = script(expected="Invalid")
    r, _, _ = run(
        [script(), weakened, weakened, weakened, weakened],
        [probe_result("runtime_error", "TimeoutError")] * 2 + [probe_result("passed")],
        [decision("REJECT", 0.9, bug=True, refine="fix"), decision("APPROVE")],
    )
    assert r.assertion_reverted is True
    assert '"Invalid credentials"' in r.script  # canonical expectation survived
    assert 'to_have_text("Invalid")' not in r.script


def test_subgraph_unsafe_script_is_not_executed_and_loop_continues():
    unsafe = ScriptSafetyViolation(["line 1: forbidden import 'os'"])
    r, fake, prober = run(
        [script(), script()],
        [unsafe, probe_result("passed")],
        [decision("APPROVE", 0.9)],
    )
    # iteration 1 -> runtime_error from safety violation (critic forced to REJECT), iteration 2 -> passes
    assert r.final == "approved" and r.iterations == 2


def test_subgraph_generation_contract_failure_does_not_crash_loop():
    no_assert = "def test_x(page):\n    '''" + CID + "'''\n    page.goto('/')\n"
    r, fake, prober = run(
        [no_assert, no_assert, script()],  # iteration 1: two bad attempts; iteration 2: good
        [probe_result("passed")],
        [decision("APPROVE", 0.9)],
    )
    assert r.final == "approved" and r.iterations == 2


def test_compiled_graph_runs_under_default_recursion_limit():
    fake, prober, gen, critic = wire([script()], [probe_result("runtime_error", "TimeoutError")],
                                     [decision("REJECT", 0.9, bug=True, refine="x")])
    graph = build_agent3(gen, prober, critic)
    out = graph.invoke(
        {"condition": CONDITION.model_dump(), "selectors": [], "snapshot_excerpt": ""},
        {"recursion_limit": 25},
    )
    assert out["final"] == "not_converged" and out["iteration"] == 3
