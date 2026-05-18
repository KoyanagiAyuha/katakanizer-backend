from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings, normalize_asyncpg_url
from .models import Base

settings = get_settings()

if settings.is_postgresql:
    database_url, connect_args = normalize_asyncpg_url(settings.database_url)
    engine = create_async_engine(
        database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
else:
    engine = create_async_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
