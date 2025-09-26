"""
基底リポジトリクラス

全てのリポジトリクラスが継承する基底クラスです。
共通的なCRUD操作を提供します。
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..database import Base

# 型変数
Model = TypeVar('Model', bound=Base)


class BaseRepository(Generic[Model]):
    """基底リポジトリクラス"""

    def __init__(self, db: Session, model: Type[Model]):
        """
        コンストラクタ

        Args:
            db: データベースセッション
            model: データベースモデルクラス
        """
        self.db = db
        self.model = model

    def create(self, **kwargs) -> Model:
        """
        エンティティを作成

        Args:
            **kwargs: モデルフィールドの値

        Returns:
            作成されたエンティティ

        Raises:
            SQLAlchemyError: データベースエラー
        """
        try:
            instance = self.model(**kwargs)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def get_by_id(self, id: int) -> Optional[Model]:
        """
        IDでエンティティを取得

        Args:
            id: エンティティID

        Returns:
            エンティティまたはNone
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Model]:
        """
        全エンティティを取得

        Args:
            skip: スキップ数
            limit: 取得上限

        Returns:
            エンティティリスト
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def update(self, id: int, **kwargs) -> Optional[Model]:
        """
        エンティティを更新

        Args:
            id: エンティティID
            **kwargs: 更新フィールドの値

        Returns:
            更新されたエンティティまたはNone

        Raises:
            SQLAlchemyError: データベースエラー
        """
        try:
            instance = self.get_by_id(id)
            if not instance:
                return None

            for field, value in kwargs.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)

            self.db.commit()
            self.db.refresh(instance)
            return instance
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def delete(self, id: int) -> bool:
        """
        エンティティを削除

        Args:
            id: エンティティID

        Returns:
            削除成功フラグ

        Raises:
            SQLAlchemyError: データベースエラー
        """
        try:
            instance = self.get_by_id(id)
            if not instance:
                return False

            self.db.delete(instance)
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def count(self) -> int:
        """
        エンティティの総数を取得

        Returns:
            エンティティ数
        """
        return self.db.query(self.model).count()

    def exists(self, **kwargs) -> bool:
        """
        条件に一致するエンティティが存在するか確認

        Args:
            **kwargs: 検索条件

        Returns:
            存在フラグ
        """
        query = self.db.query(self.model)
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query.first() is not None

    def find_by(self, **kwargs) -> List[Model]:
        """
        条件に一致するエンティティを全て取得

        Args:
            **kwargs: 検索条件

        Returns:
            エンティティリスト
        """
        query = self.db.query(self.model)
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query.all()

    def find_one_by(self, **kwargs) -> Optional[Model]:
        """
        条件に一致する最初のエンティティを取得

        Args:
            **kwargs: 検索条件

        Returns:
            エンティティまたはNone
        """
        query = self.db.query(self.model)
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query.first()