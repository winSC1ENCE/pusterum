"""Media Application Service – uploads and the image library of the inline editor."""

import uuid
from dataclasses import dataclass
from pathlib import Path

import structlog

from atem.domain.exceptions import ValidationException
from atem.domain.interfaces.image_sanitizer import IImageSanitizer

logger = structlog.get_logger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
LISTED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})


@dataclass(frozen=True)
class MediaItem:
    """An image shown in the picker."""

    filename: str
    url: str
    size_kb: float
    source: str  # "uploads" | "theme"


class MediaService:
    """Store sanitized uploads under random names and list available images."""

    def __init__(
        self, sanitizer: IImageSanitizer, media_dir: Path, static_images_dir: Path
    ) -> None:
        self._sanitizer = sanitizer
        self._media_dir = media_dir
        self._static_images_dir = static_images_dir

    def store_upload(self, raw: bytes) -> MediaItem:
        """Validate, re-encode and store an uploaded image under a random file name."""
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValidationException("Die Datei überschreitet die maximale Grösse von 10 MB.")
        image = self._sanitizer.sanitize(raw)
        self._media_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{image.extension}"
        # "xb" refuses to overwrite – no race between existence check and write.
        with (self._media_dir / filename).open("xb") as handle:
            handle.write(image.data)
        logger.info("admin_action", action="image_uploaded", filename=filename)
        return MediaItem(
            filename=filename,
            url=f"/media/{filename}",
            size_kb=round(len(image.data) / 1024, 1),
            source="uploads",
        )

    def list_images(self) -> list[MediaItem]:
        """Uploaded images first (newest first), then bundled theme images."""
        return [
            *self._list(self._media_dir, "/media", "uploads"),
            *self._list(self._static_images_dir, "/static/images", "theme"),
        ]

    @staticmethod
    def _list(directory: Path, url_prefix: str, source: str) -> list[MediaItem]:
        if not directory.is_dir():
            return []
        files = [
            f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in LISTED_EXTENSIONS
        ]
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return [
            MediaItem(
                filename=f.name,
                url=f"{url_prefix}/{f.name}",
                size_kb=round(f.stat().st_size / 1024, 1),
                source=source,
            )
            for f in files
        ]
