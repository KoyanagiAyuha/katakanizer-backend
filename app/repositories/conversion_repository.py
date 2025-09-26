"""
変換履歴リポジトリ

変換履歴とライン映射エンティティに関するデータベースアクセスを管理します。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_

from .base import BaseRepository
from ..database import ConversionHistory, LineMapping


class ConversionRepository(BaseRepository[ConversionHistory]):
    """変換履歴リポジトリクラス"""

    def __init__(self, db: Session):
        super().__init__(db, ConversionHistory)

    def create_with_mappings(
        self,
        title: str,
        original_text: str,
        language: str,
        user_id: Optional[int],
        word_mappings: List[Dict[str, str]]
    ) -> ConversionHistory:
        """
        変換履歴をライン映射と共に作成

        Args:
            title: タイトル
            original_text: 元テキスト
            language: 言語
            user_id: ユーザーID
            word_mappings: ワード映射リスト

        Returns:
            作成された変換履歴

        Raises:
            SQLAlchemyError: データベースエラー
        """
        try:
            # 変換履歴を作成
            conversion = ConversionHistory(
                title=title,
                original_text=original_text,
                language=language,
                user_id=user_id
            )
            self.db.add(conversion)
            self.db.commit()
            self.db.refresh(conversion)

            # ライン映射を作成
            for i, mapping in enumerate(word_mappings):
                line_mapping = LineMapping(
                    conversion_id=conversion.id,
                    line_text=mapping["line"],
                    casual_katakana=mapping["casual"],
                    formal_katakana=mapping["formal"],
                    line_order=i
                )
                self.db.add(line_mapping)

            self.db.commit()
            return conversion
        except Exception:
            self.db.rollback()
            raise

    def get_with_mappings(self, conversion_id: int) -> Optional[ConversionHistory]:
        """
        変換履歴をライン映射と共に取得

        Args:
            conversion_id: 変換履歴ID

        Returns:
            変換履歴（ライン映射含む）またはNone
        """
        return self.db.query(ConversionHistory).options(
            joinedload(ConversionHistory.line_mappings)
        ).filter(ConversionHistory.id == conversion_id).first()

    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_mappings: bool = False
    ) -> List[ConversionHistory]:
        """
        ユーザーの変換履歴を取得

        Args:
            user_id: ユーザーID
            skip: スキップ数
            limit: 取得上限
            include_mappings: ライン映射を含むかどうか

        Returns:
            変換履歴リスト
        """
        query = self.db.query(ConversionHistory).filter(
            ConversionHistory.user_id == user_id
        )

        if include_mappings:
            query = query.options(joinedload(ConversionHistory.line_mappings))

        return query.order_by(desc(ConversionHistory.created_at)).offset(skip).limit(limit).all()

    def get_public_conversions(
        self,
        skip: int = 0,
        limit: int = 100,
        include_mappings: bool = False
    ) -> List[ConversionHistory]:
        """
        公開変換履歴を取得

        Args:
            skip: スキップ数
            limit: 取得上限
            include_mappings: ライン映射を含むかどうか

        Returns:
            公開変換履歴リスト
        """
        query = self.db.query(ConversionHistory).filter(
            ConversionHistory.is_public == True
        )

        if include_mappings:
            query = query.options(joinedload(ConversionHistory.line_mappings))

        return query.order_by(desc(ConversionHistory.created_at)).offset(skip).limit(limit).all()

    def search_conversions(
        self,
        search_query: str,
        user_id: Optional[int] = None,
        public_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        変換履歴を検索

        Args:
            search_query: 検索クエリ
            user_id: ユーザーID（指定時はそのユーザーの履歴のみ）
            public_only: 公開履歴のみかどうか
            skip: スキップ数
            limit: 取得上限

        Returns:
            検索結果リスト
        """
        query = self.db.query(ConversionHistory)

        # テキスト検索
        search_condition = or_(
            ConversionHistory.title.contains(search_query),
            ConversionHistory.original_text.contains(search_query)
        )
        query = query.filter(search_condition)

        # ユーザー制限
        if user_id:
            query = query.filter(ConversionHistory.user_id == user_id)

        # 公開制限
        if public_only:
            query = query.filter(ConversionHistory.is_public == True)

        return query.order_by(desc(ConversionHistory.created_at)).offset(skip).limit(limit).all()

    def get_recent_conversions(
        self,
        days: int = 7,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        最近の変換履歴を取得

        Args:
            days: 過去何日間
            limit: 取得上限

        Returns:
            最近の変換履歴リスト
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(ConversionHistory).filter(
            and_(
                ConversionHistory.created_at >= since_date,
                ConversionHistory.is_public == True
            )
        ).order_by(desc(ConversionHistory.created_at)).limit(limit).all()

    def count_by_user(self, user_id: int) -> int:
        """
        ユーザーの変換履歴数を取得

        Args:
            user_id: ユーザーID

        Returns:
            変換履歴数
        """
        return self.db.query(ConversionHistory).filter(
            ConversionHistory.user_id == user_id
        ).count()

    def update_visibility(self, conversion_id: int, is_public: bool) -> Optional[ConversionHistory]:
        """
        変換履歴の公開設定を更新

        Args:
            conversion_id: 変換履歴ID
            is_public: 公開フラグ

        Returns:
            更新された変換履歴またはNone
        """
        return self.update(conversion_id, is_public=is_public)

    def delete_user_conversions(self, user_id: int) -> int:
        """
        ユーザーの全変換履歴を削除

        Args:
            user_id: ユーザーID

        Returns:
            削除された履歴数
        """
        try:
            result = self.db.query(ConversionHistory).filter(
                ConversionHistory.user_id == user_id
            ).delete()
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise