"""Step 6.3: Test Generator + assertion immutability (Invariant D7, Guide §3, §9 Agent 3)."""

from __future__ import annotations

import ast

import pytest

from reqverify.agents.generator import (
    TestGenerator,
    assertions_preserved,
    extract_assertion_signature,
)
from reqverify.llm.fake_client import FakeLLMClient
from reqverify.schemas.contracts import ExtractedCondition, ProbeResult, CriticVerdict
from reqverify.schemas.probes import GeneratedTest
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

SELECTORS = SelectorMap(
    base_url="http://localhost:3000",
    pages={
        "/login": PageSnapshot(
            route="/login",
            title="Login",
            raw_aria_tree='- textbox "Email address"',
            elements=[
                UIElementSelector(
                    element_id="e1", role="textbox", accessible_name="Email address",
                    locator_recipe='page.get_by_role("textbox", name="Email address", exact=True)',
                    page_route="/login",
                ),
                UIElementSelector(
                    element_id="e2", role="alert", accessible_name="",
                    locator_recipe='page.get_by_role("alert")', page_route="/login",
                ),
            ],
        )
    },
)


def script(locator: str = 'page.get_by_role("alert")', expected: str = "Invalid credentials",
           with_doc: bool = True, extra: str = "") -> str:
    doc = f'    """{CID}: login failure alert."""\n' if with_doc else ""
    return (
        "from playwright.sync_api import Page, expect\n\n"
        "def test_login_alert(page: Page, base_url: str):\n"
        f"{doc}"
        '    page.goto(f"{base_url}/login")\n'
        f"{extra}"
        f'    expect({locator}).to_have_text("{expected}")\n'
    )


def make_generator(*scripts: str) -> tuple[TestGenerator, FakeLLMClient]:
    fake = FakeLLMClient()
    fake.register_sequence(GeneratedTest, [GeneratedTest(script=s) for s in scripts])
    return TestGenerator(fake), fake


# ---------------------------------------------------------------- signature extraction ----------
def test_signature_ignores_locator_and_timeout_but_keeps_matcher_and_expected():
    a = extract_assertion_signature(script())
    b = extract_assertion_signature(script(locator='page.get_by_role("alert").first'))
    assert a == b and len(a) == 1


def test_signature_changes_when_expected_value_changes():
    assert extract_assertion_signature(script()) != extract_assertion_signature(script(expected="Error"))


def test_signature_changes_when_matcher_loosened():
    loosened = script().replace("to_have_text", "to_contain_text")
    assert extract_assertion_signature(script()) != extract_assertion_signature(loosened)


def test_signature_marks_guarded_assertions_as_different():
    guarded = (
        "from playwright.sync_api import Page, expect\n"
        "def test_x(page: Page):\n"
        '    if page.url:\n'
        '        expect(page.get_by_role("alert")).to_have_text("Invalid credentials")\n'
    )
    assert extract_assertion_signature(script()) != extract_assertion_signature(guarded)


def test_plain_assert_locator_normalised():
    s1 = "def test_x(page):\n    assert page.get_by_role('alert').inner_text() == 'Hi'\n"
    s2 = "def test_x(page):\n    assert page.get_by_role('alert').first.inner_text() == 'Hi'\n"
    assert extract_assertion_signature(s1) == extract_assertion_signature(s2)


def test_assertions_preserved_allows_extra_waits_but_not_removal():
    base = extract_assertion_signature(script())
    with_extra = extract_assertion_signature(
        script(extra='    expect(page).to_have_url(f"{base_url}/login")\n')
    )
    assert assertions_preserved(base, with_extra)
    assert not assertions_preserved(base, ())


# ------------------------------------------------------------------- generation (iteration 1) ---
def test_initial_generation_includes_condition_docstring():
    gen, _ = make_generator(script(with_doc=False))  # LLM forgot the docstring
    res = gen.generate(CONDITION.model_dump(), SELECTORS)
    tree = ast.parse(res.script)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    assert CID in (ast.get_docstring(fn) or "")


