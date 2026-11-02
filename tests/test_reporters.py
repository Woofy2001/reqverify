"""Combined reporter test suite re-exporting JSON and HTML reporter tests (Deliverable §4)."""

from __future__ import annotations

from tests.test_html_reporter import (
    test_html_contains_trace_links,
    test_html_highlights_untested_needs_human_review,
    test_html_renders_without_errors,
)
from tests.test_json_reporter import (
    test_json_contains_all_conditions,
    test_json_schema_compliance,
)

__all__ = [
    "test_html_contains_trace_links",
    "test_html_highlights_untested_needs_human_review",
    "test_html_renders_without_errors",
    "test_json_contains_all_conditions",
    "test_json_schema_compliance",
]
