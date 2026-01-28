from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Base

Model = TypeVar("Model", bound=Base)


class BaseRepository(Generic[Model]):
    def __init__(self, db: AsyncSession, model: type[Model]):
        self.db = db
        self.model = model

    async def create(self, **kwargs) -> Model:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, id: int) -> Model | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Model]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update(self, id: int, **kwargs) -> Model | None:
        instance = await self.get_by_id(id)
        if not instance:
            return None

        for field, value in kwargs.items():
            if hasattr(instance, field):
                setattr(instance, field, value)

        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        instance = await self.get_by_id(id)
        if not instance:
            return False

        await self.db.delete(instance)
        await self.db.commit()
        return True

    async def count(self) -> int:
        from sqlalchemy import func

        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar() or 0

    async def exists(self, **kwargs) -> bool:
        query = select(self.model)
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none() is not None

    async def find_by(self, **kwargs) -> list[Model]:
        query = select(self.model)
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_one_by(self, **kwargs) -> Model | None:
        query = select(self.model)
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()
