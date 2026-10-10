"""Image Sanitizer Interface (ABC) – content-based validation of uploaded images."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SanitizedImage:
    """A re-encoded image without metadata, ready to be stored."""

    data: bytes
    extension: str  # ".jpg", ".png" or ".webp"
    width: int
    height: int


class IImageSanitizer(ABC):
    """Verify that bytes really are a supported raster image and re-encode them safely."""

    @abstractmethod
    def sanitize(self, raw: bytes) -> SanitizedImage:
        """Return the cleaned image; raise ValidationException for anything else."""
