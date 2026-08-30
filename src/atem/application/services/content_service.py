"""Application Service for In-Context Content Management and Versioning."""

from uuid import UUID

import structlog

from atem.application.dto.content import (
    ContentBlockResponseDTO,
    ContentHistoryModalDTO,
    ContentVersionItemDTO,
    SaveContentBlockRequestDTO,
)
from atem.domain.exceptions import EntityNotFoundException, ValidationException
from atem.domain.interfaces.content_repository import IContentRepository
from atem.domain.models.content import ContentBlockType

logger = structlog.get_logger(__name__)


class ContentService:
    """Orchestrates live content retrieval, in-context editing, and immutable version tracking."""

    def __init__(self, content_repository: IContentRepository) -> None:
        self._repository = content_repository

    async def get_content_map(self) -> dict[str, ContentBlockResponseDTO]:
        """Fetch all content blocks mapped by their keys for template rendering."""
        blocks = await self._repository.get_all_blocks()
        return {key: ContentBlockResponseDTO.model_validate(block) for key, block in blocks.items()}

    async def get_block(self, key: str) -> ContentBlockResponseDTO:
        """Fetch a single content block by key."""
        block = await self._repository.get_block(key)
        if not block:
            raise EntityNotFoundException("ContentBlock", key)
        return ContentBlockResponseDTO.model_validate(block)

    async def save_block_content(
        self,
        key: str,
        dto: SaveContentBlockRequestDTO,
        author_name: str,
        author_id: UUID | None = None,
    ) -> ContentBlockResponseDTO:
        """Save a new version of the specified content block."""
        clean_content = dto.content.strip()
        if not clean_content:
            raise ValidationException("Content cannot be empty.")

        existing_block = await self._repository.get_block(key)
        if existing_block and existing_block.current_content.strip() == clean_content:
            logger.info(
                "content_unchanged_skipping_version",
                key=key,
                version=existing_block.current_version_number,
            )
            return ContentBlockResponseDTO.model_validate(existing_block)

        await self._repository.save_version(
            key=key,
            content=clean_content,
            author_name=author_name,
            author_id=author_id,
            change_summary=dto.change_summary or "In-Context Editierung",
        )

        updated_block = await self._repository.get_block(key)
        if not updated_block:
            raise EntityNotFoundException("ContentBlock", key)

        logger.info(
            "content_version_saved",
            key=key,
            new_version=updated_block.current_version_number,
            author=author_name,
        )
        return ContentBlockResponseDTO.model_validate(updated_block)

    async def get_block_history(self, key: str) -> ContentHistoryModalDTO:
        """Fetch the full audit trail and version history for a content block."""
        block = await self._repository.get_block(key)
        if not block:
            raise EntityNotFoundException("ContentBlock", key)

        versions = await self._repository.get_version_history(key)
        is_img = block.block_type == ContentBlockType.IMAGE_URL

        version_items: list[ContentVersionItemDTO] = []
        for v in versions:
            version_items.append(
                ContentVersionItemDTO(
                    id=v.id,
                    block_key=v.block_key,
                    version_number=v.version_number,
                    content=v.content,
                    author_name=v.author_name,
                    author_id=v.author_id,
                    change_summary=v.change_summary,
                    created_at=v.created_at,
                    formatted_date=v.created_at.strftime("%d.%m.%Y, %H:%M Uhr"),
                    is_current=(v.version_number == block.current_version_number),
                    is_image=is_img,
                )
            )

        return ContentHistoryModalDTO(
            block_key=block.key,
            block_type=block.block_type,
            current_version=block.current_version_number,
            versions=version_items,
        )

    async def restore_block_version(
        self,
        key: str,
        target_version_number: int,
        author_name: str,
        author_id: UUID | None = None,
    ) -> ContentBlockResponseDTO:
        """Restore an older historical version as the next higher version number."""
        block = await self._repository.get_block(key)
        if not block:
            raise EntityNotFoundException("ContentBlock", key)

        await self._repository.restore_version(
            key=key,
            target_version_number=target_version_number,
            author_name=author_name,
            author_id=author_id,
        )

        updated_block = await self._repository.get_block(key)
        if not updated_block:
            raise EntityNotFoundException("ContentBlock", key)

        logger.info(
            "content_version_restored",
            key=key,
            from_version=target_version_number,
            new_version=updated_block.current_version_number,
            author=author_name,
        )
        return ContentBlockResponseDTO.model_validate(updated_block)
