"""Tests verifying document ingestion (.md and .pdf) and deterministic requirement splitting (Guide §9 Agent 1)."""

from __future__ import annotations

import io
from pathlib import Path
import pytest
from pypdf import PdfWriter

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_REQS_PATH = REPO_ROOT / "dev_app" / "requirements.md"
EVAL_REQS_PATH = REPO_ROOT / "eval" / "ground_truth" / "requirements.md"


def test_ingestion_module_importable():
    """Verify ingestion module exports ingest_document and split_requirements."""
    from reqverify.agents.ingestion import ingest_document, split_requirements, RequirementChunk
    assert callable(ingest_document)
    assert callable(split_requirements)
    assert RequirementChunk is not None


def test_ingest_markdown_document_and_hash():
    """Verify ingestion of markdown document computes valid SHA-256 hash."""
    from reqverify.agents.ingestion import ingest_document

    assert DEV_REQS_PATH.exists()
    text, doc_hash = ingest_document(DEV_REQS_PATH)

    assert isinstance(text, str)
    assert len(text) > 50
    assert "REQ-DEV-01" in text
    assert len(doc_hash) == 64  # Standard SHA-256 hex string

    # Determinism: re-ingestion returns identical text and hash
    text2, doc_hash2 = ingest_document(DEV_REQS_PATH)
    assert text == text2
    assert doc_hash == doc_hash2


def test_split_markdown_requirements_dev_set():
    """Verify deterministic splitting of dev_app requirements into REQ chunks."""
    from reqverify.agents.ingestion import ingest_document, split_requirements

    text, _ = ingest_document(DEV_REQS_PATH)
    chunks = split_requirements(text)

    # dev_app/requirements.md defines REQ-DEV-01 through REQ-DEV-05
    assert len(chunks) == 5
    expected_ids = [f"REQ-DEV-{i:02d}" for i in range(1, 6)]
    actual_ids = [c.req_id for c in chunks]
    assert actual_ids == expected_ids

    for chunk in chunks:
        assert chunk.req_id.startswith("REQ-")
        assert len(chunk.title.strip()) > 0
        assert len(chunk.text.strip()) > 0
        assert chunk.start_char < chunk.end_char
        # The slice of text matches chunk text exactly
        assert text[chunk.start_char:chunk.end_char] == chunk.text


def test_split_markdown_requirements_eval_set():
    """Verify deterministic splitting of full 16 requirements in ground truth."""
    from reqverify.agents.ingestion import ingest_document, split_requirements

    assert EVAL_REQS_PATH.exists()
    text, _ = ingest_document(EVAL_REQS_PATH)
    chunks = split_requirements(text)

    assert len(chunks) == 16
    expected_ids = [f"REQ-{i:02d}" for i in range(1, 17)]
    actual_ids = [c.req_id for c in chunks]
    assert actual_ids == expected_ids


def test_pdf_ingestion_with_pypdf(tmp_path: Path):
    """Verify PDF document ingestion using pypdf."""
    from reqverify.agents.ingestion import ingest_document

    # Create a synthetic PDF using pypdf
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    pdf_path = tmp_path / "sample_reqs.pdf"
    with open(pdf_path, "wb") as f:
        writer.write(f)

    text, doc_hash = ingest_document(pdf_path)
    assert isinstance(text, str)
    assert len(doc_hash) == 64


def test_unsupported_document_format(tmp_path: Path):
    """Verify unsupported file extensions raise ValueError."""
    from reqverify.agents.ingestion import ingest_document

    bad_file = tmp_path / "requirements.docx"
    bad_file.write_text("dummy", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        ingest_document(bad_file)
