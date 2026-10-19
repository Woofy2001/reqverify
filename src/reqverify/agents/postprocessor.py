"""Programmatic post-processing rules for Agent 1 (Guide §7.2).

Enforces:
1. Verbatim source_span substring verification against document text after whitespace normalization.
2. Deterministic condition ID assignment via make_condition_id (Invariant D4).
3. Exact duplicate condition dropping with metric tracking.
4. Comprehensive metric counting for academic and run-manifest reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from reqverify.schemas.contracts import (
    normalize,
    make_condition_id,
    LLMCondition,
    ExtractedCondition,
)

logger = logging.getLogger(__name__)


@dataclass
class PostProcessorMetrics:
    """Metrics tracking post-processing filtering and validation results."""
    total_received: int = 0
    valid_count: int = 0
    dropped_hallucinated_spans: int = 0
    dropped_duplicates: int = 0
    dropped_schema_failures: int = 0


def postprocess_conditions(
    raw_conditions: list[LLMCondition],
    document_text: str,
    document_hash: str,
    req_id: str,
) -> tuple[list[ExtractedCondition], PostProcessorMetrics]:
    """Execute post-processing rules on conditions extracted by LLM.

    Args:
        raw_conditions: Unprocessed conditions returned by LLM extraction.
        document_text: Raw text of the full requirements document or chunk.
        document_hash: SHA-256 hash of the parent requirements document.
        req_id: Canonical requirement ID (e.g. 'REQ-01').

    Returns:
        tuple[list[ExtractedCondition], PostProcessorMetrics]: Validated conditions and metrics.
    """
    metrics = PostProcessorMetrics(total_received=len(raw_conditions))
    normalized_doc = normalize(document_text)

    valid_conditions: list[ExtractedCondition] = []
    seen_predicates: set[str] = set()
    ordinal = 0

    for cond in raw_conditions:
        # Rule 1: Verbatim substring check (after whitespace normalization)
        normalized_span = normalize(cond.source_span)
        if not normalized_span or normalized_span not in normalized_doc:
            metrics.dropped_hallucinated_spans += 1
            logger.warning(
                "Dropped condition with non-verbatim source_span: %r in %s",
                cond.source_span,
                req_id,
            )
            continue

        # Rule 3: Exact duplicate filtering on normalized predicate text
        normalized_predicate = normalize(cond.predicate_text)
        if normalized_predicate in seen_predicates:
            metrics.dropped_duplicates += 1
            logger.info(
                "Dropped duplicate condition with identical predicate in %s: %r",
                req_id,
                cond.predicate_text,
            )
            continue
        seen_predicates.add(normalized_predicate)

        # Rule 2: Deterministic ID assignment
        ordinal += 1
        cond_id = make_condition_id(
            req_id=req_id,
            source_span=cond.source_span,
            ordinal=ordinal,
        )

        extracted = ExtractedCondition(
            source_requirement_id=req_id,
            source_span=cond.source_span,
            predicate_text=cond.predicate_text,
            is_testable=cond.is_testable,
            untestable_reason=cond.untestable_reason,
            extraction_confidence=cond.extraction_confidence,
            rationale=cond.rationale,
            condition_id=cond_id,
            document_hash=document_hash,
        )

        valid_conditions.append(extracted)
        metrics.valid_count += 1

    return valid_conditions, metrics
