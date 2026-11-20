"""Text-layer extraction for born-digital PDFs.

Uzbekistan's e-invoicing mandate (2020, expanded through 2024) means a growing
share of incoming documents are PDFs with a real text layer rather than scans.
Reading that layer costs nothing, takes milliseconds and is 100% accurate, so it
runs first in the chain and skips the paid OCR call entirely.
"""

from __future__ import annotations

import io
import time

from app.core.logging import get_logger
from app.services.ocr.base import OcrBlock, OcrError, OcrOutput, OcrProvider

logger = get_logger(__name__)

# Below this many characters per page the "text layer" is usually just a
# scanner watermark, so fall through to real OCR instead.
MIN_CHARS_PER_PAGE = 40


class PdfTextProvider(OcrProvider):
    name = "pdf_text"
    supported_mime_prefixes = ("application/pdf",)

    def is_available(self) -> bool:
        try:
            import pypdf  # noqa: F401, PLC0415
        except ImportError:  # pragma: no cover - dependency is pinned
            return False
        return True

    def run(self, data: bytes, mime_type: str) -> OcrOutput:
        from pypdf import PdfReader  # noqa: PLC0415

        started = time.perf_counter()
        try:
            reader = PdfReader(io.BytesIO(data))
        except Exception as exc:  # pypdf raises a wide range of parse errors
            raise OcrError(f"Cannot parse PDF: {exc}") from exc

        blocks: list[OcrBlock] = []
        total_chars = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # a single broken page must not kill the doc
                logger.warning("pdf_text page failed", extra={"page": page_number, "error": str(exc)})
                continue
            total_chars += len(text.strip())
            for line in text.splitlines():
                stripped = line.strip()
                if stripped:
                    # Digital text is exact; the residual uncertainty is layout,
                    # not character recognition.
                    blocks.append(OcrBlock(text=stripped, page=page_number, confidence=0.99))

        page_count = len(reader.pages)
        duration_ms = int((time.perf_counter() - started) * 1000)

        if page_count and total_chars / page_count < MIN_CHARS_PER_PAGE:
            raise OcrError(
                f"PDF has no usable text layer ({total_chars} chars over {page_count} pages)"
            )

        return OcrOutput(
            provider=self.name,
            blocks=blocks,
            page_count=page_count,
            duration_ms=duration_ms,
            mean_confidence=0.99 if blocks else None,
        )
