"""
ユーザーリポジトリ

ユーザーエンティティに関するデータベースアクセスを管理します。
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .base import BaseRepository
from ..database import User


class UserRepository(BaseRepository[User]):
    """ユーザーリポジトリクラス"""

    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_username(self, username: str) -> Optional[User]:
        """
        ユーザー名でユーザーを取得

        Args:
            username: ユーザー名

        Returns:
            ユーザーまたはNone
        """
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """
        メールアドレスでユーザーを取得

        Args:
            email: メールアドレス

        Returns:
            ユーザーまたはNone
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        """
        ユーザー名またはメールアドレスでユーザーを取得

        Args:
            identifier: ユーザー名またはメールアドレス

        Returns:
            ユーザーまたはNone
        """
        return self.db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

    def is_username_taken(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        ユーザー名が使用されているか確認

        Args:
            username: 確認するユーザー名
            exclude_user_id: 除外するユーザーID（更新時用）

        Returns:
            使用中フラグ
        """
        query = self.db.query(User).filter(User.username == username)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    def is_email_taken(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        メールアドレスが使用されているか確認

        Args:
            email: 確認するメールアドレス
            exclude_user_id: 除外するユーザーID（更新時用）

        Returns:
            使用中フラグ
        """
        query = self.db.query(User).filter(User.email == email)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    def get_active_users(self) -> List[User]:
        """
        アクティブなユーザーを全て取得

        Returns:
            アクティブユーザーリスト
        """
        return self.db.query(User).filter(
            and_(User.is_active == True, User.is_email_verified == True)
        ).all()

    def get_unverified_users(self, older_than: Optional[datetime] = None) -> List[User]:
        """
        メール未確認のユーザーを取得

        Args:
            older_than: この日時より古いユーザーのみ取得

        Returns:
            未確認ユーザーリスト
        """
        query = self.db.query(User).filter(User.is_email_verified == False)
        if older_than:
            query = query.filter(User.created_at < older_than)
        return query.all()

    def get_premium_users(self) -> List[User]:
        """
        プレミアムユーザーを取得

        Returns:
            プレミアムユーザーリスト
        """
        return self.db.query(User).filter(
            and_(
                User.is_premium == True,
                or_(
                    User.premium_expires_at.is_(None),
                    User.premium_expires_at > datetime.utcnow()
                )
            )
        ).all()

    def update_email_verification(self, user_id: int, verified: bool = True) -> Optional[User]:
        """
        メール確認状態を更新

        Args:
            user_id: ユーザーID
            verified: 確認状態

        Returns:
            更新されたユーザーまたはNone
        """
        return self.update(
            user_id,
            is_email_verified=verified,
            email_verification_token=None,
            email_verification_expires=None
        )

    def update_password(self, user_id: int, hashed_password: str) -> Optional[User]:
        """
        パスワードを更新

        Args:
            user_id: ユーザーID
            hashed_password: ハッシュ化されたパスワード

        Returns:
            更新されたユーザーまたはNone
        """
        return self.update(
            user_id,
            hashed_password=hashed_password,
            password_reset_token=None,
            password_reset_expires=None
        )

    def update_daily_conversion_count(self, user_id: int, count: int) -> Optional[User]:
        """
        日次変換回数を更新

        Args:
            user_id: ユーザーID
            count: 変換回数

        Returns:
            更新されたユーザーまたはNone
        """
        return self.update(
            user_id,
            daily_conversion_count=count,
            last_conversion_reset=datetime.utcnow()
        )

    def reset_daily_conversion_counts(self) -> int:
        """
        全ユーザーの日次変換回数をリセット

        Returns:
            更新されたユーザー数
        """
        try:
            result = self.db.query(User).update({
                User.daily_conversion_count: 0,
                User.last_conversion_reset: datetime.utcnow()
            })
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def increment_conversion_count(self, user_id: int) -> Optional[User]:
        """
        変換回数をインクリメント

        Args:
            user_id: ユーザーID

        Returns:
            更新されたユーザーまたはNone
        """
        user = self.get_by_id(user_id)
        if not user:
            return None

        return self.update(user_id, daily_conversion_count=user.daily_conversion_count + 1)