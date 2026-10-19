"""Tests verifying strict black-box isolation of the mutant registry (Invariant D6).

Guarantees:
1. SUT Docker images never contain the mutant registry (enforced by .dockerignore).
2. The pipeline codebase under src/reqverify/ never imports, references, or inspects
   the mutant registry or answer keys.
3. techstore/mutants/registry.yaml matches expected grading catalog schema for evaluation.
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TECHSTORE_DIR = REPO_ROOT / "techstore"
PIPELINE_SRC_DIR = REPO_ROOT / "src" / "reqverify"
REGISTRY_PATH = TECHSTORE_DIR / "mutants" / "registry.yaml"
DOCKERIGNORE_PATH = TECHSTORE_DIR / ".dockerignore"


def test_dockerignore_blocks_mutants_directory():
    """Invariant D6: .dockerignore must explicitly exclude mutants/ directory."""
    assert DOCKERIGNORE_PATH.exists(), f".dockerignore not found at {DOCKERIGNORE_PATH}"
    lines = [
        line.strip()
        for line in DOCKERIGNORE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    # Check that mutants or mutants/ is present in .dockerignore
    assert any("mutants" in line for line in lines), (
        "Invariant D6 violation: techstore/.dockerignore must exclude 'mutants' from container build"
    )


def test_pipeline_source_never_imports_or_references_mutants():
    """Invariant D6: Pipeline code under src/reqverify/ must never reference mutant registry."""
    assert PIPELINE_SRC_DIR.exists(), f"Source directory not found at {PIPELINE_SRC_DIR}"

    python_files = list(PIPELINE_SRC_DIR.rglob("*.py"))
    assert len(python_files) > 0, "Pipeline source directory must contain Python files"

    for py_file in python_files:
        content = py_file.read_text(encoding="utf-8")
        parsed = ast.parse(content, filename=str(py_file))

        for node in ast.walk(parsed):
            # 1. Check direct imports: import ...
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "mutants" not in alias.name.lower(), (
                        f"Invariant D6 violation in {py_file}: illegal import of '{alias.name}'"
                    )

            # 2. Check from imports: from ... import ...
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert "mutants" not in mod.lower(), (
                    f"Invariant D6 violation in {py_file}: illegal import from '{mod}'"
                )

            # 3. Check string literals: no direct hardcoded path to registry.yaml
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                val_lower = node.value.lower()
                assert "registry.yaml" not in val_lower, (
                    f"Invariant D6 violation in {py_file}: hardcoded reference to 'registry.yaml'"
                )
                assert "techstore/mutants" not in val_lower and "techstore\\mutants" not in val_lower, (
                    f"Invariant D6 violation in {py_file}: hardcoded reference to 'techstore/mutants'"
                )


def test_mutant_registry_catalog_schema():
    """Mutant catalog at techstore/mutants/registry.yaml must be valid YAML for grading harness."""
    assert REGISTRY_PATH.exists(), f"Registry file not found at {REGISTRY_PATH}"
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))

    assert "mutants" in data, "registry.yaml must have top-level 'mutants' key"
    mutants = data["mutants"]
    if isinstance(mutants, list):
        mutant_map = {item["id"]: item for item in mutants if "id" in item}
    else:
        mutant_map = mutants

    assert len(mutant_map) == 10, f"Expected 10 mutants, found {len(mutant_map)}"

    expected_ids = [f"M{i:02d}" for i in range(1, 11)]
    for m_id in expected_ids:
        assert m_id in mutant_map, f"Mutant {m_id} missing in registry.yaml"
        entry = mutant_map[m_id]
        assert "module" in entry, f"{m_id} missing 'module'"
        assert "description" in entry, f"{m_id} missing 'description'"
        assert "violated_conditions" in entry or "condition_id" in entry, f"{m_id} missing condition mapping"
