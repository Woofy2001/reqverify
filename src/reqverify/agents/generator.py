"""Agent 3 (part 1): Test Generator with assertion immutability (Invariant D7, Guide Â§3, Â§9).

The Generator writes ONE self-contained pytest-playwright test per testable condition. The asserted
expectation is derived from ``predicate_text`` in iteration 1 and is then *locked*: repair iterations may
change locators, waits and navigation but never the expectation. The lock is enforced in code (not only in
the prompt) by comparing a structural signature of every ``expect(...)`` / ``assert`` statement:

* locators (anything rooted at ``page``) and ``timeout=`` kwargs are normalised away -> repairable;
* matcher name, negation, expected values and other kwargs are kept -> immutable;
* assertions nested under ``if/for/while`` are marked ``guarded:`` -> wrapping an assertion changes the signature.

Extra assertions added during repair (e.g. an ``expect(page).to_have_url`` wait) are allowed; removing or
altering a canonical one is rejected, retried once, then reverted to the previous script.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

from reqverify.llm.client import LLMClient
from reqverify.llm.fake_client import FakeLLMClient
from reqverify.schemas.contracts import CriticVerdict, ExtractedCondition, ProbeResult
from reqverify.schemas.probes import GeneratedTest
from reqverify.schemas.selectors import SelectorMap, UIElementSelector

MAX_GENERATION_ATTEMPTS = 2
_CONTROL_FLOW = (ast.If, ast.While, ast.For, ast.AsyncFor)
_CONTAINERS = (ast.With, ast.AsyncWith, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


class GenerationContractError(RuntimeError):
    """The Generator could not produce a script satisfying the structural contract (and cannot revert)."""


# --------------------------------------------------------------------------- assertion signature --
class _NormaliseLocators(ast.NodeTransformer):
    """Replace every expression chain rooted at ``page`` with the placeholder ``LOC``."""

    @staticmethod
    def _root(node: ast.AST) -> Optional[str]:
        while isinstance(node, (ast.Call, ast.Attribute, ast.Subscript)):
            node = node.func if isinstance(node, ast.Call) else node.value
        return node.id if isinstance(node, ast.Name) else None

    def _maybe(self, node):
        if self._root(node) == "page":
            return ast.copy_location(ast.Name(id="LOC", ctx=ast.Load()), node)
        return self.generic_visit(node)

    visit_Call = visit_Attribute = visit_Subscript = _maybe


def _norm_dump(node: ast.AST) -> str:
    return ast.dump(_NormaliseLocators().visit(copy.deepcopy(node)))


def _expect_signature(call: ast.AST) -> Optional[str]:
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
        return None
    matcher, base, negated = call.func.attr, call.func.value, False
    if isinstance(base, ast.Attribute) and base.attr == "not_":
        negated, base = True, base.value
    if not (isinstance(base, ast.Call) and isinstance(base.func, ast.Name) and base.func.id == "expect"):
        return None
    args = [_norm_dump(a) for a in call.args]
    kwargs = sorted((k.arg or "**", _norm_dump(k.value)) for k in call.keywords if k.arg != "timeout")
    return f"expect|{'not_.' if negated else ''}{matcher}|{args}|{kwargs}"


def _collect(stmts: Iterable[ast.stmt], guarded: bool, source: str, out: List[Tuple[int, str, str]]) -> None:
    for stmt in stmts:
        sig: Optional[str] = None
        if isinstance(stmt, ast.Expr):
            sig = _expect_signature(stmt.value)
        elif isinstance(stmt, ast.Assert):
            sig = f"assert|{_norm_dump(stmt.test)}"
        if sig is not None:
            code = ast.get_source_segment(source, stmt) or ast.unparse(stmt)
            out.append((stmt.lineno, ("guarded:" if guarded else "") + sig, code))
        elif isinstance(stmt, _CONTROL_FLOW):
            _collect(stmt.body, True, source, out)
            _collect(stmt.orelse, True, source, out)
        elif isinstance(stmt, ast.Try):
            _collect(stmt.body, True, source, out)
        elif isinstance(stmt, _CONTAINERS):
            _collect(stmt.body, guarded, source, out)


def _assertions(script: str) -> List[Tuple[int, str, str]]:
    tree = ast.parse(script)
    found: List[Tuple[int, str, str]] = []
    _collect(tree.body, False, script, found)
    return sorted(found, key=lambda t: t[0])


def extract_assertion_signature(script: str) -> Tuple[str, ...]:
    """Structural signature of every assertion in ``script`` (locators and timeouts normalised away)."""
    return tuple(sig for _, sig, _ in _assertions(script))


def extract_assertion_code(script: str) -> List[str]:
    """Human-readable source of every assertion statement (shown to the LLM as the locked expectation)."""
    return [code for _, _, code in _assertions(script)]


def assertions_preserved(canonical: Sequence[str], candidate: Sequence[str]) -> bool:
    """True if ``canonical`` is an ordered subsequence of ``candidate`` (extra waits allowed, edits/removals not)."""
    it = iter(candidate)
    return all(any(c == s for s in it) for c in canonical)


# ---------------------------------------------------------------------------------- prompts ------
GENERATOR_SYSTEM_PROMPT = (
    "You are a senior QA automation engineer writing ONE Python pytest-playwright test that verifies ONE "
    "atomic requirement condition against a live web application, without access to its source code.\n\n"
    "Hard rules:\n"
    "1. Output a complete, self-contained module with exactly one function named test_*; it must navigate "
    "to everything it needs itself (log in first if the condition requires an authenticated state).\n"
    "2. Allowed imports only: `re`, `pytest`, and `from playwright.sync_api import Page, expect`.\n"
    "3. Use ONLY the locators listed under 'Available locators', copied verbatim. Never write CSS/XPath, "
    "`page.locator(...)`, `page.evaluate(...)`, `wait_for_timeout`, `time.sleep` or 'networkidle'. Wait with "
    "web-first `expect(...)` assertions or `page.wait_for_url(...)`.\n"
    "4. Available fixtures: `page`, `base_url` (use `f\"{base_url}/route\"`), `test_user` and `admin_user` "
    "(dicts with 'email' and 'password'). Never hard-code credentials.\n"
    "5. The final assertion must express the condition's predicate_text exactly, using `expect(...)`. Do not "
    "weaken it with partial matches, regexes broader than the predicate, `try/except`, `skip` or `xfail`.\n"
    "6. The test function docstring must start with the condition_id.\n"
    "7. Return the code only in the `script` field (no markdown fences)."
)


def _as_condition(condition: Union[ExtractedCondition, dict]) -> ExtractedCondition:
    return condition if isinstance(condition, ExtractedCondition) else ExtractedCondition.model_validate(condition)


def _as_selectors(selectors: Union[SelectorMap, Sequence[Any]]) -> List[UIElementSelector]:
    items = selectors.get_all_elements() if isinstance(selectors, SelectorMap) else list(selectors)
    return [s if isinstance(s, UIElementSelector) else UIElementSelector.model_validate(s) for s in items]


def _render_selectors(selectors: Sequence[UIElementSelector]) -> str:
    lines = [
        f'- [{s.page_route or "?"}] {s.role} "{s.accessible_name}" -> {s.locator_recipe}'
        for s in selectors
        if s.locator_recipe
    ]
    return "\n".join(lines) if lines else "(none discovered)"


def _dump(model: Any) -> Any:
    return model.model_dump() if hasattr(model, "model_dump") else model


def build_user_prompt(
    condition: ExtractedCondition,
    selectors: Sequence[UIElementSelector],
    iteration: int,
    previous_script: Optional[str] = None,
    canonical_assertion_code: Optional[Sequence[str]] = None,
    probe: Optional[ProbeResult] = None,
    critic: Optional[CriticVerdict] = None,
    violation: Optional[str] = None,
) -> str:
    parts = [
        f"Iteration: {iteration}",
        f"condition_id: {condition.condition_id}",
        f"requirement: {condition.source_requirement_id}",
        f'predicate_text: "{condition.predicate_text}"',
        f'source_span: "{condition.source_span}"',
        "",
        "Available locators:",
        _render_selectors(selectors),
    ]
    if iteration > 1 and previous_script:
        parts += ["", "Previous script:", "```python", previous_script, "```"]
        if probe is not None:
            parts += [
                "",
                f"Probe result: outcome={probe.outcome} exception_type={probe.exception_type}",
                f"Probe output tail:\n{probe.stdout_tail[-1200:]}",
            ]
        if critic is not None:
            parts += [
                "",
                f"Critic notes: {critic.critique_notes}",
                f"Suggested refinement: {critic.suggested_refinement or '(none)'}",
            ]
        locked = "\n".join(canonical_assertion_code or [])
        parts += [
            "",
            "You may only repair locators, waits, and navigation actions. You MUST NOT modify or loosen the "
            f"following assertion(s):\n{locked}",
        ]
    if violation:
        parts += ["", f"Your previous answer was rejected: {violation}. Fix this and answer again."]
    parts += ["", "Write the test now."]
    return "\n".join(parts)


# ---------------------------------------------------------------------------------- results ------
@dataclass
class GenerationResult:
    script: str
    signature: Tuple[str, ...]
    assertion_code: List[str]
    iteration: int
    reverted: bool = False
    attempts: int = 1
    notes: str = field(default="")


class TestGenerator:
    """LLM-backed generator of immutable-assertion pytest-playwright tests."""

    __test__ = False  # not a pytest test class

    def __init__(self, llm_client: Union[LLMClient, FakeLLMClient]):
        self.llm_client = llm_client

    # -- public ---------------------------------------------------------------------------------
    def generate(
        self,
        condition: Union[ExtractedCondition, dict],
        selectors: Union[SelectorMap, Sequence[Any]],
        *,
        iteration: int = 1,
        previous_script: Optional[str] = None,
        canonical_signature: Optional[Sequence[str]] = None,
        canonical_assertion_code: Optional[Sequence[str]] = None,
        probe: Optional[Union[ProbeResult, dict]] = None,
        critic: Optional[Union[CriticVerdict, dict]] = None,
    ) -> GenerationResult:
        cond = _as_condition(condition)
        sels = _as_selectors(selectors)
        probe_m = ProbeResult.model_validate(probe) if isinstance(probe, dict) else probe
        critic_m = CriticVerdict.model_validate(critic) if isinstance(critic, dict) else critic

        violation: Optional[str] = None
        for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
            user = build_user_prompt(
                cond, sels, iteration, previous_script, canonical_assertion_code, probe_m, critic_m, violation
            )
            out, _meta = self.llm_client.parse(system=GENERATOR_SYSTEM_PROMPT, user=user, schema=GeneratedTest)
            script = self._ensure_condition_docstring(out.script, cond.condition_id)
            violation = self._contract_violation(script, canonical_signature)
            if violation is None:
                return GenerationResult(
                    script=script,
                    signature=extract_assertion_signature(script),
                    assertion_code=extract_assertion_code(script),
                    iteration=iteration,
                    attempts=attempt,
                    notes=out.notes,
                )

        # Both attempts violated the contract.
        if previous_script is not None and canonical_signature is not None:
            return GenerationResult(
                script=previous_script,
                signature=tuple(canonical_signature),
                assertion_code=list(canonical_assertion_code or []),
                iteration=iteration,
                reverted=True,
                attempts=MAX_GENERATION_ATTEMPTS,
            )
        raise GenerationContractError(violation or "generation failed")

    # -- helpers --------------------------------------------------------------------------------
    @staticmethod
    def _contract_violation(script: str, canonical: Optional[Sequence[str]]) -> Optional[str]:
        try:
            signature = extract_assertion_signature(script)
        except SyntaxError as exc:
            return f"syntax error at line {exc.lineno}: {exc.msg}"
        if not signature:
            return "the script contains no expect(...) or assert statement"
        if canonical is not None and not assertions_preserved(canonical, signature):
            return "the locked assertion was modified, weakened, removed or wrapped in control flow"
        return None

    @staticmethod
    def _ensure_condition_docstring(script: str, condition_id: str) -> str:
        try:
            tree = ast.parse(script)
        except SyntaxError:
            return script  # surfaced later by _contract_violation
        fn = next(
            (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")),
            None,
        )
        if fn is None:
            return script
        doc = ast.get_docstring(fn)
        if doc and condition_id in doc:
            return script
        if doc is not None:
            fn.body[0] = ast.Expr(value=ast.Constant(value=f"{condition_id}: {doc}"))
        else:
            fn.body.insert(0, ast.Expr(value=ast.Constant(value=f"{condition_id}: generated verification test")))
        return ast.unparse(ast.fix_missing_locations(tree)) + "\n"
