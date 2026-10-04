"""Pillow implementation of IImageSanitizer.

The decision is made on the *content*, never on the file name: the image is decoded,
verified, orientation-corrected, downscaled and re-encoded. Re-encoding drops every kind of
metadata (EXIF incl. GPS, XMP, ICC comments) and neutralises polyglot files (e.g. HTML or
script appended to a PNG). SVG and all other formats are rejected.
"""

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from atem.domain.exceptions import ValidationException
from atem.domain.interfaces.image_sanitizer import IImageSanitizer, SanitizedImage

MAX_DIMENSION = 2400
MAX_PIXELS = 40_000_000  # decompression-bomb guard (≈ 6300 × 6300)
JPEG_QUALITY = 85
_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
UNSUPPORTED_MESSAGE = "Ungültige Bilddatei. Erlaubt sind PNG, JPG und WEBP."


class PillowImageSanitizer(IImageSanitizer):
    """Decode, verify and re-encode PNG/JPEG/WEBP images."""

    def sanitize(self, raw: bytes) -> SanitizedImage:
        try:
            with Image.open(io.BytesIO(raw)) as probe:
                image_format = probe.format
                probe.verify()
            if image_format not in _EXTENSIONS:
                raise ValidationException(UNSUPPORTED_MESSAGE)
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > MAX_PIXELS:
                    raise ValidationException("Das Bild ist zu gross (Pixelanzahl).")
                cleaned = ImageOps.exif_transpose(image)
                cleaned.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
                return self._encode(cleaned, image_format)
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
            raise ValidationException(UNSUPPORTED_MESSAGE) from exc

    @staticmethod
    def _encode(image: Image.Image, image_format: str) -> SanitizedImage:
        buffer = io.BytesIO()
        if image_format == "JPEG":
            image.convert("RGB").save(
                buffer, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True
            )
        elif image_format == "WEBP":
            image.save(buffer, "WEBP", quality=JPEG_QUALITY, method=4)
        else:
            if image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                image = image.convert("RGBA")
            image.save(buffer, "PNG", optimize=True)
        return SanitizedImage(
            data=buffer.getvalue(),
            extension=_EXTENSIONS[image_format],
            width=image.width,
            height=image.height,
        )
