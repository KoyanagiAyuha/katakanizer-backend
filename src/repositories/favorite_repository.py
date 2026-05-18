from datetime import datetime, timedelta

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import ConversionHistory, Favorite
from .base import BaseRepository


class FavoriteRepository(BaseRepository[Favorite]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Favorite)

    async def add_favorite(self, user_id: int, conversion_id: int) -> Favorite | None:
        existing = await self.get_favorite(user_id, conversion_id)
        if existing:
            return None

        favorite = Favorite(user_id=user_id, conversion_id=conversion_id)
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)
        return favorite

    async def remove_favorite(self, user_id: int, conversion_id: int) -> bool:
        favorite = await self.get_favorite(user_id, conversion_id)
        if not favorite:
            return False

        await self.db.delete(favorite)
        await self.db.commit()
        return True

    async def get_favorite(self, user_id: int, conversion_id: int) -> Favorite | None:
        result = await self.db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.conversion_id == conversion_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def is_favorited(self, user_id: int, conversion_id: int) -> bool:
        return await self.get_favorite(user_id, conversion_id) is not None

    async def get_user_favorites(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_conversions: bool = True,
    ) -> list[Favorite]:
        query = select(Favorite).where(Favorite.user_id == user_id)

        if include_conversions:
            query = query.options(
                selectinload(Favorite.conversion).selectinload(ConversionHistory.line_mappings)
            )

        query = query.order_by(desc(Favorite.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_favorite_conversions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ConversionHistory]:
        query = (
            select(ConversionHistory)
            .join(Favorite)
            .where(Favorite.user_id == user_id)
            .options(
                selectinload(ConversionHistory.line_mappings),
                selectinload(ConversionHistory.user),
            )
            .order_by(desc(Favorite.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_user_favorites(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
        )
        return result.scalar() or 0

    async def count_conversion_favorites(self, conversion_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Favorite)
            .where(Favorite.conversion_id == conversion_id)
        )
        return result.scalar() or 0

    async def get_popular_conversions(
        self, days: int = 30, limit: int = 100
    ) -> list[ConversionHistory]:
        since_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(ConversionHistory)
            .join(Favorite)
            .where(
                and_(
                    Favorite.created_at >= since_date,
                    ConversionHistory.is_public.is_(True),
                )
            )
            .group_by(ConversionHistory.id)
            .order_by(desc(func.count(Favorite.id)))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_user_favorites(self, user_id: int) -> int:
        result = await self.db.execute(delete(Favorite).where(Favorite.user_id == user_id))
        await self.db.commit()
        return result.rowcount or 0
