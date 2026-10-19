"""Tests verifying Docker multi-stage containerization, non-root security, and image tagging for TechStore."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TECHSTORE_DIR = REPO_ROOT / "techstore"
DOCKERFILE_PATH = TECHSTORE_DIR / "Dockerfile"
BUILD_SCRIPT_PATH = TECHSTORE_DIR / "scripts" / "build_mutants.ps1"
DOCKER_COMPOSE_PATH = TECHSTORE_DIR / "docker-compose.yml"


def test_dockerfile_multi_stage_and_pinned_base():
    """Dockerfile must use pinned node:22.14-alpine base and multi-stage build."""
    assert DOCKERFILE_PATH.exists(), f"Dockerfile not found at {DOCKERFILE_PATH}"
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")

    # Base image must be pinned node:22.14-alpine
    assert re.search(r"FROM\s+node:22\.14-alpine", content, re.IGNORECASE), (
        "Dockerfile must use pinned base image node:22.14-alpine"
    )

    # Multi-stage build structure
    assert "AS deps" in content or "as deps" in content, "Dockerfile must define 'deps' stage"
    assert "AS builder" in content or "as builder" in content, "Dockerfile must define 'builder' stage"
    assert "AS runner" in content or "as runner" in content, "Dockerfile must define 'runner' stage"


def test_dockerfile_enforces_non_root_user():
    """Dockerfile runner stage must drop root and enforce USER node (CIS Benchmark)."""
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    
    # Check that USER node is explicitly declared in runner stage
    assert re.search(r"\nUSER\s+node", content), (
        "Dockerfile must switch to non-root 'USER node' in runtime stage"
    )


def test_dockerfile_supports_mutant_arg_and_env():
    """Dockerfile must declare ARG MUTANT and ENV MUTANT for immutable tagging."""
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "ARG MUTANT" in content, "Dockerfile must support ARG MUTANT"
    assert "ENV MUTANT" in content, "Dockerfile must define ENV MUTANT"


def test_build_mutants_script_defines_11_tags():
    """build_mutants.ps1 must exist and define building all 11 immutable tags."""
    assert BUILD_SCRIPT_PATH.exists(), f"Build script not found at {BUILD_SCRIPT_PATH}"
    script_content = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")

    expected_tags = [
        "techstore:clean",
        "techstore:m01",
        "techstore:m02",
        "techstore:m03",
        "techstore:m04",
        "techstore:m05",
        "techstore:m06",
        "techstore:m07",
        "techstore:m08",
        "techstore:m09",
        "techstore:m10",
    ]

    for tag in expected_tags:
        assert tag in script_content, f"build_mutants.ps1 missing image tag {tag}"


def test_docker_compose_validity():
    """docker-compose.yml must specify clean image and standard port mapping."""
    assert DOCKER_COMPOSE_PATH.exists()
    content = DOCKER_COMPOSE_PATH.read_text(encoding="utf-8")
    assert "techstore:clean" in content
    assert "3000:3000" in content
