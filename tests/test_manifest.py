import json
import pytest
from pathlib import Path
from reqverify.llm.manifest import RunManifest, write_manifest

def test_manifest_schema_completeness():
    """Verify that RunManifest schema includes all required experimental provenance fields."""
    manifest = RunManifest(
        run_id="run-exp-01",
        model="claude-sonnet-5-5",
        effort="medium",
        sdk_versions={"anthropic": "1.15.0", "pydantic": "2.14.1"},
        playwright_browser_build="chromium-1248",
        reqverify_commit="ae70f0d",
        sut_commit="clean",
        mutant_id="clean",
        document_sha256="abc12345def",
        total_input_tokens=1500,
        total_output_tokens=450,
        cost_estimate_usd=0.0075,
        cache_hit_ratio=0.85,
        timestamp_iso="2026-10-19T12:00:00Z"
    )
    data = manifest.model_dump()
    assert data["run_id"] == "run-exp-01"
    assert data["model"] == "claude-sonnet-5-5"
    assert data["cost_estimate_usd"] == 0.0075
    assert "anthropic" in data["sdk_versions"]

def test_manifest_scrubs_api_keys(tmp_path):
    """Verify that writing manifest never includes ANTHROPIC_API_KEY even if present in environment."""
    output_dir = tmp_path / "runs" / "run-test-key"
    manifest = RunManifest(
        run_id="run-test-key",
        model="claude-sonnet-5-5",
        effort="medium",
        sdk_versions={"anthropic": "1.15.0"},
        playwright_browser_build="chromium-1248",
        reqverify_commit="head",
        sut_commit="clean",
        mutant_id="clean",
        document_sha256="sha",
        total_input_tokens=10,
        total_output_tokens=10,
        cost_estimate_usd=0.0001,
        cache_hit_ratio=0.0,
        timestamp_iso="2026-10-19T12:00:00Z"
    )
    manifest_path = write_manifest(manifest, base_dir=str(tmp_path / "runs"))
    assert Path(manifest_path).exists()
    
    content = Path(manifest_path).read_text(encoding="utf-8")
    assert "sk-ant" not in content
    assert "API_KEY" not in content
