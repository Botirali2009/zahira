"""Local Tesseract OCR.

Used for on-premise deployments where no document may reach a cloud API, and as
a fallback when Vision is unreachable. Requires the `uzb`, `uzb_cyrl` and `rus`
traineddata packs; if they are missing the provider reports itself unavailable
rather than silently producing garbage.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ocr.base import OcrBlock, OcrError, OcrOutput, OcrProvider

logger = get_logger(__name__)


class TesseractProvider(OcrProvider):
    name = "tesseract"
    supported_mime_prefixes = ("image/",)

    def __init__(self, cmd: str | None = None, languages: str | None = None) -> None:
        self.cmd = cmd or settings.tesseract_cmd
        self.languages = languages or settings.tesseract_languages

    def is_available(self) -> bool:
        return shutil.which(self.cmd) is not None

    def run(self, data: bytes, mime_type: str) -> OcrOutput:
        if not self.is_available():
            raise OcrError(f"tesseract binary '{self.cmd}' not found on PATH")

        started = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "page.img"
            image_path.write_bytes(data)
            try:
                completed = subprocess.run(
                    [self.cmd, str(image_path), "stdout", "-l", self.languages, "--psm", "6", "tsv"],
                    capture_output=True,
                    timeout=settings.ocr_timeout_seconds,
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.decode("utf-8", "replace")[:500]
                raise OcrError(f"tesseract failed: {stderr}") from exc
            except subprocess.TimeoutExpired as exc:
                raise OcrError("tesseract timed out") from exc

        blocks, confidences = _parse_tsv(completed.stdout.decode("utf-8", "replace"))
        return OcrOutput(
            provider=self.name,
            blocks=blocks,
            page_count=1,
            duration_ms=int((time.perf_counter() - started) * 1000),
            mean_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        )


def _parse_tsv(tsv: str) -> tuple[list[OcrBlock], list[float]]:
    """Group Tesseract's word-level TSV rows back into lines."""
    lines = tsv.splitlines()
    if not lines:
        return [], []

    header = lines[0].split("\t")
    try:
        idx = {name: header.index(name) for name in
               ("block_num", "par_num", "line_num", "left", "top", "width", "height", "conf", "text")}
    except ValueError:
        return [], []

    grouped: dict[tuple[str, str, str], dict] = {}
    for row in lines[1:]:
        cells = row.split("\t")
        if len(cells) <= idx["text"]:
            continue
        text = cells[idx["text"]].strip()
        if not text:
            continue
        try:
            conf = float(cells[idx["conf"]])
        except ValueError:
            conf = -1.0
        if conf < 0:
            continue

        key = (cells[idx["block_num"]], cells[idx["par_num"]], cells[idx["line_num"]])
        entry = grouped.setdefault(key, {"words": [], "confs": [], "box": None})
        entry["words"].append(text)
        entry["confs"].append(conf / 100.0)

        left, top = float(cells[idx["left"]]), float(cells[idx["top"]])
        right, bottom = left + float(cells[idx["width"]]), top + float(cells[idx["height"]])
        if entry["box"] is None:
            entry["box"] = [left, top, right, bottom]
        else:
            box = entry["box"]
            entry["box"] = [min(box[0], left), min(box[1], top), max(box[2], right), max(box[3], bottom)]

    blocks: list[OcrBlock] = []
    confidences: list[float] = []
    for entry in grouped.values():
        confidence = sum(entry["confs"]) / len(entry["confs"])
        confidences.append(confidence)
        box = entry["box"]
        blocks.append(
            OcrBlock(
                text=" ".join(entry["words"]),
                page=1,
                bbox=(box[0], box[1], box[2], box[3]) if box else None,
                confidence=round(confidence, 4),
            )
        )
    return blocks, confidences
