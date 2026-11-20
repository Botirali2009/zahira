#!/usr/bin/env python
"""Field-level extraction accuracy harness.

Phase 2.7 and gate G3 are stated in accuracy percentages ("85%+ on beta customer
documents"). A number nobody can reproduce is not a gate, so this script makes
accuracy a command you can run:

    python scripts/eval_extraction.py --count 300
    python scripts/eval_extraction.py --count 300 --via-pdf --json report.json

`--via-pdf` renders each invoice to a real PDF and pushes it through the actual
OCR chain, so it measures the deployed pipeline rather than the parser alone.

The corpus is synthetic. It measures whether the parser handles the layouts,
scripts and number formats it claims to handle — it does not prove anything
about a specific customer's documents. Only the beta measures that.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.extract.base import ExtractionContext, ExtractionResult  # noqa: E402
from app.services.extract.rules import RuleBasedExtractor  # noqa: E402
from app.services.ocr.registry import run_ocr  # noqa: E402
from app.services.script_detect import annotate_blocks, summarize_blocks  # noqa: E402
from app.services.templates import KnownParty, apply_known_parties  # noqa: E402
from app.services.validate import validate_extraction  # noqa: E402
from app.testing.corpus import (  # noqa: E402
    LAYOUTS,
    STYLES,
    InvoiceSpec,
    add_ocr_noise,
    degrade_lines,
    known_parties,
    random_invoice,
    render_pdf,
    render_text,
)

SCORED_FIELDS = (
    "invoice_number",
    "invoice_date",
    "vendor_name",
    "vendor_tin",
    "buyer_name",
    "buyer_tin",
    "subtotal",
    "vat_amount",
    "total_amount",
    "currency",
)

MONEY_FIELDS = {"subtotal", "vat_amount", "total_amount"}

# Fields below this confidence are surfaced in the review UI as "check this".
# The number that decides whether this product is safe to sell is not accuracy,
# it is the *silent* error rate: values that are wrong AND confident, because
# those are the ones that reach a tax filing without a human ever looking.
REVIEW_THRESHOLD = 0.85


def normalize_text(value: Any) -> str:
    return " ".join(str(value).split()).casefold()


def values_match(field: str, expected: Any, actual: Any) -> bool:
    if actual is None or actual == "":
        return False
    if field in MONEY_FIELDS:
        try:
            return Decimal(str(expected)) == Decimal(str(actual))
        except Exception:
            return False
    if field == "invoice_date":
        return str(expected) == str(actual)
    return normalize_text(expected) == normalize_text(actual)


def score_line_items(spec: InvoiceSpec, result: ExtractionResult) -> tuple[int, int]:
    """Return (matched rows, expected rows). A row matches on description+amount."""
    expected = {
        (normalize_text(item.description), Decimal(str(item.amount)))
        for item in spec.line_items
    }
    actual = set()
    for item in result.line_items:
        if item.amount is None or item.description is None:
            continue
        try:
            actual.add((normalize_text(item.description), Decimal(str(item.amount))))
        except Exception:
            continue
    return len(expected & actual), len(expected)


def run_one(
    spec: InvoiceSpec,
    seed: int,
    via_pdf: bool,
    noise: float = 0.0,
    registry: dict[str, KnownParty] | None = None,
) -> tuple[ExtractionResult, str]:
    if via_pdf:
        data = render_pdf(spec, seed=seed)
        output = run_ocr(data, "application/pdf")
        blocks = annotate_blocks([block.to_dict() for block in output.blocks])
        context = ExtractionContext(blocks=blocks, script_summary=summarize_blocks(blocks))
        text = output.text
    else:
        text = render_text(spec, seed=seed)
        context = ExtractionContext()

    if noise > 0:
        text = degrade_lines(add_ocr_noise(text, rate=noise, seed=seed), seed=seed)

    result = RuleBasedExtractor().extract(text, context)
    if registry:
        # Models the steady state: the customer has already confirmed at least
        # one invoice from this supplier, so the name can be repaired from their
        # own saved counterparty list.
        apply_known_parties(result, registry)
    # Validation is part of the pipeline, not a reporting step: it is what moves
    # confidence down on values the arithmetic disagrees with.
    validate_extraction(result, vat_rate_percent=float(context.vat_rate_percent))
    return result, text


def build_registry() -> dict[str, KnownParty]:
    """Seed a counterparty registry with every corpus party, in all scripts."""
    return {
        tin: KnownParty(tin=tin, name=names[0], seen_count=10, aliases=list(names))
        for tin, names in known_parties().items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=200, help="invoices to generate")
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--via-pdf", action="store_true", help="render to PDF and run the OCR chain")
    parser.add_argument("--registry", action="store_true",
                        help="simulate a customer who has already confirmed these suppliers once")
    parser.add_argument("--noise", type=float, default=0.0,
                        help="simulated OCR character error rate (0.02 = clean scan, 0.10 = phone photo)")
    parser.add_argument("--json", type=Path, help="write the full report as JSON")
    parser.add_argument("--show-failures", type=int, default=3, help="print N failing documents")
    parser.add_argument("--fail-under", type=float, default=0.0,
                        help="exit non-zero if overall field accuracy is below this (0-1)")
    args = parser.parse_args()

    hits: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    by_style: dict[str, list[float]] = defaultdict(list)
    by_layout: dict[str, list[float]] = defaultdict(list)
    line_hits = line_total = 0
    confidences: list[float] = []
    failures: list[dict[str, Any]] = []
    flagged_errors = 0
    false_alarms = 0
    silent_errors: list[str] = []
    silent_by_field: dict[str, int] = defaultdict(int)
    registry = build_registry() if args.registry else None

    for index in range(args.count):
        seed = args.seed + index
        spec = random_invoice(seed=seed)
        try:
            result, text = run_one(spec, seed, args.via_pdf, noise=args.noise, registry=registry)
        except Exception as exc:  # a crash is a total miss, not a stopped run
            for name in SCORED_FIELDS:
                totals[name] += 1
            failures.append({"seed": seed, "error": repr(exc), "style": spec.style})
            continue

        expected = spec.expected_fields()
        document_hits = 0
        missed: list[str] = []
        for name in SCORED_FIELDS:
            totals[name] += 1
            entry = result.get(name)
            actual = entry.value
            flagged = entry.confidence < REVIEW_THRESHOLD
            if values_match(name, expected[name], actual):
                hits[name] += 1
                document_hits += 1
                if flagged:
                    false_alarms += 1
            else:
                if flagged:
                    flagged_errors += 1
                else:
                    silent_by_field[name] += 1
                    silent_errors.append(f"{name} (conf {entry.confidence:.2f}): "
                                         f"expected {expected[name]!r}, got {actual!r}")
                missed.append(f"{name}: expected {expected[name]!r}, got {actual!r}"
                              f"{' [flagged]' if flagged else ' [SILENT]'}")

        matched_rows, expected_rows = score_line_items(spec, result)
        line_hits += matched_rows
        line_total += expected_rows

        ratio = document_hits / len(SCORED_FIELDS)
        by_style[spec.style].append(ratio)
        by_layout[spec.layout].append(ratio)
        confidences.append(result.overall_confidence)

        if missed and len(failures) < args.show_failures:
            failures.append({
                "seed": seed,
                "style": spec.style,
                "layout": spec.layout,
                "missed": missed,
                "text": text,
            })

    total_fields = sum(totals.values())
    total_hits = sum(hits.values())
    overall = total_hits / total_fields if total_fields else 0.0

    print(f"\nDocuments: {args.count}   mode: {'pdf+ocr' if args.via_pdf else 'text'}"
          f"   noise: {args.noise:.0%}   registry: {'on' if args.registry else 'off'}")
    print(f"Overall field accuracy: {overall:.1%}  ({total_hits}/{total_fields})")
    if line_total:
        print(f"Line-item row accuracy: {line_hits / line_total:.1%}  ({line_hits}/{line_total})")
    if confidences:
        print(f"Mean self-reported confidence: {sum(confidences) / len(confidences):.1%}")

    errors = total_fields - total_hits
    silent_count = len(silent_errors)
    print(f"\nReview safety (threshold {REVIEW_THRESHOLD:.0%}):")
    print(f"  Wrong fields:            {errors} ({errors / total_fields:.1%} of all fields)")
    if errors:
        print(f"    caught by low confidence: {flagged_errors} ({flagged_errors / errors:.1%} of errors)")
        print(f"    SILENT (wrong+confident): {silent_count} ({silent_count / errors:.1%} of errors)")
    print(f"  Silent error rate:       {silent_count / total_fields:.2%} of all fields")
    print(f"  False alarms:            {false_alarms} correct fields flagged "
          f"({false_alarms / total_fields:.1%})")
    if silent_by_field:
        print("  Silent errors by field:  " + ", ".join(
            f"{name}={count}" for name, count in
            sorted(silent_by_field.items(), key=lambda pair: -pair[1])))

    print("\nPer field:")
    for name in SCORED_FIELDS:
        count = totals[name]
        accuracy = hits[name] / count if count else 0.0
        flag = "  <-- below 85%" if accuracy < 0.85 else ""
        print(f"  {name:<16} {accuracy:>7.1%}  ({hits[name]}/{count}){flag}")

    print("\nPer script mix:")
    for style in STYLES:
        scores = by_style.get(style, [])
        if scores:
            print(f"  {style:<14} {sum(scores) / len(scores):>7.1%}  (n={len(scores)})")

    print("\nPer layout:")
    for layout in LAYOUTS:
        scores = by_layout.get(layout, [])
        if scores:
            print(f"  {layout:<14} {sum(scores) / len(scores):>7.1%}  (n={len(scores)})")

    if failures and args.show_failures:
        print("\n--- sample failures ---")
        for failure in failures[: args.show_failures]:
            print(f"\nseed={failure['seed']} style={failure.get('style')} layout={failure.get('layout')}")
            for line in failure.get("missed", []):
                print(f"   {line}")
            if failure.get("error"):
                print(f"   ERROR {failure['error']}")

    if args.json:
        report = {
            "count": args.count,
            "mode": "pdf+ocr" if args.via_pdf else "text",
            "overall_field_accuracy": overall,
            "line_item_accuracy": (line_hits / line_total) if line_total else None,
            "per_field": {name: (hits[name] / totals[name]) if totals[name] else 0.0
                          for name in SCORED_FIELDS},
            "per_style": {style: (sum(scores) / len(scores)) if scores else None
                          for style, scores in by_style.items()},
            "per_layout": {layout: (sum(scores) / len(scores)) if scores else None
                           for layout, scores in by_layout.items()},
        }
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {args.json}")

    if args.fail_under and overall < args.fail_under:
        print(f"\nFAIL: {overall:.1%} is below the required {args.fail_under:.1%}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
