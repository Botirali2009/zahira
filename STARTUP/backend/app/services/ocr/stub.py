"""Deterministic OCR provider for tests and demos.

Returns text queued by the caller, so pipeline behaviour can be tested without
network access, API keys or image fixtures.
"""

from __future__ import annotations

from app.services.ocr.base import OcrBlock, OcrError, OcrOutput, OcrProvider


class StubProvider(OcrProvider):
    name = "stub"

    #: Queue of texts to return, one per call. Falls back to `default_text`.
    queue: list[str] = []
    default_text: str = ""

    def is_available(self) -> bool:
        return bool(self.queue or self.default_text)

    def run(self, data: bytes, mime_type: str) -> OcrOutput:
        text = self.queue.pop(0) if self.queue else self.default_text
        if not text:
            raise OcrError("stub provider has no text queued")
        blocks = [
            OcrBlock(text=line.strip(), page=1, confidence=0.95)
            for line in text.splitlines()
            if line.strip()
        ]
        return OcrOutput(provider=self.name, blocks=blocks, page_count=1, duration_ms=1,
                         mean_confidence=0.95)

    @classmethod
    def push(cls, text: str) -> None:
        cls.queue.append(text)

    @classmethod
    def reset(cls) -> None:
        cls.queue = []
        cls.default_text = ""
