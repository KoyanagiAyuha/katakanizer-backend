from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import ConversionHistory, LineMapping
from .base import BaseRepository


class ConversionRepository(BaseRepository[ConversionHistory]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ConversionHistory)

    async def create_with_mappings(
        self,
        title: str,
        original_text: str,
        language: str,
        user_id: int | None,
        word_mappings: list[dict[str, str]],
    ) -> ConversionHistory:
        conversion = ConversionHistory(
            title=title,
            original_text=original_text,
            language=language,
            user_id=user_id,
        )
        self.db.add(conversion)
        await self.db.commit()
        await self.db.refresh(conversion)

        for i, mapping in enumerate(word_mappings):
            line_mapping = LineMapping(
                conversion_id=conversion.id,
                line_text=mapping["line"],
                casual_katakana=mapping["casual"],
                formal_katakana=mapping["formal"],
                line_order=i,
            )
            self.db.add(line_mapping)

        await self.db.commit()
        return conversion

    async def get_with_mappings(self, conversion_id: int) -> ConversionHistory | None:
        result = await self.db.execute(
            select(ConversionHistory)
            .options(selectinload(ConversionHistory.line_mappings))
            .where(ConversionHistory.id == conversion_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_mappings: bool = False,
    ) -> list[ConversionHistory]:
        query = select(ConversionHistory).where(ConversionHistory.user_id == user_id)

        if include_mappings:
            query = query.options(selectinload(ConversionHistory.line_mappings))

        query = query.order_by(desc(ConversionHistory.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_public_conversions(
        self,
        skip: int = 0,
        limit: int = 100,
        include_mappings: bool = False,
    ) -> list[ConversionHistory]:
        query = select(ConversionHistory).where(ConversionHistory.is_public.is_(True))

        if include_mappings:
            query = query.options(selectinload(ConversionHistory.line_mappings))

        query = query.order_by(desc(ConversionHistory.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_conversions(
        self,
        search_query: str,
        user_id: int | None = None,
        public_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ConversionHistory]:
        query = select(ConversionHistory)

        search_condition = or_(
            ConversionHistory.title.contains(search_query),
            ConversionHistory.original_text.contains(search_query),
        )
        query = query.where(search_condition)

        if user_id:
            query = query.where(ConversionHistory.user_id == user_id)

        if public_only:
            query = query.where(ConversionHistory.is_public.is_(True))

        query = query.order_by(desc(ConversionHistory.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count())
            .select_from(ConversionHistory)
            .where(ConversionHistory.user_id == user_id)
        )
        return result.scalar() or 0

    async def update_visibility(
        self, conversion_id: int, is_public: bool
    ) -> ConversionHistory | None:
        return await self.update(conversion_id, is_public=is_public)

    async def delete_user_conversions(self, user_id: int) -> int:
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(ConversionHistory).where(ConversionHistory.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount or 0
