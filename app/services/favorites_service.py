"""
お気に入りサービス

お気に入り関連のビジネスロジックを管理します。
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_service import BaseService
from ..repositories import FavoriteRepository, ConversionRepository
from ..database import Favorite, ConversionHistory


class FavoritesService(BaseService):
    """お気に入りサービスクラス"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.favorite_repo = self._get_repository(FavoriteRepository)
        self.conversion_repo = self._get_repository(ConversionRepository)

    def add_favorite(self, user_id: int, conversion_id: int) -> Dict[str, Any]:
        """
        お気に入りに追加

        Args:
            user_id: ユーザーID
            conversion_id: 変換履歴ID

        Returns:
            結果情報

        Raises:
            RuntimeError: エラー情報
        """
        # 変換履歴の存在確認
        conversion = self.conversion_repo.get_by_id(conversion_id)
        if not conversion:
            raise RuntimeError("変換履歴が見つかりません")

        # 自分の変換履歴はお気に入りに追加できない
        if conversion.user_id == user_id:
            raise RuntimeError("自分の変換履歴はお気に入りに追加できません")

        # 公開されていない変換履歴はお気に入りに追加できない
        if not conversion.is_public:
            raise RuntimeError("この変換履歴はお気に入りに追加できません")

        # 既にお気に入りに追加されているかチェック
        if self.favorite_repo.is_favorited(user_id, conversion_id):
            return {
                "message": "既にお気に入りに追加されています",
                "is_favorited": True
            }

        # お気に入りに追加
        favorite = self.favorite_repo.add_favorite(user_id, conversion_id)
        if not favorite:
            raise RuntimeError("お気に入りの追加に失敗しました")

        return {
            "message": "お気に入りに追加しました",
            "is_favorited": True,
            "favorite_id": favorite.id
        }

    def remove_favorite(self, user_id: int, conversion_id: int) -> Dict[str, Any]:
        """
        お気に入りから削除

        Args:
            user_id: ユーザーID
            conversion_id: 変換履歴ID

        Returns:
            結果情報
        """
        success = self.favorite_repo.remove_favorite(user_id, conversion_id)

        if success:
            return {
                "message": "お気に入りから削除しました",
                "is_favorited": False
            }
        else:
            return {
                "message": "お気に入りに登録されていません",
                "is_favorited": False
            }

    def get_user_favorites(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        ユーザーのお気に入り変換履歴を取得

        Args:
            user_id: ユーザーID
            skip: スキップ数
            limit: 取得上限

        Returns:
            お気に入り変換履歴リスト
        """
        return self.favorite_repo.get_favorite_conversions(
            user_id=user_id,
            skip=skip,
            limit=limit
        )

    def get_favorite_status(self, user_id: int, conversion_id: int) -> Dict[str, Any]:
        """
        お気に入り状態を取得

        Args:
            user_id: ユーザーID
            conversion_id: 変換履歴ID

        Returns:
            お気に入り状態情報
        """
        is_favorited = self.favorite_repo.is_favorited(user_id, conversion_id)
        favorite_count = self.favorite_repo.count_conversion_favorites(conversion_id)

        return {
            "is_favorited": is_favorited,
            "favorite_count": favorite_count
        }

    def get_user_favorite_count(self, user_id: int) -> int:
        """
        ユーザーのお気に入り数を取得

        Args:
            user_id: ユーザーID

        Returns:
            お気に入り数
        """
        return self.favorite_repo.count_user_favorites(user_id)

    def get_popular_conversions(
        self,
        days: int = 30,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        人気の変換履歴を取得

        Args:
            days: 過去何日間
            limit: 取得上限

        Returns:
            人気変換履歴リスト
        """
        return self.favorite_repo.get_popular_conversions(
            days=days,
            limit=limit
        )

    def bulk_remove_favorites(self, user_id: int, conversion_ids: List[int]) -> Dict[str, Any]:
        """
        複数のお気に入りを一括削除

        Args:
            user_id: ユーザーID
            conversion_ids: 変換履歴IDリスト

        Returns:
            削除結果情報
        """
        removed_count = 0
        errors = []

        for conversion_id in conversion_ids:
            try:
                success = self.favorite_repo.remove_favorite(user_id, conversion_id)
                if success:
                    removed_count += 1
            except Exception as e:
                errors.append(f"ID {conversion_id}: {str(e)}")

        return {
            "removed_count": removed_count,
            "total_requested": len(conversion_ids),
            "errors": errors
        }

    def get_conversion_with_favorite_info(
        self,
        conversion_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        変換履歴をお気に入り情報と共に取得

        Args:
            conversion_id: 変換履歴ID
            user_id: ユーザーID（お気に入り状態確認用）

        Returns:
            変換履歴とお気に入り情報またはNone
        """
        conversion = self.conversion_repo.get_with_mappings(conversion_id)
        if not conversion:
            return None

        # お気に入り情報を取得
        is_favorited = False
        if user_id:
            is_favorited = self.favorite_repo.is_favorited(user_id, conversion_id)

        favorite_count = self.favorite_repo.count_conversion_favorites(conversion_id)

        return {
            "conversion": conversion,
            "is_favorited": is_favorited,
            "favorite_count": favorite_count
        }