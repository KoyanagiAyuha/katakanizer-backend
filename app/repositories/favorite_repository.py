"""
お気に入りリポジトリ

お気に入りエンティティに関するデータベースアクセスを管理します。
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, func

from .base import BaseRepository
from ..database import Favorite, ConversionHistory


class FavoriteRepository(BaseRepository[Favorite]):
    """お気に入りリポジトリクラス"""

    def __init__(self, db: Session):
        super().__init__(db, Favorite)

    def add_favorite(self, user_id: int, conversion_id: int) -> Optional[Favorite]:
        """
        お気に入りに追加

        Args:
            user_id: ユーザーID
            conversion_id: 変換履歴ID

        Returns:
            作成されたお気に入りまたはNone（既に存在する場合）

        Raises:
            SQLAlchemyError: データベースエラー
        """
        # 既に存在するかチェック
        existing = self.get_favorite(user_id, conversion_id)
        if existing:
            return None

        try:
            favorite = Favorite(
                user_id=user_id,
                conversion_id=conversion_id
            )
            self.db.add(favorite)
            self.db.commit()
            self.db.refresh(favorite)
            return favorite
        except Exception:
            self.db.rollback()
            raise

    def remove_favorite(self, user_id: int, conversion_id: int) -> bool:
        """
        お気に入りから削除

        Args:
            user_id: ユーザーID
            conversion_id: 変換履歴ID

        Returns:
            削除成功フラグ
        """
        try:
            favorite = self.get_favorite(user_id, conversion_id)
            if not favorite:
                return False

            self.db.delete(favorite)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def get_favorite(self, user_id: int, conversion_id: int) -> Optional[Favorite]:
        """
        特定のお気に入りを取得

        Args:
            user_id: ユーザーID
            conversion_id: 変換履歴ID

        Returns:
            お気に入りまたはNone
        """
        return self.db.query(Favorite).filter(
            and_(
                Favorite.user_id == user_id,
                Favorite.conversion_id == conversion_id
            )
        ).first()

    def is_favorited(self, user_id: int, conversion_id: int) -> bool:
        """
        お気に入り登録されているかチェック

        Args:
            user_id: ユーザーID
            conversion_id: 変換履歴ID

        Returns:
            お気に入り登録フラグ
        """
        return self.get_favorite(user_id, conversion_id) is not None

    def get_user_favorites(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_conversions: bool = True
    ) -> List[Favorite]:
        """
        ユーザーのお気に入りを取得

        Args:
            user_id: ユーザーID
            skip: スキップ数
            limit: 取得上限
            include_conversions: 変換履歴を含むかどうか

        Returns:
            お気に入りリスト
        """
        query = self.db.query(Favorite).filter(Favorite.user_id == user_id)

        if include_conversions:
            query = query.options(
                joinedload(Favorite.conversion).joinedload(ConversionHistory.line_mappings)
            )

        return query.order_by(desc(Favorite.created_at)).offset(skip).limit(limit).all()

    def get_favorite_conversions(
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
        return self.db.query(ConversionHistory).join(Favorite).filter(
            Favorite.user_id == user_id
        ).options(
            joinedload(ConversionHistory.line_mappings)
        ).order_by(desc(Favorite.created_at)).offset(skip).limit(limit).all()

    def count_user_favorites(self, user_id: int) -> int:
        """
        ユーザーのお気に入り数を取得

        Args:
            user_id: ユーザーID

        Returns:
            お気に入り数
        """
        return self.db.query(Favorite).filter(Favorite.user_id == user_id).count()

    def count_conversion_favorites(self, conversion_id: int) -> int:
        """
        変換履歴のお気に入り数を取得

        Args:
            conversion_id: 変換履歴ID

        Returns:
            お気に入り数
        """
        return self.db.query(Favorite).filter(Favorite.conversion_id == conversion_id).count()

    def get_popular_conversions(
        self,
        days: int = 30,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        人気の変換履歴を取得（お気に入り数順）

        Args:
            days: 過去何日間
            limit: 取得上限

        Returns:
            人気変換履歴リスト
        """
        since_date = datetime.utcnow() - timedelta(days=days)

        return self.db.query(ConversionHistory).join(Favorite).filter(
            and_(
                Favorite.created_at >= since_date,
                ConversionHistory.is_public == True
            )
        ).group_by(ConversionHistory.id).order_by(
            desc(func.count(Favorite.id))
        ).limit(limit).all()

    def delete_user_favorites(self, user_id: int) -> int:
        """
        ユーザーの全お気に入りを削除

        Args:
            user_id: ユーザーID

        Returns:
            削除されたお気に入り数
        """
        try:
            result = self.db.query(Favorite).filter(
                Favorite.user_id == user_id
            ).delete()
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def delete_conversion_favorites(self, conversion_id: int) -> int:
        """
        変換履歴の全お気に入りを削除

        Args:
            conversion_id: 変換履歴ID

        Returns:
            削除されたお気に入り数
        """
        try:
            result = self.db.query(Favorite).filter(
                Favorite.conversion_id == conversion_id
            ).delete()
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise