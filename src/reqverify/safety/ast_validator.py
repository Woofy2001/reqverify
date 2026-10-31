"""AST safety validator for LLM-generated pytest-playwright scripts (Guide §9 Agent 3, NFR-04).

The generated script is *untrusted code*. Before it is ever executed, it is parsed (never run) and
rejected if it imports anything outside a tiny allow-list, calls dynamic-evaluation / file-IO builtins,
touches dunder attributes, uses CSS/XPath ``locator()`` instead of role-based locators (Decision D2),
or relies on fixed sleeps / ``networkidle`` instead of explicit waits.
"""

from __future__ import annotations

import ast
from typing import List

ALLOWED_IMPORT_ROOTS = frozenset({"pytest", "re", "playwright", "__future__"})
ALLOWED_PLAYWRIGHT_MODULES = frozenset({"playwright.sync_api", "playwright.async_api"})

FORBIDDEN_CALLS = frozenset(
    {
        "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
        "getattr", "setattr", "delattr", "globals", "locals", "vars",
    }
)
FORBIDDEN_METHODS = frozenset(
    {
        "write_text", "read_text", "write_bytes", "read_bytes", "unlink", "rmdir", "mkdir",
        "touch", "rename", "replace", "chmod", "wait_for_timeout", "locator", "evaluate",
        "evaluate_handle", "add_init_script", "route", "expose_function", "expose_binding",
    }
)
FORBIDDEN_STRING_CONSTANTS = frozenset({"networkidle"})
FORBIDDEN_PYTEST_CALLS = frozenset({"skip", "xfail", "importorskip", "exit", "fail"})
FORBIDDEN_MARK_PREFIXES = ("pytest.mark.skip", "pytest.mark.xfail")


class ScriptSafetyViolation(Exception):
    """Raised when a generated script fails the static safety gate. Carries every violation found."""

    def __init__(self, violations: List[str]):
        self.violations = list(violations)
        super().__init__("; ".join(self.violations))


class _SafetyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: List[str] = []
        self.has_test_function = False

    # -- imports ------------------------------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_module(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            self.violations.append(f"line {node.lineno}: relative import is forbidden")
        else:
            self._check_module(node.module or "", node.lineno)
        self.generic_visit(node)

    def _check_module(self, module: str, lineno: int) -> None:
        root = module.split(".")[0]
        if root not in ALLOWED_IMPORT_ROOTS:
            self.violations.append(f"line {lineno}: forbidden import '{module}'")
        elif root == "playwright" and module not in ALLOWED_PLAYWRIGHT_MODULES:
            self.violations.append(f"line {lineno}: forbidden import '{module}' (only playwright.sync_api allowed)")

    # -- functions / calls / attributes -------------------------------------------------------
    def _visit_function(self, node) -> None:
        if node.name.startswith("test_"):
            self.has_test_function = True
        for deco in node.decorator_list:
            text = ast.unparse(deco)
            if text.startswith(FORBIDDEN_MARK_PREFIXES):
                self.violations.append(f"line {deco.lineno}: forbidden decorator '@{text}' (skips/xfails hide failures)")
        self.generic_visit(node)

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Try(self, node: ast.Try) -> None:
        self.violations.append(f"line {node.lineno}: 'try' statement is forbidden (could swallow an AssertionError)")
        self.generic_visit(node)

    visit_TryStar = visit_Try

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
            self.violations.append(f"line {node.lineno}: forbidden call '{func.id}()'")
        elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_METHODS:
            self.violations.append(f"line {node.lineno}: forbidden method call '.{func.attr}()'")
        elif (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "pytest"
            and func.attr in FORBIDDEN_PYTEST_CALLS
        ):
            self.violations.append(f"line {node.lineno}: forbidden call 'pytest.{func.attr}()'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__") and node.attr.endswith("__"):
            self.violations.append(f"line {node.lineno}: forbidden dunder attribute '{node.attr}'")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("__") and node.id.endswith("__"):
            self.violations.append(f"line {node.lineno}: forbidden dunder name '{node.id}'")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and node.value in FORBIDDEN_STRING_CONSTANTS:
            self.violations.append(f"line {node.lineno}: forbidden wait strategy '{node.value}'")
        self.generic_visit(node)


def validate_script_ast(script: str) -> None:
    """Parse ``script`` (without executing it) and raise :class:`ScriptSafetyViolation` if unsafe."""
    try:
        tree = ast.parse(script)
    except SyntaxError as exc:
        raise ScriptSafetyViolation([f"syntax error at line {exc.lineno}: {exc.msg}"]) from exc

    visitor = _SafetyVisitor()
    visitor.visit(tree)
    if not visitor.has_test_function:
        visitor.violations.append("script must define at least one function named 'test_*'")
    if visitor.violations:
        raise ScriptSafetyViolation(visitor.violations)
