"""Abstract Base Class (Port) for Content Management and Versioning."""

from abc import ABC, abstractmethod
from uuid import UUID

from atem.domain.models.content import ContentBlock, ContentBlockVersion


class IContentRepository(ABC):
    """Interface for managing site content blocks and immutable version histories."""

    @abstractmethod
    async def seed_missing_blocks(self) -> int:
        """Insert missing default content blocks; return the number inserted."""

    @abstractmethod
    async def get_block(self, key: str) -> ContentBlock | None:
        """Retrieve an active content block by its unique key."""

    @abstractmethod
    async def get_all_blocks(self) -> dict[str, ContentBlock]:
        """Retrieve all active content blocks mapped by their keys."""

    @abstractmethod
    async def save_version(
        self,
        key: str,
        content: str,
        author_name: str,
        author_id: UUID | None = None,
        change_summary: str | None = None,
    ) -> ContentBlockVersion:
        """Append a new version for a content block and update the active block content."""

    @abstractmethod
    async def get_version_history(self, key: str) -> list[ContentBlockVersion]:
        """Fetch all historical versions for a block, ordered newest first."""

    @abstractmethod
    async def restore_version(
        self,
        key: str,
        target_version_number: int,
        author_name: str,
        author_id: UUID | None = None,
    ) -> ContentBlockVersion:
        """Restore a historical version by appending it as the next higher version number."""
