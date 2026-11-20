"""OCR provider chain.

Tries each configured provider in order and returns the first usable result.
Order matters commercially: `pdf_text` is free, `google_vision` costs money per
page, `tesseract` costs nothing but is less accurate — so the chain is also a
cost-control mechanism, not just a fallback list.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ocr.base import OcrError, OcrOutput, OcrProvider
from app.services.ocr.google_vision import GoogleVisionProvider
from app.services.ocr.pdf_text import PdfTextProvider
from app.services.ocr.stub import StubProvider
from app.services.ocr.tesseract import TesseractProvider

logger = get_logger(__name__)

PROVIDER_CLASSES: dict[str, type[OcrProvider]] = {
    PdfTextProvider.name: PdfTextProvider,
    GoogleVisionProvider.name: GoogleVisionProvider,
    TesseractProvider.name: TesseractProvider,
    StubProvider.name: StubProvider,
}


def build_chain(names: list[str] | None = None) -> list[OcrProvider]:
    selected = names if names is not None else settings.ocr_provider_list
    chain: list[OcrProvider] = []
    for name in selected:
        provider_class = PROVIDER_CLASSES.get(name)
        if provider_class is None:
            logger.warning("Unknown OCR provider configured", extra={"provider": name})
            continue
        chain.append(provider_class())
    return chain


def run_ocr(data: bytes, mime_type: str, chain: list[OcrProvider] | None = None) -> OcrOutput:
    """Run the provider chain and return the first non-empty result."""
    providers = chain if chain is not None else build_chain()
    attempted: list[str] = []
    warnings: list[str] = []

    for provider in providers:
        if not provider.supports(mime_type):
            continue
        if not provider.is_available():
            warnings.append(f"{provider.name}: not available")
            continue

        attempted.append(provider.name)
        try:
            output = provider.run(data, mime_type)
        except OcrError as exc:
            logger.info("OCR provider declined", extra={"provider": provider.name, "reason": str(exc)})
            warnings.append(f"{provider.name}: {exc}")
            continue
        except Exception as exc:  # a provider bug must not take down processing
            logger.exception("OCR provider crashed", extra={"provider": provider.name})
            warnings.append(f"{provider.name}: unexpected error {exc}")
            continue

        if output.is_empty():
            warnings.append(f"{provider.name}: returned no text")
            continue

        output.warnings.extend(warnings)
        return output

    raise OcrError(
        "No OCR provider produced text for this document. "
        f"Attempted: {attempted or 'none'}. Details: {'; '.join(warnings) or 'no providers configured'}"
    )
