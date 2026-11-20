"""Vendor template learning and counterparty canonicalisation.

Two mechanisms, both fed by human corrections:

1. **Counterparty canonicalisation.** A company invoices the same suppliers over
   and over. Once a vendor's name has been confirmed by a human against its
   STIR, every later invoice from that STIR can have an OCR-damaged name
   repaired from the registry — `"СИФАТ МЕБЕЛ"` becomes `"СИФАТ МЕБЕЛЬ"` again.
   This matters beyond cosmetics: 1C matches counterparties by name, so a
   one-character difference silently creates a duplicate counterparty record.

2. **Layout hints.** After enough corrections on one vendor's format, the labels
   that actually work for that vendor are recorded and tried first. This is the
   mechanism behind the "80% inference cost reduction for repeat vendors" claim
   in the deep dive — a resolved template needs no LLM call at all.

Both are per-company. Vendor knowledge is never shared across tenants: one
customer's supplier list is competitively sensitive information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Correction, Extraction, VendorTemplate
from app.services.extract.base import ExtractionResult, FieldValue
from app.services.extract.parsers import is_valid_tin
from app.services.script_detect import fold_confusables, lower_preserving_length

logger = get_logger(__name__)

# Above this similarity, a differing name is treated as OCR damage to a known
# counterparty. Below it, it is treated as a genuinely different party and the
# extracted value is kept but flagged.
NAME_REPAIR_THRESHOLD = 0.75
CONF_REGISTRY_CANONICAL = 0.90
CONF_REGISTRY_CONFLICT = 0.50


@dataclass
class KnownParty:
    """A confirmed counterparty and every spelling of it we have accepted.

    Aliases exist because of the script transition: the same supplier issues
    `"OLTIN VODIY SAVDO" MChJ` on one invoice and `"ОЛТИН ВОДИЙ САВДО" МЧЖ` on
    the next. Both are correct, neither is a typo, and a registry that stored
    only one would flag every invoice in the other script as a conflict.
    """

    tin: str
    name: str
    seen_count: int = 0
    hints: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)

    def all_names(self) -> list[str]:
        names = [self.name] if self.name else []
        names.extend(alias for alias in self.aliases if alias and alias != self.name)
        return names

    def best_match(self, candidate: str) -> tuple[str | None, float]:
        """The stored spelling closest to `candidate`, with its similarity."""
        best_name: str | None = None
        best_ratio = 0.0
        for name in self.all_names():
            ratio = similarity(candidate, name)
            if ratio > best_ratio:
                best_name, best_ratio = name, ratio
        return best_name, best_ratio


def normalize_for_compare(text: str) -> str:
    """Fold case, homoglyphs and punctuation so only real differences remain."""
    folded = fold_confusables(lower_preserving_length(str(text)))
    return "".join(char for char in folded if char.isalnum())


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_for_compare(left), normalize_for_compare(right)).ratio()


def apply_known_parties(
    result: ExtractionResult,
    known: dict[str, KnownParty],
    roles: tuple[str, ...] = ("vendor", "buyer"),
) -> list[dict[str, Any]]:
    """Repair counterparty names against the registry.

    Returns a list of the repairs made, so the UI can show "we corrected this
    from your saved supplier list" rather than silently rewriting what the
    document said.
    """
    repairs: list[dict[str, Any]] = []
    if not known:
        return repairs

    for role in roles:
        tin_entry = result.fields.get(f"{role}_tin")
        name_key = f"{role}_name"
        name_entry = result.fields.get(name_key)
        if tin_entry is None or not tin_entry.is_present:
            continue

        tin = str(tin_entry.value)
        if not is_valid_tin(tin):
            continue
        party = known.get(tin)
        if party is None:
            continue

        if name_entry is None or not name_entry.is_present:
            result.set(name_key, FieldValue(
                value=party.name,
                confidence=CONF_REGISTRY_CANONICAL,
                source=f"registry:tin={tin}",
            ))
            repairs.append({"field": name_key, "from": None, "to": party.name, "reason": "filled"})
            continue

        extracted = str(name_entry.value)
        matched_name, ratio = party.best_match(extracted)

        if matched_name is not None and \
                normalize_for_compare(extracted) == normalize_for_compare(matched_name):
            # Same party, only punctuation or homoglyph noise differs: keep the
            # registry spelling so 1C sees one counterparty, not two.
            if extracted != matched_name:
                name_entry.value = matched_name
                name_entry.source += "+registry_normalized"
                repairs.append({"field": name_key, "from": extracted, "to": matched_name,
                                "reason": "normalized"})
            continue

        if matched_name is not None and ratio >= NAME_REPAIR_THRESHOLD:
            name_entry.value = matched_name
            name_entry.confidence = max(name_entry.confidence, CONF_REGISTRY_CANONICAL)
            name_entry.source = f"registry:tin={tin} (repaired, similarity {ratio:.2f})"
            repairs.append({"field": name_key, "from": extracted, "to": matched_name,
                            "reason": "ocr_repair", "similarity": round(ratio, 3)})
        else:
            # Same STIR, no stored spelling close enough: either the TIN was
            # misread, the counterparty was renamed, or this is a new
            # transliteration. A human has to decide which.
            name_entry.confidence = min(name_entry.confidence, CONF_REGISTRY_CONFLICT)
            name_entry.source += f" (no registry match for STIR {tin})"
            repairs.append({"field": name_key, "from": extracted, "to": None,
                            "reason": "conflict", "registry_names": party.all_names(),
                            "similarity": round(ratio, 3)})
    return repairs


# --- Persistence ------------------------------------------------------------

def load_known_parties(db: Session, company_id: int) -> dict[str, KnownParty]:
    """Load this company's confirmed counterparties, keyed by STIR."""
    templates = db.scalars(
        select(VendorTemplate).where(VendorTemplate.company_id == company_id)
    ).all()
    return {
        template.vendor_tin: KnownParty(
            tin=template.vendor_tin,
            name=template.vendor_name or "",
            seen_count=template.sample_count,
            hints=template.hints or {},
            aliases=list((template.hints or {}).get("aliases", [])),
        )
        for template in templates
        if template.vendor_name
    }


