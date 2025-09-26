"""
基底サービスクラス

全てのサービスクラスが継承する基底クラスです。
共通的なビジネスロジックパターンを提供します。
"""

from typing import TypeVar, Generic
from sqlalchemy.orm import Session

from ..repositories.base import BaseRepository

# 型変数
Repository = TypeVar('Repository', bound=BaseRepository)


class BaseService(Generic[Repository]):
    """基底サービスクラス"""

    def __init__(self, db: Session):
        """
        コンストラクタ

        Args:
            db: データベースセッション
        """
        self.db = db

    def _get_repository(self, repository_class) -> Repository:
        """
        リポジトリインスタンスを取得

        Args:
            repository_class: リポジトリクラス

        Returns:
            リポジトリインスタンス
        """
        return repository_class(self.db)