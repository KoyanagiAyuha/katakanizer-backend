"""
ユーザーサービス

ユーザー関連のビジネスロジックを管理します。
"""

from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .base_service import BaseService
from ..repositories import UserRepository, RefreshTokenRepository, ApiUsageRepository
from ..database import User
from ..config import get_settings
from .email_service import EmailService
from ..auth import (
    get_password_hash, verify_password, validate_password,
    validate_email, validate_username, create_access_token,
    create_refresh_token, save_refresh_token
)

settings = get_settings()


class UserService(BaseService):
    """ユーザーサービスクラス"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.user_repo = self._get_repository(UserRepository)
        self.refresh_token_repo = self._get_repository(RefreshTokenRepository)
        self.api_usage_repo = self._get_repository(ApiUsageRepository)

    def register_user(
        self,
        username: str,
        email: str,
        password: str
    ) -> Tuple[User, str]:
        """
        ユーザーを登録

        Args:
            username: ユーザー名
            email: メールアドレス
            password: パスワード

        Returns:
            (作成されたユーザー, 登録メッセージ)

        Raises:
            ValueError: バリデーションエラー
            RuntimeError: 重複エラーやその他のエラー
        """
        # バリデーション
        if not validate_username(username):
            raise ValueError("ユーザー名は3〜30文字で、英数字とアンダースコアのみ使用可能です")

        if not validate_email(email):
            raise ValueError("無効なメールアドレス形式です")

        if not validate_password(password):
            raise ValueError("パスワードは8文字以上で、大文字、小文字、数字、特殊文字を含む必要があります")

        # 重複チェック
        if self.user_repo.is_username_taken(username):
            raise RuntimeError("このユーザー名は既に使用されています")

        if self.user_repo.is_email_taken(email):
            raise RuntimeError("このメールアドレスは既に登録されています")

        # ユーザー作成
        hashed_password = get_password_hash(password)
        user = self.user_repo.create(
            username=username,
            email=email,
            hashed_password=hashed_password
        )

        return user, "登録が完了しました！ログインする前に、メールを確認してアカウントを認証してください。"

    async def send_verification_email(self, user: User) -> bool:
        """
        メール確認用のメールを送信

        Args:
            user: ユーザー

        Returns:
            送信成功フラグ
        """
        token = EmailService.generate_verification_token(user.email)
        return await EmailService.send_verification_email(user.email, user.username, token)

    async def verify_email(self, token: str) -> Optional[User]:
        """
        メール確認トークンを検証

        Args:
            token: 確認トークン

        Returns:
            確認されたユーザーまたはNone
        """
        email = EmailService.verify_verification_token(token)
        if not email:
            return None

        user = self.user_repo.get_by_email(email)
        if not user:
            return None

        # 既に確認済みでもユーザーを返す
        if user.is_email_verified:
            return user

        # 未確認の場合は確認済みにする
        return self.user_repo.update_email_verification(user.id, True)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        ユーザー認証

        Args:
            username: ユーザー名
            password: パスワード

        Returns:
            認証されたユーザーまたはNone
        """
        user = self.user_repo.get_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    def create_tokens(self, user: User) -> Tuple[str, str]:
        """
        アクセストークンとリフレッシュトークンのペアを作成

        Args:
            user: ユーザー

        Returns:
            (アクセストークン, リフレッシュトークン)
        """
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        refresh_token_expires = timedelta(days=settings.jwt_refresh_token_expire_days)

        # アクセストークン作成
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )

        # リフレッシュトークン作成
        refresh_token = create_refresh_token(
            data={"sub": user.username},
            expires_delta=refresh_token_expires
        )

        # リフレッシュトークンをDBに保存
        expires_at = datetime.utcnow() + refresh_token_expires
        self.refresh_token_repo.create_token(refresh_token, user.id, expires_at)

        return access_token, refresh_token

    def verify_refresh_token(self, token: str) -> Optional[User]:
        """
        リフレッシュトークン検証

        Args:
            token: リフレッシュトークン

        Returns:
            ユーザーまたはNone
        """
        refresh_token = self.refresh_token_repo.get_valid_token(token)
        if not refresh_token:
            return None

        return self.user_repo.get_by_id(refresh_token.user_id)

    def revoke_user_tokens(self, user_id: int) -> int:
        """
        ユーザーの全リフレッシュトークンを無効化

        Args:
            user_id: ユーザーID

        Returns:
            無効化されたトークン数
        """
        return self.refresh_token_repo.revoke_user_tokens(user_id)

    def revoke_token(self, token: str) -> bool:
        """
        特定のリフレッシュトークンを無効化

        Args:
            token: トークン文字列

        Returns:
            無効化成功フラグ
        """
        return self.refresh_token_repo.revoke_token(token)

    async def request_password_reset(self, email: str) -> bool:
        """
        パスワードリセットリクエスト

        Args:
            email: メールアドレス

        Returns:
            処理成功フラグ
        """
        if not validate_email(email):
            return False

        user = self.user_repo.get_by_email(email)
        if not user:
            return True  # セキュリティ上、存在しなくても成功レスポンス

        token = EmailService.generate_password_reset_token(email)
        return await EmailService.send_password_reset_email(user.email, user.username, token)

    def reset_password(self, token: str, new_password: str) -> bool:
        """
        パスワードリセット実行

        Args:
            token: リセットトークン
            new_password: 新しいパスワード

        Returns:
            リセット成功フラグ
        """
        email = EmailService.verify_password_reset_token(token)
        if not email:
            return False

        user = self.user_repo.get_by_email(email)
        if not user:
            return False

        if not validate_password(new_password):
            return False

        # パスワードを更新
        hashed_password = get_password_hash(new_password)
        updated_user = self.user_repo.update_password(user.id, hashed_password)
        if not updated_user:
            return False

        # 全リフレッシュトークンを無効化（セキュリティ対策）
        self.revoke_user_tokens(user.id)
        return True

    def update_username(self, user_id: int, new_username: str) -> Optional[User]:
        """
        ユーザー名を更新

        Args:
            user_id: ユーザーID
            new_username: 新しいユーザー名

        Returns:
            更新されたユーザーまたはNone

        Raises:
            ValueError: バリデーションエラー
            RuntimeError: 重複エラー
        """
        if not validate_username(new_username):
            raise ValueError("ユーザー名は3〜30文字で、英数字とアンダースコアのみ使用可能です")

        if self.user_repo.is_username_taken(new_username, exclude_user_id=user_id):
            raise RuntimeError("このユーザー名は既に使用されています")

        return self.user_repo.update(user_id, username=new_username)

    def update_email(self, user_id: int, new_email: str, password: str) -> Optional[User]:
        """
        メールアドレスを更新

        Args:
            user_id: ユーザーID
            new_email: 新しいメールアドレス
            password: 確認用パスワード

        Returns:
            更新されたユーザーまたはNone

        Raises:
            ValueError: バリデーションエラー
            RuntimeError: 認証エラーや重複エラー
        """
        if not validate_email(new_email):
            raise ValueError("無効なメールアドレス形式です")

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise RuntimeError("ユーザーが見つかりません")

        if not verify_password(password, user.hashed_password):
            raise RuntimeError("パスワードが間違っています")

        if self.user_repo.is_email_taken(new_email, exclude_user_id=user_id):
            raise RuntimeError("このメールアドレスは既に使用されています")

        return self.user_repo.update(
            user_id,
            email=new_email,
            is_email_verified=False  # 新しいメールアドレスは再確認が必要
        )

    def update_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        パスワードを更新

        Args:
            user_id: ユーザーID
            current_password: 現在のパスワード
            new_password: 新しいパスワード

        Returns:
            更新成功フラグ

        Raises:
            ValueError: バリデーションエラー
            RuntimeError: 認証エラー
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise RuntimeError("ユーザーが見つかりません")

        if not verify_password(current_password, user.hashed_password):
            raise RuntimeError("現在のパスワードが間違っています")

        if not validate_password(new_password):
            raise ValueError("パスワードは8文字以上で、大文字、小文字、数字、特殊文字を含む必要があります")

        hashed_password = get_password_hash(new_password)
        updated_user = self.user_repo.update_password(user.id, hashed_password)

        if updated_user:
            # 全リフレッシュトークンを無効化（セキュリティ対策）
            self.revoke_user_tokens(user.id)
            return True

        return False

    def get_user_profile(self, user_id: int) -> Optional[dict]:
        """
        ユーザープロフィール情報を取得

        Args:
            user_id: ユーザーID

        Returns:
            プロフィール情報またはNone
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return None

        # 日次変換制限のリセットチェック
        self._check_and_reset_daily_limit(user)

        remaining_conversions = self._get_remaining_conversions(user)

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "is_premium": user.is_premium,
            "premium_expires_at": user.premium_expires_at.isoformat() if user.premium_expires_at else None,
            "daily_conversion_count": user.daily_conversion_count,
            "remaining_conversions": remaining_conversions,
            "created_at": user.created_at.isoformat()
        }

    def _check_and_reset_daily_limit(self, user: User) -> None:
        """日次制限のリセットチェック"""
        now = datetime.utcnow()
        if user.last_conversion_reset.date() < now.date():
            self.user_repo.update_daily_conversion_count(user.id, 0)

    def _get_remaining_conversions(self, user: User) -> int:
        """残り変換回数を取得"""
        if user.is_premium:
            # プレミアム期限をチェック
            if user.premium_expires_at and user.premium_expires_at < datetime.utcnow():
                self.user_repo.update(user.id, is_premium=False)
                return max(0, settings.free_user_daily_limit - user.daily_conversion_count)
            return -1  # 無制限

        return max(0, settings.free_user_daily_limit - user.daily_conversion_count)