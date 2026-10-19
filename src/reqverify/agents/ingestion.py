"""Requirements document ingestion and deterministic requirement splitting (Guide §9 Agent 1)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from pypdf import PdfReader


@dataclass(frozen=True)
class RequirementChunk:
    """Atomic requirement segment extracted deterministically from a document."""
    req_id: str
    title: str
    text: str
    start_char: int
    end_char: int


def ingest_document(path: Path | str) -> tuple[str, str]:
    """Ingest a requirements document (.md, .txt, or .pdf) and compute its SHA-256 hash.

    Args:
        path: Path to the requirements document.

    Returns:
        tuple[str, str]: (document_text, document_sha256_hex)

    Raises:
        FileNotFoundError: If the document path does not exist.
        ValueError: If the file extension is not supported.
    """
    doc_path = Path(path)
    if not doc_path.exists():
        raise FileNotFoundError(f"Requirements document not found at: {doc_path}")

    ext = doc_path.suffix.lower()

    if ext in {".md", ".markdown", ".txt"}:
        text = doc_path.read_text(encoding="utf-8")
    elif ext == ".pdf":
        reader = PdfReader(str(doc_path))
        pages_text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pages_text.append(extracted)
        text = "\n\n".join(pages_text)
    else:
        raise ValueError(
            f"Unsupported file extension '{ext}'. Only .md, .markdown, .txt, and .pdf are supported."
        )

    doc_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, doc_hash


def split_requirements(text: str) -> list[RequirementChunk]:
    """Deterministically segment requirements text into individual requirement chunks.

    Splits on Markdown headings identifying requirements, e.g.
    '## REQ-01: User Login' or '### REQ-DEV-01: Task Creation'.

    Args:
        text: Ingested document text.

    Returns:
        list[RequirementChunk]: Ordered list of requirement chunks.
    """
    pattern = re.compile(
        r"(?m)^(#{1,4}\s+((?:REQ|req)(?:-[A-Za-z0-9]+)*)(?::\s*|\s*[-–—]\s*|\s+)(.*?))\s*$"
    )
    matches = list(pattern.finditer(text))

    chunks: list[RequirementChunk] = []
    for i, match in enumerate(matches):
        req_id = match.group(2).strip().upper()
        title = match.group(3).strip()
        start_char = match.start()
        end_char = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start_char:end_char]

        chunks.append(
            RequirementChunk(
                req_id=req_id,
                title=title,
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
            )
        )

    return chunks
