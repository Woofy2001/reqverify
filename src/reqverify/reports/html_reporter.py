"""Jinja2 HTML audit report generator for Agent 4 (Step 7.4, NFR-07, NFR-08)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reqverify.schemas.reports import VerificationSummary

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_SECRET_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9\-_]+")


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml", "jinja2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html_report(summary: VerificationSummary) -> str:
    """Render VerificationSummary into a standalone, accessible HTML audit report."""
    env = _get_jinja_env()
    template = env.get_template("report.html.jinja2")
    rendered = template.render(summary=summary)
    return _SECRET_PATTERN.sub("[REDACTED_API_KEY]", rendered)


def write_html_report(
    summary: VerificationSummary,
    base_dir: Union[str, Path] = "reports",
    filename: str = "report.html",
) -> Path:
    """Write the rendered HTML audit report to `reports/{run_id}/report.html`."""
    out_dir = Path(base_dir) / summary.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename
    out_file.write_text(render_html_report(summary), encoding="utf-8")
    return out_file