def record_accepted_extraction(db: Session, company_id: int, extraction: Extraction) -> None:
    """Update the registry from an extraction a human has confirmed.

    Only accepted extractions count. Learning from unreviewed machine output
    would let one bad OCR result poison every later invoice from that vendor.
    """
    fields = extraction.fields or {}
    tin = _field_value(fields, "vendor_tin")
    name = _field_value(fields, "vendor_name")
    if not tin or not is_valid_tin(str(tin)):
        return

    template = db.scalar(
        select(VendorTemplate).where(
            VendorTemplate.company_id == company_id,
            VendorTemplate.vendor_tin == str(tin),
        )
    )
    if template is None:
        template = VendorTemplate(
            company_id=company_id,
            vendor_tin=str(tin),
            vendor_name=str(name) if name else None,
            hints={},
            sample_count=0,
        )
        db.add(template)

    template.sample_count += 1
    hints_aliases = list((template.hints or {}).get("aliases", []))
    if name:
        template.vendor_name = str(name)
        # Every confirmed spelling is kept, so the same supplier is recognised
        # whether the next invoice arrives in Latin or Cyrillic.
        if str(name) not in hints_aliases:
            hints_aliases.append(str(name))

    # Record which labels actually located each field for this vendor, so the
    # next invoice from them can try those first.
    hints = dict(template.hints or {})
    hints["aliases"] = hints_aliases
    for field_name, payload in fields.items():
        source = str((payload or {}).get("source") or "")
        if source.startswith("label:"):
            label = source.split("label:", 1)[1].split("+", maxsplit=1)[0]
            entry = hints.setdefault(field_name, {"labels": []})
            if label not in entry["labels"]:
                entry["labels"].append(label)
    template.hints = hints

    corrections = db.scalar(
        select(Correction.id).where(Correction.extraction_id == extraction.id).limit(1)
    )
    if corrections:
        template.correction_count += 1

    template.is_active = template.sample_count >= settings.template_learning_threshold
    logger.info(
        "vendor template updated",
        extra={
            "company_id": company_id,
            "vendor_tin": template.vendor_tin,
            "sample_count": template.sample_count,
            "is_active": template.is_active,
        },
    )


def _field_value(fields: dict[str, Any], name: str) -> Any:
    payload = fields.get(name)
    if isinstance(payload, dict):
        return payload.get("value")
    return payload


def template_hints_for(db: Session, company_id: int, vendor_tin: str | None) -> dict[str, Any]:
    if not vendor_tin:
        return {}
    template = db.scalar(
        select(VendorTemplate).where(
            VendorTemplate.company_id == company_id,
            VendorTemplate.vendor_tin == vendor_tin,
            VendorTemplate.is_active.is_(True),
        )
    )
    return dict(template.hints or {}) if template else {}
