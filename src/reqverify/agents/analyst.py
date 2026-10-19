"""Agent 1: Requirements Analyst Agent (Guide §9, Invariant D1, D4, D13).

Decomposes requirement documents into atomic testable conditions via Claude structured
outputs and executes strict programmatic post-processing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from reqverify.schemas.contracts import (
    LLMExtraction,
    ExtractedCondition,
    CoverageMatrix,
)
from reqverify.agents.ingestion import ingest_document, split_requirements, RequirementChunk
from reqverify.agents.postprocessor import postprocess_conditions, PostProcessorMetrics
from reqverify.llm.client import LLMClient
from reqverify.llm.fake_client import FakeLLMClient

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = (
    "You are an expert Requirements Engineering Analyst. "
    "Your task is to decompose the provided software requirement into a complete set of atomic, "
    "unambiguous, and testable conditions.\n\n"
    "Extraction Rules:\n"
    "1. source_span: Must be an EXACT, VERBATIM substring copied directly from the requirement text.\n"
    "2. predicate_text: A concise, verifiable assertion about observable application behavior.\n"
    "3. is_testable: Set to True if a user or automated test can observe this behavior through the web UI alone. "
    "If it is a backend-only process (e.g. database trigger, internal logging, encryption at rest), set to False.\n"
    "4. untestable_reason: If is_testable is False, provide a short explanation (e.g. 'Backend logging only').\n"
    "5. extraction_confidence: Float between 0.0 and 1.0 reflecting confidence in this condition extraction.\n"
    "6. rationale: A single short sentence (minimum 10 characters) justifying why this is an atomic condition. "
    "Do NOT include multi-step chain-of-thought or reasoning."
)


class RequirementsAnalystAgent:
    """Agent 1 decomposes requirement specifications into atomic testable conditions."""

    def __init__(
        self,
        llm_client: Optional[Union[LLMClient, FakeLLMClient]] = None,
        model: str = "claude-sonnet-5-5",
    ):
        self.llm_client = llm_client or LLMClient()
        self.model = model
        self.last_metrics: PostProcessorMetrics = PostProcessorMetrics()

    def analyze_document(self, document_input: Union[Path, str]) -> CoverageMatrix:
        """Analyze a requirements document and return the full CoverageMatrix.

        Args:
            document_input: Path to requirements document (.md or .pdf) or raw markdown text.

        Returns:
            CoverageMatrix: Global matrix of validated atomic conditions.
        """
        # Determine whether input is a file path or raw text
        is_path = False
        try:
            p = Path(document_input)
            if p.exists() and p.is_file():
                is_path = True
        except (OSError, ValueError):
            is_path = False

        if is_path:
            text, doc_hash = ingest_document(document_input)
        else:
            text = str(document_input)
            import hashlib
            doc_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        chunks = split_requirements(text)
        if not chunks:
            # Fallback if text doesn't contain REQ-xx headers: treat whole document as REQ-01
            chunks = [
                RequirementChunk(
                    req_id="REQ-01",
                    title="Requirement Specification",
                    text=text,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        all_conditions: list[ExtractedCondition] = []
        cumulative_metrics = PostProcessorMetrics()

        for chunk in chunks:
            logger.info("Decomposing requirement %s: %s", chunk.req_id, chunk.title)
            user_prompt = (
                f"Requirement ID: {chunk.req_id}\n"
                f"Title: {chunk.title}\n\n"
                f"Requirement Text:\n\"\"\"\n{chunk.text}\n\"\"\"\n\n"
                "Extract all atomic testable conditions following the schema."
            )

            extraction, meta = self.llm_client.parse(
                system=ANALYST_SYSTEM_PROMPT,
                user=user_prompt,
                schema=LLMExtraction,
            )

            # Post-process conditions per Guide §7.2
            valid_conditions, chunk_metrics = postprocess_conditions(
                raw_conditions=extraction.conditions,
                document_text=chunk.text,
                document_hash=doc_hash,
                req_id=chunk.req_id,
            )

            all_conditions.extend(valid_conditions)
            cumulative_metrics.total_received += chunk_metrics.total_received
            cumulative_metrics.valid_count += chunk_metrics.valid_count
            cumulative_metrics.dropped_hallucinated_spans += chunk_metrics.dropped_hallucinated_spans
            cumulative_metrics.dropped_duplicates += chunk_metrics.dropped_duplicates

        self.last_metrics = cumulative_metrics

        return CoverageMatrix(
            document_hash=doc_hash,
            model=self.model,
            conditions=all_conditions,
        )
