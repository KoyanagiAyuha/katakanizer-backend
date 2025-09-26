"""
リフレッシュトークンリポジトリ

リフレッシュトークンエンティティに関するデータベースアクセスを管理します。
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .base import BaseRepository
from ..database import RefreshToken


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """リフレッシュトークンリポジトリクラス"""

    def __init__(self, db: Session):
        super().__init__(db, RefreshToken)

    def create_token(
        self,
        token: str,
        user_id: int,
        expires_at: datetime
    ) -> RefreshToken:
        """
        リフレッシュトークンを作成

        Args:
            token: トークン文字列
            user_id: ユーザーID
            expires_at: 有効期限

        Returns:
            作成されたリフレッシュトークン

        Raises:
            SQLAlchemyError: データベースエラー
        """
        return self.create(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """
        トークン文字列でリフレッシュトークンを取得

        Args:
            token: トークン文字列

        Returns:
            リフレッシュトークンまたはNone
        """
        return self.db.query(RefreshToken).filter(
            RefreshToken.token == token
        ).first()

    def get_valid_token(self, token: str) -> Optional[RefreshToken]:
        """
        有効なリフレッシュトークンを取得

        Args:
            token: トークン文字列

        Returns:
            有効なリフレッシュトークンまたはNone
        """
        return self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.token == token,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.utcnow()
            )
        ).first()

    def get_user_tokens(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[RefreshToken]:
        """
        ユーザーのリフレッシュトークンを取得

        Args:
            user_id: ユーザーID
            active_only: アクティブなトークンのみかどうか

        Returns:
            リフレッシュトークンリスト
        """
        query = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        )

        if active_only:
            query = query.filter(
                and_(
                    RefreshToken.revoked == False,
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )

        return query.all()

    def revoke_token(self, token: str) -> bool:
        """
        リフレッシュトークンを無効化

        Args:
            token: トークン文字列

        Returns:
            無効化成功フラグ
        """
        try:
            result = self.db.query(RefreshToken).filter(
                RefreshToken.token == token
            ).update({"revoked": True})
            self.db.commit()
            return result > 0
        except Exception:
            self.db.rollback()
            raise

    def revoke_user_tokens(self, user_id: int) -> int:
        """
        ユーザーの全リフレッシュトークンを無効化

        Args:
            user_id: ユーザーID

        Returns:
            無効化されたトークン数
        """
        try:
            result = self.db.query(RefreshToken).filter(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False
                )
            ).update({"revoked": True})
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def cleanup_expired_tokens(self) -> int:
        """
        期限切れトークンを削除

        Returns:
            削除されたトークン数
        """
        try:
            result = self.db.query(RefreshToken).filter(
                RefreshToken.expires_at <= datetime.utcnow()
            ).delete()
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def cleanup_revoked_tokens(self, older_than_days: int = 30) -> int:
        """
        古い無効化トークンを削除

        Args:
            older_than_days: 何日より古いトークンを削除するか

        Returns:
            削除されたトークン数
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        try:
            result = self.db.query(RefreshToken).filter(
                and_(
                    RefreshToken.revoked == True,
                    RefreshToken.created_at <= cutoff_date
                )
            ).delete()
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def count_user_active_tokens(self, user_id: int) -> int:
        """
        ユーザーのアクティブトークン数を取得

        Args:
            user_id: ユーザーID

        Returns:
            アクティブトークン数
        """
        return self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.utcnow()
            )
        ).count()