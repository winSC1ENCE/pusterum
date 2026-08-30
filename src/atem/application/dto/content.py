"""Data Transfer Objects for Content Management, Inline Editing, and Versioning."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from atem.domain.models.content import ContentBlockType


class SaveContentBlockRequestDTO(BaseModel):
    """Payload for saving an edited content block."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(..., min_length=1, description="Updated text, HTML, or image path")
    change_summary: str | None = Field(default=None, max_length=255)


class ContentBlockResponseDTO(BaseModel):
    """View model for rendering content blocks in templates and inline editors."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    section: str
    block_type: ContentBlockType
    current_version_number: int
    current_content: str
    updated_at: datetime


class ContentVersionItemDTO(BaseModel):
    """Individual version entry formatted for the Audit Trail modal."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    block_key: str
    version_number: int
    content: str
    author_name: str
    author_id: UUID | None
    change_summary: str | None
    created_at: datetime
    formatted_date: str
    is_current: bool = False
    is_image: bool = False


class ContentHistoryModalDTO(BaseModel):
    """Complete dataset for rendering the Audit Trail Modal dialog."""

    model_config = ConfigDict(from_attributes=True)

    block_key: str
    block_type: ContentBlockType
    current_version: int
    versions: list[ContentVersionItemDTO]