def test_initial_generation_records_canonical_assertion():
    gen, _ = make_generator(script())
    res = gen.generate(CONDITION.model_dump(), SELECTORS)
    assert res.iteration == 1 and not res.reverted
    assert len(res.signature) == 1
    assert res.assertion_code == ['expect(page.get_by_role("alert")).to_have_text("Invalid credentials")']


def test_prompt_contains_predicate_selectors_and_no_mutant_info():
    gen, fake = make_generator(script())
    gen.generate(CONDITION.model_dump(), SELECTORS)
    call = fake.call_history[0]
    assert "Invalid credentials" in call["user"]
    assert 'page.get_by_role("textbox", name="Email address", exact=True)' in call["user"]
    assert CID in call["user"]
    for banned in ("mutant", "MUTANT", "registry"):
        assert banned not in call["system"] + call["user"]


def test_script_without_assertion_is_rejected_then_regenerated():
    no_assert = "def test_x(page):\n    '''" + CID + "'''\n    page.goto('/')\n"
    gen, fake = make_generator(no_assert, script())
    res = gen.generate(CONDITION.model_dump(), SELECTORS)
    assert len(res.signature) == 1
    assert len(fake.call_history) == 2


def test_script_without_any_assertion_after_retry_raises():
    from reqverify.agents.generator import GenerationContractError

    no_assert = "def test_x(page):\n    '''" + CID + "'''\n    page.goto('/')\n"
    gen, _ = make_generator(no_assert, no_assert)
    with pytest.raises(GenerationContractError):
        gen.generate(CONDITION.model_dump(), SELECTORS)


# --------------------------------------------------------------------------- D7 across repairs ---
def _repair_kwargs(first):
    return dict(
        iteration=2,
        previous_script=first.script,
        canonical_signature=list(first.signature),
        canonical_assertion_code=list(first.assertion_code),
        probe=ProbeResult(exit_code=1, outcome="runtime_error", exception_type="TimeoutError",
                          stdout_tail="locator timeout", duration_s=1.0),
        critic=CriticVerdict(verdict="REJECT", assertion_validity_score=0.9,
                             critique_notes="wrong locator", suggested_refinement="use the textbox locator"),
    )


def test_assertion_statement_remains_invariant_across_refinements():
    first_script = script()
    repaired = script(locator='page.get_by_role("alert").first', extra='    page.get_by_role("textbox", name="Email address", exact=True).fill("x")\n')
    gen, _ = make_generator(first_script, repaired)
    first = gen.generate(CONDITION.model_dump(), SELECTORS)
    second = gen.generate(CONDITION.model_dump(), SELECTORS, **_repair_kwargs(first))
    assert not second.reverted
    assert second.script == repaired
    assert assertions_preserved(first.signature, second.signature)


def test_repair_prompt_forbids_modifying_canonical_assertion():
    gen, fake = make_generator(script(), script())
    first = gen.generate(CONDITION.model_dump(), SELECTORS)
    gen.generate(CONDITION.model_dump(), SELECTORS, **_repair_kwargs(first))
    prompt = fake.call_history[1]["user"] + fake.call_history[1]["system"]
    assert "MUST NOT modify or loosen" in prompt
    assert first.assertion_code[0] in prompt
    assert "use the textbox locator" in prompt
    assert "Iteration: 2" in fake.call_history[1]["user"]


def test_weakened_assertion_is_retried_then_accepted_when_fixed():
    weakened = script(expected="Invalid")  # LLM loosens the expectation
    gen, fake = make_generator(script(), weakened, script(locator='page.get_by_role("alert").first'))
    first = gen.generate(CONDITION.model_dump(), SELECTORS)
    second = gen.generate(CONDITION.model_dump(), SELECTORS, **_repair_kwargs(first))
    assert not second.reverted and second.attempts == 2
    assert len(fake.call_history) == 3


def test_persistently_weakened_assertion_is_reverted_to_previous_script():
    weakened = script(expected="Invalid")
    gen, _ = make_generator(script(), weakened, weakened)
    first = gen.generate(CONDITION.model_dump(), SELECTORS)
    second = gen.generate(CONDITION.model_dump(), SELECTORS, **_repair_kwargs(first))
    assert second.reverted is True
    assert second.script == first.script
    assert second.attempts == 2
