"""JSON report serializer and loader for Agent 4 (Step 7.3, NFR-07, NFR-08)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Union

from reqverify.schemas.reports import VerificationSummary

_SECRET_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9\-_]+")


def serialize_json_report(summary: VerificationSummary) -> str:
    """Serialize a VerificationSummary to formatted JSON with zero-leakage scrubbing (NFR-08)."""
    payload = summary.model_dump(mode="json")
    raw_json = json.dumps(payload, indent=2, ensure_ascii=False)
    return _SECRET_PATTERN.sub("[REDACTED_API_KEY]", raw_json)


def write_json_report(
    summary: VerificationSummary,
    base_dir: Union[str, Path] = "reports",
    filename: str = "results.json",
) -> Path:
    """Write VerificationSummary to `reports/{run_id}/results.json` and return its Path."""
    out_dir = Path(base_dir) / summary.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename
    out_file.write_text(serialize_json_report(summary), encoding="utf-8")
    return out_file


def load_json_report(path: Union[str, Path]) -> VerificationSummary:
    """Load and validate a VerificationSummary from a JSON file."""
    raw = Path(path).read_text(encoding="utf-8")
    return VerificationSummary.model_validate_json(raw)
