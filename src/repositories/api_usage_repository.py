from datetime import datetime, timedelta

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ApiUsage
from .base import BaseRepository


class ApiUsageRepository(BaseRepository[ApiUsage]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ApiUsage)

    async def record_usage(
        self,
        user_id: int,
        endpoint: str,
        response_time_ms: int | None = None,
        status_code: int | None = None,
    ) -> ApiUsage:
        return await self.create(
            user_id=user_id,
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            status_code=status_code,
        )

    async def get_user_usage(
        self,
        user_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        endpoint: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ApiUsage]:
        query = select(ApiUsage).where(ApiUsage.user_id == user_id)

        if start_date:
            query = query.where(ApiUsage.created_at >= start_date)
        if end_date:
            query = query.where(ApiUsage.created_at <= end_date)
        if endpoint:
            query = query.where(ApiUsage.endpoint == endpoint)

        query = query.order_by(desc(ApiUsage.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_user_requests(
        self,
        user_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        endpoint: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(ApiUsage).where(ApiUsage.user_id == user_id)

        if start_date:
            query = query.where(ApiUsage.created_at >= start_date)
        if end_date:
            query = query.where(ApiUsage.created_at <= end_date)
        if endpoint:
            query = query.where(ApiUsage.endpoint == endpoint)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_daily_usage_count(
        self,
        user_id: int,
        date: datetime | None = None,
        endpoint: str | None = None,
    ) -> int:
        if not date:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return await self.count_user_requests(
            user_id=user_id,
            start_date=start_of_day,
            end_date=end_of_day,
            endpoint=endpoint,
        )

    async def cleanup_old_usage(self, older_than_days: int = 90) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        result = await self.db.execute(delete(ApiUsage).where(ApiUsage.created_at <= cutoff_date))
        await self.db.commit()
        return result.rowcount or 0
