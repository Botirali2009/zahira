"""Extractor selection and the rules-then-LLM escalation policy."""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.services.extract.base import ExtractionContext, ExtractionResult, FieldValue
from app.services.extract.llm import LLMExtractor
from app.services.extract.rules import RuleBasedExtractor

logger = get_logger(__name__)


def extract_fields(
    text: str,
    context: ExtractionContext,
    strategy: str | None = None,
    llm: LLMExtractor | None = None,
) -> ExtractionResult:
    """Run the configured extraction strategy.

    `auto` is the production setting: rules first, and the LLM only when the
    rules come back below the escalation threshold. Escalated results are merged
    field by field rather than replacing the rule output wholesale — the rules
    can be certain about the total while being blind to the vendor name, and
    throwing away the part that worked would be a regression.
    """
    strategy = strategy or settings.extraction_strategy
    llm = llm or LLMExtractor()

    if strategy == "llm" and llm.is_available():
        return llm.extract(text, context)

    result = RuleBasedExtractor().extract(text, context)

    if strategy != "auto":
        return result

    if result.overall_confidence >= settings.llm_escalation_threshold:
        return result

    if not llm.is_available():
        result.warnings.append(
            "Low rule confidence and no LLM configured; document needs human review"
        )
        return result

    logger.info(
        "escalating to LLM",
        extra={"rule_confidence": result.overall_confidence,
               "threshold": settings.llm_escalation_threshold},
    )
    llm_result = llm.extract(text, context)
    return merge_results(result, llm_result)


def merge_results(primary: ExtractionResult, secondary: ExtractionResult) -> ExtractionResult:
    """Take each field from whichever extractor was more confident about it."""
    merged = ExtractionResult(
        fields=dict(primary.fields),
        line_items=list(primary.line_items),
        doc_type=primary.doc_type,
        strategy=f"{primary.strategy}+{secondary.strategy}",
        model_name=secondary.model_name or primary.model_name,
        duration_ms=primary.duration_ms + secondary.duration_ms,
        cost_usd=primary.cost_usd + secondary.cost_usd,
        warnings=[*primary.warnings, *secondary.warnings],
    )

    for name, candidate in secondary.fields.items():
        existing = merged.fields.get(name)
        if existing is None or not existing.is_present:
            merged.fields[name] = candidate
        elif candidate.is_present and candidate.confidence > existing.confidence:
            merged.fields[name] = FieldValue(
                value=candidate.value,
                confidence=candidate.confidence,
                source=f"{candidate.source} (over {existing.source})",
                raw_text=candidate.raw_text,
                page=candidate.page,
                bbox=candidate.bbox,
            )

    # Line items are all-or-nothing: a half-and-half table would not reconcile
    # against either extractor's totals.
    if not merged.line_items and secondary.line_items or secondary.line_items and _mean_confidence(secondary.line_items) > _mean_confidence(
        merged.line_items
    ):
        merged.line_items = secondary.line_items

    return merged


def _mean_confidence(items: list) -> float:
    if not items:
        return 0.0
    return sum(item.confidence for item in items) / len(items)
