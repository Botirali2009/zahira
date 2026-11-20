"""Google Cloud Vision OCR.

Primary engine for scanned pages during months 1-9 of the plan: ~$1.50 per 1,000
pages, native Cyrillic, no model training required. Language hints are set to
Uzbek + Russian + English because a single Uzbek invoice commonly carries all
three.

Replaced later by a fine-tuned PaddleOCR deployment (see docs/architecture.md,
"self-hosted transition"); the provider interface is the seam that makes that
swap a config change.
"""

from __future__ import annotations

import base64
import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ocr.base import OcrBlock, OcrError, OcrOutput, OcrProvider

logger = get_logger(__name__)

LANGUAGE_HINTS = ["uz", "ru", "en"]


class GoogleVisionProvider(OcrProvider):
    name = "google_vision"
    supported_mime_prefixes = ("image/", "application/pdf")

    def __init__(self, api_key: str | None = None, endpoint: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.google_vision_api_key
        self.endpoint = endpoint or settings.google_vision_endpoint

    def is_available(self) -> bool:
        return bool(self.api_key)

    def run(self, data: bytes, mime_type: str) -> OcrOutput:
        if not self.is_available():
            raise OcrError("Google Vision API key is not configured")

        started = time.perf_counter()
        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(data).decode("ascii")},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    "imageContext": {"languageHints": LANGUAGE_HINTS},
                }
            ]
        }
        try:
            response = httpx.post(
                self.endpoint,
                params={"key": self.api_key},
                json=payload,
                timeout=settings.ocr_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise OcrError(f"Google Vision request failed: {exc}") from exc

        responses = body.get("responses") or [{}]
        first = responses[0]
        if "error" in first:
            raise OcrError(f"Google Vision error: {first['error'].get('message')}")

        annotation = first.get("fullTextAnnotation") or {}
        blocks, confidences = self._parse_annotation(annotation)

        duration_ms = int((time.perf_counter() - started) * 1000)
        return OcrOutput(
            provider=self.name,
            blocks=blocks,
            page_count=len(annotation.get("pages", [])) or 1,
            duration_ms=duration_ms,
            mean_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        )

    @staticmethod
    def _parse_annotation(annotation: dict) -> tuple[list[OcrBlock], list[float]]:
        """Flatten Vision's page/block/paragraph/word/symbol tree into lines.

        Vision does not emit line breaks as structure — they arrive as a
        `detectedBreak` property on the last symbol of a line, so lines have to
        be rebuilt symbol by symbol.
        """
        blocks: list[OcrBlock] = []
        confidences: list[float] = []

        for page_index, page in enumerate(annotation.get("pages", []), start=1):
            for block in page.get("blocks", []):
                for paragraph in block.get("paragraphs", []):
                    current: list[str] = []
                    for word in paragraph.get("words", []):
                        word_text = "".join(
                            symbol.get("text", "") for symbol in word.get("symbols", [])
                        )
                        current.append(word_text)
                        breaks = [
                            symbol.get("property", {}).get("detectedBreak", {}).get("type")
                            for symbol in word.get("symbols", [])
                        ]
                        if any(brk in ("LINE_BREAK", "EOL_SURE_SPACE") for brk in breaks):
                            text = " ".join(current).strip()
                            current = []
                            if not text:
                                continue
                            confidence = paragraph.get("confidence")
                            if confidence is not None:
                                confidences.append(float(confidence))
                            blocks.append(
                                OcrBlock(
                                    text=text,
                                    page=page_index,
                                    bbox=_bbox_from_vertices(
                                        paragraph.get("boundingBox", {}).get("vertices", [])
                                    ),
                                    confidence=confidence,
                                )
                            )
                    if current:
                        text = " ".join(current).strip()
                        if text:
                            confidence = paragraph.get("confidence")
                            if confidence is not None:
                                confidences.append(float(confidence))
                            blocks.append(
                                OcrBlock(
                                    text=text,
                                    page=page_index,
                                    bbox=_bbox_from_vertices(
                                        paragraph.get("boundingBox", {}).get("vertices", [])
                                    ),
                                    confidence=confidence,
                                )
                            )

        if not blocks and annotation.get("text"):
            # Older API shapes only return the flat text field.
            blocks = [
                OcrBlock(text=line.strip(), page=1)
                for line in str(annotation["text"]).splitlines()
                if line.strip()
            ]
        return blocks, confidences


def _bbox_from_vertices(vertices: list[dict]) -> tuple[float, float, float, float] | None:
    if not vertices:
        return None
    xs = [float(vertex.get("x", 0)) for vertex in vertices]
    ys = [float(vertex.get("y", 0)) for vertex in vertices]
    return (min(xs), min(ys), max(xs), max(ys))
