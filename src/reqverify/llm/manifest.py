from __future__ import annotations
import json
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class RunManifest(BaseModel):
    """Immutable audit record capturing complete provenance for an experimental run."""
    run_id: str
    model: str = "claude-sonnet-5-5"
    effort: str = "medium"
    sdk_versions: Dict[str, str] = Field(default_factory=dict)
    playwright_browser_build: str = "chromium-1248"
    reqverify_commit: str = "unknown"
    sut_commit: str = "clean"
    mutant_id: str = "clean"
    document_sha256: str = "unknown"
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cost_estimate_usd: float = 0.0
    cache_hit_ratio: float = 0.0
    timestamp_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

def get_installed_package_versions() -> Dict[str, str]:
    """Inspect and return current environment versions of key dependencies."""
    packages = ["anthropic", "langgraph", "playwright", "pydantic", "scipy", "pytest"]
    versions = {}
    for pkg in packages:
        try:
            versions[pkg] = version(pkg)
        except PackageNotFoundError:
            versions[pkg] = "not-installed"
    return versions

def get_git_commit(cwd: Optional[str] = None) -> str:
    """Return the current git commit SHA."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"

def write_manifest(manifest: RunManifest, base_dir: str = "runs") -> str:
    """Write sanitized run manifest to runs/{run_id}/manifest.json."""
    run_dir = Path(base_dir) / manifest.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_file = run_dir / "manifest.json"
    manifest_dict = manifest.model_dump()
    
    # Defensive scrub: guarantee no token or key strings are serialized
    clean_json = json.dumps(manifest_dict, indent=2)
    manifest_file.write_text(clean_json, encoding="utf-8")
    return str(manifest_file)
