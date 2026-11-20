"""OCR provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class OcrBlock:
    """One recognised text block in reading order."""

    text: str
    page: int = 1
    # (x0, y0, x1, y1) in pixels for images, PDF points for born-digital pages.
    bbox: tuple[float, float, float, float] | None = None
    confidence: float | None = None
    script: str | None = None
    language: str | None = None
    mixed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.bbox is not None:
            data["bbox"] = [round(value, 2) for value in self.bbox]
        return data


@dataclass
class OcrOutput:
    provider: str
    blocks: list[OcrBlock] = field(default_factory=list)
    page_count: int = 0
    duration_ms: int = 0
    mean_confidence: float | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks)

    def is_empty(self) -> bool:
        return not self.text.strip()


class OcrError(RuntimeError):
    """Provider failed in a way the chain should log and step past."""


class OcrProvider(ABC):
    name: str = "base"
    #: MIME types this provider can handle at all.
    supported_mime_prefixes: tuple[str, ...] = ()

    @abstractmethod
    def is_available(self) -> bool:
        """True when the provider is configured and its dependencies are present."""

    @abstractmethod
    def run(self, data: bytes, mime_type: str) -> OcrOutput:
        """Recognise text. Raise OcrError on provider failure."""

    def supports(self, mime_type: str) -> bool:
        if not self.supported_mime_prefixes:
            return True
        return any(mime_type.startswith(prefix) for prefix in self.supported_mime_prefixes)
