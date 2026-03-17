"""Async repository layer for content database operations."""

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import ContentIteration, ContentRow, PublishConfig, Template


class ContentRepository:
    """Async CRUD operations for all Phase 1 content tables."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- ContentRow ---

    async def create_content_row(self, data: dict) -> ContentRow:
        row = ContentRow(**data)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get_content_row(self, row_id: int) -> ContentRow | None:
        return await self.session.get(ContentRow, row_id)

    async def get_all_content_rows(self) -> list[ContentRow]:
        result = await self.session.execute(select(ContentRow).order_by(ContentRow.date.desc()))
        return list(result.scalars().all())

    async def get_rows_by_status(self, status: str) -> list[ContentRow]:
        result = await self.session.execute(select(ContentRow).where(ContentRow.status == status))
        return list(result.scalars().all())

    async def get_rows_by_date_range(self, start: datetime, end: datetime) -> list[ContentRow]:
        result = await self.session.execute(
            select(ContentRow)
            .where(ContentRow.date >= start, ContentRow.date <= end)
            .order_by(ContentRow.date)
        )
        return list(result.scalars().all())

    async def update_captions(self, row_id: int, captions: str) -> None:
        await self.session.execute(
            update(ContentRow)
            .where(ContentRow.id == row_id)
            .values(captions=captions, updated_at=datetime.now(UTC))
        )
        await self.session.commit()

    async def update_status(self, row_id: int, status: str) -> None:
        await self.session.execute(
            update(ContentRow)
            .where(ContentRow.id == row_id)
            .values(status=status, updated_at=datetime.now(UTC))
        )
        await self.session.commit()

    async def update_postiz_ids(
        self, row_id: int, postiz_ids: str, posted_at: datetime | None = None
    ) -> None:
        values: dict = {"postiz_ids": postiz_ids, "updated_at": datetime.now(UTC)}
        if posted_at is not None:
            values["posted_at"] = posted_at
        await self.session.execute(
            update(ContentRow).where(ContentRow.id == row_id).values(**values)
        )
        await self.session.commit()

    async def delete_content_row(self, row_id: int) -> bool:
        await self.session.execute(delete(ContentRow).where(ContentRow.id == row_id))
        await self.session.commit()
        return True

    # --- ContentIteration ---

    async def add_iteration(self, data: dict) -> ContentIteration:
        iteration = ContentIteration(**data)
        self.session.add(iteration)
        await self.session.commit()
        await self.session.refresh(iteration)
        return iteration

    async def get_iterations(self, content_row_id: int) -> list[ContentIteration]:
        result = await self.session.execute(
            select(ContentIteration)
            .where(ContentIteration.content_row_id == content_row_id)
            .order_by(ContentIteration.created_at)
        )
        return list(result.scalars().all())

    # --- Template ---

    async def create_template(self, data: dict) -> Template:
        template = Template(**data)
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def get_templates(self) -> list[Template]:
        result = await self.session.execute(select(Template).order_by(Template.name))
        return list(result.scalars().all())

    async def get_template(self, template_id: int) -> Template | None:
        return await self.session.get(Template, template_id)

    async def update_template(self, template_id: int, data: dict) -> Template | None:
        data["updated_at"] = datetime.now(UTC)
        await self.session.execute(
            update(Template).where(Template.id == template_id).values(**data)
        )
        await self.session.commit()
        return await self.get_template(template_id)

    async def delete_template(self, template_id: int) -> bool:
        await self.session.execute(delete(Template).where(Template.id == template_id))
        await self.session.commit()
        return True

    # --- PublishConfig ---

    async def get_publish_configs(self) -> list[PublishConfig]:
        result = await self.session.execute(select(PublishConfig).order_by(PublishConfig.platform))
        return list(result.scalars().all())

    async def upsert_publish_config(self, platform: str, data: dict) -> PublishConfig:
        result = await self.session.execute(
            select(PublishConfig).where(PublishConfig.platform == platform)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now(UTC)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        config = PublishConfig(platform=platform, **data)
        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        return config
