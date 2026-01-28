from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ConversionHistory
from ..repositories import ConversionRepository, FavoriteRepository


class FavoritesService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.favorite_repo = FavoriteRepository(db)
        self.conversion_repo = ConversionRepository(db)

    async def add_favorite(self, user_id: int, conversion_id: int) -> dict:
        conversion = await self.conversion_repo.get_by_id(conversion_id)
        if not conversion:
            raise RuntimeError("変換履歴が見つかりません")

        if conversion.user_id == user_id:
            raise RuntimeError("自分の変換履歴はお気に入りに追加できません")

        if not conversion.is_public:
            raise RuntimeError("この変換履歴はお気に入りに追加できません")

        if await self.favorite_repo.is_favorited(user_id, conversion_id):
            return {"message": "既にお気に入りに追加されています", "is_favorited": True}

        favorite = await self.favorite_repo.add_favorite(user_id, conversion_id)
        if not favorite:
            raise RuntimeError("お気に入りの追加に失敗しました")

        return {
            "message": "お気に入りに追加しました",
            "is_favorited": True,
            "favorite_id": favorite.id,
        }

    async def remove_favorite(self, user_id: int, conversion_id: int) -> dict:
        success = await self.favorite_repo.remove_favorite(user_id, conversion_id)

        if success:
            return {"message": "お気に入りから削除しました", "is_favorited": False}
        return {"message": "お気に入りに登録されていません", "is_favorited": False}

    async def toggle_favorite(self, user_id: int, conversion_id: int) -> dict:
        conversion = await self.conversion_repo.get_by_id(conversion_id)
        if not conversion:
            raise RuntimeError("変換履歴が見つかりません")

        if await self.favorite_repo.is_favorited(user_id, conversion_id):
            await self.favorite_repo.remove_favorite(user_id, conversion_id)
            return {"message": "お気に入りから削除しました", "is_favorited": False}
        else:
            await self.favorite_repo.add_favorite(user_id, conversion_id)
            return {"message": "お気に入りに追加しました", "is_favorited": True}

    async def get_user_favorites(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ConversionHistory]:
        return await self.favorite_repo.get_favorite_conversions(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    async def get_favorite_status(self, user_id: int, conversion_id: int) -> dict:
        is_favorited = await self.favorite_repo.is_favorited(user_id, conversion_id)
        favorite_count = await self.favorite_repo.count_conversion_favorites(conversion_id)

        return {
            "is_favorited": is_favorited,
            "favorite_count": favorite_count,
        }

    async def get_user_favorite_count(self, user_id: int) -> int:
        return await self.favorite_repo.count_user_favorites(user_id)

    async def get_popular_conversions(
        self, days: int = 30, limit: int = 100
    ) -> list[ConversionHistory]:
        return await self.favorite_repo.get_popular_conversions(days=days, limit=limit)
