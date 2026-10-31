"""pytest plugin that records *why* a probe test ended, as JSON (Guide §7.3, Spike S-4).

``pytest`` exit code 1 covers both "assertion did not hold" and "test could not run", so the outcome is
classified here from the exception type:

* no exception                         -> ``passed``
* ``AssertionError`` (selectors resolved, expectation not met) -> ``assertion_failed``  (candidate app defect)
* ``AssertionError`` raised because ``expect()`` never found its element -> ``runtime_error``
  (Playwright reports an unresolvable locator as an assertion failure; per §7.3 a FAIL requires that
  selectors resolved, so this is a test bug, not an application defect)
* anything else (Playwright ``TimeoutError``, ``AttributeError``, fixture/setup failure) -> ``runtime_error``

The result path comes from ``REQVERIFY_PROBE_RESULT_PATH`` (default ``probe_result.json`` in the cwd).
"""

from __future__ import annotations

import json
import os

RESULT_PATH_ENV = "REQVERIFY_PROBE_RESULT_PATH"
_UNRESOLVED_MARKERS = ("element(s) not found", "waiting for get_by_", "strict mode violation")


def classify_exception(exc_type_name: str | None, message: str | None) -> str:
    """Map an exception type + message to a ProbeResult outcome (never returns ``timeout``)."""
    if exc_type_name is None:
        return "passed"
    if exc_type_name == "AssertionError":
        text = (message or "").lower()
        if any(marker in text for marker in _UNRESOLVED_MARKERS) and "locator resolved to" not in text:
            return "runtime_error"
        return "assertion_failed"
    return "runtime_error"


def _write(report: dict) -> None:
    path = os.environ.get(RESULT_PATH_ENV, "probe_result.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh)


def pytest_runtest_makereport(item, call):
    if call.when == "call" or (call.when == "setup" and call.excinfo is not None):
        exc_name = call.excinfo.typename if call.excinfo else None
        message = str(call.excinfo.value) if call.excinfo else None
        _write(
            {
                "outcome": classify_exception(exc_name, message),
                "exception_type": exc_name,
                "message": message,
                "duration": call.duration,
            }
        )
