"""Image preprocessing before OCR.

Uzbek office scans are rarely clean: 150-200 DPI, skewed on the glass, and often
a photocopy of a photocopy with a stamp across the total. Deskewing and
contrast normalisation before OCR is the cheapest accuracy gain available — it
costs milliseconds and needs no model.
"""

from __future__ import annotations

import io
import math

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from app.core.logging import get_logger

logger = get_logger(__name__)

# Below this width, characters are too few pixels tall for reliable OCR, so the
# page is upscaled before recognition.
MIN_WIDTH_PX = 1600
MAX_WIDTH_PX = 4000
MAX_SKEW_DEGREES = 8.0
SKEW_SEARCH_STEP = 0.5


def preprocess_image(data: bytes, deskew: bool = True) -> bytes:
    """Return a cleaned-up PNG ready for OCR. Falls back to the original bytes."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as exc:
        logger.warning("preprocess: cannot open image", extra={"error": str(exc)})
        return data

    try:
        image = ImageOps.exif_transpose(image)
        if image.mode != "L":
            image = image.convert("L")

        image = _resize_for_ocr(image)
        image = ImageOps.autocontrast(image, cutoff=1)
        image = image.filter(ImageFilter.MedianFilter(size=3))

        if deskew:
            angle = estimate_skew(image)
            if abs(angle) >= SKEW_SEARCH_STEP:
                image = image.rotate(
                    angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255
                )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
    except Exception as exc:
        logger.warning("preprocess failed, using original", extra={"error": str(exc)})
        return data


def _resize_for_ocr(image: Image.Image) -> Image.Image:
    width, height = image.size
    if width < MIN_WIDTH_PX:
        scale = MIN_WIDTH_PX / width
    elif width > MAX_WIDTH_PX:
        scale = MAX_WIDTH_PX / width
    else:
        return image
    return image.resize(
        (int(width * scale), int(height * scale)), resample=Image.Resampling.LANCZOS
    )


def estimate_skew(image: Image.Image) -> float:
    """Estimate page rotation by maximising horizontal projection variance.

    Text lines produce sharp peaks in the row-sum profile only when they are
    horizontal, so the angle whose profile varies most is the deskew angle.
    Cheap, dependency-free, and accurate to about half a degree — enough, since
    OCR engines tolerate small residual skew.
    """
    thumbnail = image.copy()
    thumbnail.thumbnail((800, 800), Image.Resampling.BILINEAR)
    array = np.asarray(thumbnail, dtype=np.float32)
    if array.ndim != 2 or array.size == 0:
        return 0.0

    # Ink as high values so row sums track text density.
    binary = (array < array.mean()).astype(np.float32)
    if binary.sum() == 0:
        return 0.0

    best_angle = 0.0
    best_score = -1.0
    steps = int(MAX_SKEW_DEGREES / SKEW_SEARCH_STEP)
    for step in range(-steps, steps + 1):
        angle = step * SKEW_SEARCH_STEP
        score = _projection_score(binary, angle)
        if score > best_score:
            best_score, best_angle = score, angle
    return best_angle


def _projection_score(binary: np.ndarray, angle: float) -> float:
    if angle == 0.0:
        profile = binary.sum(axis=1)
    else:
        # Shear rows instead of rotating: for angles this small the difference
        # is negligible and a shear is far cheaper than an interpolated rotate.
        height, width = binary.shape
        shift_per_row = math.tan(math.radians(angle))
        rows = np.arange(height)
        shifts = np.round((rows - height / 2) * shift_per_row).astype(int)
        profile = np.empty(height, dtype=np.float32)
        for row in range(height):
            shift = shifts[row]
            if shift == 0:
                profile[row] = binary[row].sum()
            elif shift > 0:
                profile[row] = binary[row, :max(width - shift, 0)].sum()
            else:
                profile[row] = binary[row, -shift:].sum()
    return float(np.var(profile))


def is_image(mime_type: str) -> bool:
    return mime_type.startswith("image/")


def page_count_of_pdf(data: bytes) -> int | None:
    try:
        from pypdf import PdfReader  # noqa: PLC0415

        return len(PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return None
