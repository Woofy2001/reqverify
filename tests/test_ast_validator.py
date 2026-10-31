"""Step 6.1: AST safety gate for LLM-written pytest-playwright scripts (Guide §9 Agent 3 Safety, NFR-04)."""

from __future__ import annotations

import pytest

from reqverify.safety.ast_validator import ScriptSafetyViolation, validate_script_ast

VALID_SCRIPT = '''
"""C-01.1-abcd1234: Login rejects invalid credentials."""
import re
import pytest
from playwright.sync_api import Page, expect


def test_login_alert(page: Page, base_url: str):
    page.goto(f"{base_url}/login")
    page.get_by_role("textbox", name="Email address", exact=True).fill("a@b.com")
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_role("alert")).to_have_text(re.compile("Invalid credentials"))
'''


def _violations(script: str) -> list[str]:
    with pytest.raises(ScriptSafetyViolation) as exc:
        validate_script_ast(script)
    return exc.value.violations


def test_valid_playwright_script_passes():
    validate_script_ast(VALID_SCRIPT)  # must not raise


@pytest.mark.parametrize(
    "stmt",
    [
        "import os",
        "import sys",
        "import subprocess",
        "import socket",
        "import requests",
        "import urllib.request",
        "from os import path",
        "from subprocess import run",
        "import time",
    ],
)
def test_forbidden_imports_rejected(stmt):
    script = f"{stmt}\n\ndef test_x(page):\n    pass\n"
    violations = _violations(script)
    assert any("import" in v.lower() for v in violations)


@pytest.mark.parametrize("call", ["eval('1')", "exec('x=1')", "__import__('os')", "compile('1','f','eval')"])
def test_eval_exec_rejected(call):
    script = f"def test_x(page):\n    {call}\n"
    violations = _violations(script)
    assert any(call.split("(")[0] in v for v in violations)


@pytest.mark.parametrize(
    "body",
    [
        "open('x.txt','w')",
        "pathlib.Path('x').write_text('y')",
        "Path('x').read_text()",
    ],
)
def test_file_io_rejected(body):
    script = f"def test_x(page):\n    {body}\n"
    assert _violations(script)


def test_dunder_attribute_escape_rejected():
    script = "def test_x(page):\n    page.__class__.__mro__\n"
    assert any("__class__" in v or "__mro__" in v for v in _violations(script))


def test_dynamic_attribute_builtins_rejected():
    script = "def test_x(page):\n    getattr(page, 'goto')('/')\n"
    assert any("getattr" in v for v in _violations(script))


def test_fixed_sleep_and_networkidle_rejected():
    script = (
        "def test_x(page):\n"
        "    page.wait_for_timeout(500)\n"
        "    page.wait_for_load_state('networkidle')\n"
    )
    violations = _violations(script)
    assert any("wait_for_timeout" in v for v in violations)
    assert any("networkidle" in v for v in violations)


def test_css_xpath_locator_rejected():
    script = "def test_x(page):\n    page.locator('div.x').click()\n"
    assert any("locator" in v for v in _violations(script))


def test_syntax_error_reported_as_violation():
    violations = _violations("def test_x(:\n    pass\n")
    assert any("syntax" in v.lower() for v in violations)


def test_script_without_test_function_rejected():
    violations = _violations("import re\n\ndef helper():\n    return 1\n")
    assert any("test_" in v for v in violations)


def test_all_violations_collected_not_just_first():
    script = "import os\nimport socket\n\ndef test_x(page):\n    eval('1')\n"
    assert len(_violations(script)) >= 3


def test_try_except_wrapping_rejected():
    """A try/except can swallow an AssertionError and fake a PASS (Invariant D7)."""
    script = (
        "from playwright.sync_api import expect\n"
        "def test_x(page):\n"
        "    try:\n"
        "        expect(page).to_have_title('x')\n"
        "    except Exception:\n"
        "        pass\n"
    )
    assert any("try" in v.lower() for v in _violations(script))


@pytest.mark.parametrize(
    "body",
    ["pytest.skip('x')", "pytest.xfail('x')", "pytest.importorskip('x')"],
)
def test_pytest_skip_xfail_calls_rejected(body):
    script = f"import pytest\ndef test_x(page):\n    {body}\n"
    assert any("pytest" in v for v in _violations(script))


@pytest.mark.parametrize("deco", ["@pytest.mark.skip", "@pytest.mark.xfail", "@pytest.mark.skipif(True, reason='x')"])
def test_skip_decorators_rejected(deco):
    script = f"import pytest\n{deco}\ndef test_x(page):\n    pass\n"
    assert any("pytest.mark" in v for v in _violations(script))


def test_pytest_fixtures_and_parametrize_still_allowed():
    validate_script_ast(
        "import pytest\n"
        "@pytest.mark.parametrize('n', [1, 2])\n"
        "def test_x(page, n):\n    pass\n"
    )
