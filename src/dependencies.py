from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .middlewares import get_firebase_user, get_optional_firebase_user
from .models import User
from .repositories import (
    ApiUsageRepository,
    ConversionRepository,
    FavoriteRepository,
    UserRepository,
)
from .services import ConversionService, FavoritesService, UserService

# === Database Dependencies ===


async def get_database_session() -> AsyncSession:
    async for session in get_db():
        yield session


# === Repository Dependencies ===


async def get_user_repository(db: AsyncSession = Depends(get_database_session)) -> UserRepository:
    return UserRepository(db)


async def get_conversion_repository(
    db: AsyncSession = Depends(get_database_session),
) -> ConversionRepository:
    return ConversionRepository(db)


async def get_favorite_repository(
    db: AsyncSession = Depends(get_database_session),
) -> FavoriteRepository:
    return FavoriteRepository(db)


async def get_api_usage_repository(
    db: AsyncSession = Depends(get_database_session),
) -> ApiUsageRepository:
    return ApiUsageRepository(db)


# === Service Dependencies ===


async def get_user_service(db: AsyncSession = Depends(get_database_session)) -> UserService:
    return UserService(db)


async def get_conversion_service(
    db: AsyncSession = Depends(get_database_session),
) -> ConversionService:
    return ConversionService(db)


async def get_favorites_service(
    db: AsyncSession = Depends(get_database_session),
) -> FavoritesService:
    return FavoritesService(db)


# === Authentication Dependencies ===


async def get_current_user(
    firebase_user: dict = Depends(get_firebase_user),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Firebase 認証済みユーザーから DB ユーザーを取得"""
    user = await user_service.get_user_by_firebase_uid(firebase_user["uid"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが登録されていません。先にサインアップしてください。",
        )
    return user


async def get_optional_current_user(
    firebase_user: dict | None = Depends(get_optional_firebase_user),
    user_service: UserService = Depends(get_user_service),
) -> User | None:
    """認証オプショナル"""
    if not firebase_user:
        return None

    return await user_service.get_user_by_firebase_uid(firebase_user["uid"])


async def get_premium_user(current_user: User = Depends(get_current_user)) -> User:
    """プレミアムユーザーを取得"""
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この機能はプレミアムユーザー限定です",
        )
    return current_user


# === Utility Dependencies ===


def get_pagination_params(skip: int = 0, limit: int = 100) -> tuple[int, int]:
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip は 0 以上である必要があります",
        )

    if limit <= 0 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit は 1 以上 1000 以下である必要があります",
        )

    return skip, limit
