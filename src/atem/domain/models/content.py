"""Domain Models for Live In-Context Content Management and Versioning."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from atem.domain.models.base import BaseEntity

# Content keys are dotted identifiers such as "hero.title" or "quotes.3.author".
CONTENT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+){1,4}$")
# Image blocks may only reference uploaded media or bundled theme images.
IMAGE_PATH_PATTERN = re.compile(r"^/(media|static/images)/[A-Za-z0-9_.-]{1,120}$")
MAX_CONTENT_LENGTH = 10_000


class ContentBlockType(StrEnum):
    """Supported content block rendering and editing types."""

    TEXT = "text"
    TEXTAREA = "textarea"
    RICH_TEXT = "rich_text"
    IMAGE_URL = "image"
    PHONE = "phone"
    EMAIL = "email"


@dataclass(kw_only=True)
class ContentBlock(BaseEntity):
    """A managed content element on the website (e.g. title, paragraph, image)."""

    key: str
    section: str
    block_type: ContentBlockType
    current_version_number: int
    current_content: str


@dataclass(kw_only=True)
class ContentBlockVersion:
    """An immutable version record of a content block (Append-Only Audit Log)."""

    id: UUID = field(default_factory=uuid4)
    block_key: str
    version_number: int
    content: str
    author_name: str
    author_id: UUID | None = None
    change_summary: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        block_key: str,
        version_number: int,
        content: str,
        author_name: str,
        *,
        author_id: UUID | None = None,
        change_summary: str | None = None,
    ) -> "ContentBlockVersion":
        """Factory method to create a new content version snapshot."""
        return cls(
            id=uuid4(),
            block_key=block_key,
            version_number=version_number,
            content=content,
            author_id=author_id,
            author_name=author_name,
            change_summary=change_summary,
            created_at=datetime.now(UTC),
        )
