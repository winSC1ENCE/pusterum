"""SQLAlchemy 2.0 Async implementation of IContentRepository with Versioning."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.exceptions import EntityNotFoundException
from atem.domain.interfaces.content_repository import IContentRepository
from atem.domain.models.content import ContentBlock, ContentBlockType, ContentBlockVersion
from atem.infrastructure.database.models.content import ContentBlockModel, ContentBlockVersionModel
from atem.infrastructure.database.seed.content_defaults import DEFAULT_CONTENT_BLOCKS


class SqlAlchemyContentRepository(IContentRepository):
    """PostgreSQL / SQLite async repository for live website content and versioning."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: ContentBlockModel) -> ContentBlock:
        return ContentBlock(
            id=UUID(int=0),  # String key is primary identifier
            key=model.key,
            section=model.section,
            block_type=ContentBlockType(model.block_type),
            current_version_number=model.current_version_number,
            current_content=model.current_content,
            updated_at=model.updated_at,
        )

    def _to_version_entity(self, model: ContentBlockVersionModel) -> ContentBlockVersion:
        return ContentBlockVersion(
            id=model.id,
            block_key=model.block_key,
            version_number=model.version_number,
            content=model.content,
            author_id=model.author_id,
            author_name=model.author_name,
            change_summary=model.change_summary,
            created_at=model.created_at,
        )

    async def seed_missing_blocks(self) -> int:
        """Insert default content blocks whose key does not exist yet.

        Runs once at startup (development/test lifespan) or via ``python -m atem.cli seed-content``
        in production. Existing blocks are never overwritten. Returns the number of inserted blocks.
        """
        existing_stmt = select(ContentBlockModel.key)
        existing_res = await self._session.execute(existing_stmt)
        existing_keys = set(existing_res.scalars().all())

        missing_blocks = [
            item for item in DEFAULT_CONTENT_BLOCKS if item["key"] not in existing_keys
        ]
        if missing_blocks:
            now = datetime.now(UTC)
            for item in missing_blocks:
                block_model = ContentBlockModel(
                    key=item["key"],
                    section=item["section"],
                    block_type=item["type"],
                    current_version_number=1,
                    current_content=item["content"],
                    updated_at=now,
                )
                self._session.add(block_model)
                version_model = ContentBlockVersionModel(
                    block_key=item["key"],
                    version_number=1,
                    content=item["content"],
                    author_name="System Initialisierung",
                    change_summary="Standard-Inhalt",
                    created_at=now,
                )
                self._session.add(version_model)
            await self._session.flush()
        return len(missing_blocks)

    async def get_block(self, key: str) -> ContentBlock | None:
        stmt = select(ContentBlockModel).where(ContentBlockModel.key == key)
        res = await self._session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all_blocks(self) -> dict[str, ContentBlock]:
        stmt = select(ContentBlockModel)
        res = await self._session.execute(stmt)
        models = res.scalars().all()
        return {m.key: self._to_entity(m) for m in models}

    async def save_version(
        self,
        key: str,
        content: str,
        author_name: str,
        author_id: UUID | None = None,
        change_summary: str | None = None,
    ) -> ContentBlockVersion:
        stmt = select(ContentBlockModel).where(ContentBlockModel.key == key)
        res = await self._session.execute(stmt)
        block_model = res.scalar_one_or_none()

        now = datetime.now(UTC)
        if not block_model:
            # Only seeded keys exist – new keys are never created through the editor.
            raise EntityNotFoundException("ContentBlock", key)
        new_version_num = block_model.current_version_number + 1
        block_model.current_version_number = new_version_num
        block_model.current_content = content
        block_model.updated_at = now

        version_model = ContentBlockVersionModel(
            block_key=key,
            version_number=new_version_num,
            content=content,
            author_id=author_id,
            author_name=author_name,
            change_summary=change_summary or "Aktualisierung",
            created_at=now,
        )
        self._session.add(version_model)
        await self._session.flush()
        await self._session.refresh(version_model)
        return self._to_version_entity(version_model)

    async def get_version_history(self, key: str) -> list[ContentBlockVersion]:
        stmt = (
            select(ContentBlockVersionModel)
            .where(ContentBlockVersionModel.block_key == key)
            .order_by(ContentBlockVersionModel.version_number.desc())
        )
        res = await self._session.execute(stmt)
        models = res.scalars().all()
        return [self._to_version_entity(m) for m in models]

    async def restore_version(
        self,
        key: str,
        target_version_number: int,
        author_name: str,
        author_id: UUID | None = None,
    ) -> ContentBlockVersion:
        stmt = select(ContentBlockVersionModel).where(
            ContentBlockVersionModel.block_key == key,
            ContentBlockVersionModel.version_number == target_version_number,
        )
        res = await self._session.execute(stmt)
        target_model = res.scalar_one_or_none()
        if not target_model:
            raise EntityNotFoundException("ContentBlockVersion", f"{key}#v{target_version_number}")

        summary = f"Wiederherstellung von Version v{target_version_number}"
        return await self.save_version(
            key=key,
            content=target_model.content,
            author_name=author_name,
            author_id=author_id,
            change_summary=summary,
        )
