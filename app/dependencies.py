"""
依存関係注入

アプリケーション全体で使用される依存関係を管理します。
"""

from typing import Optional, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import PyJWTError

from .config import get_settings
from .database import get_db, User
from .repositories import (
    UserRepository,
    ConversionRepository,
    FavoriteRepository,
    RefreshTokenRepository,
    ApiUsageRepository
)
from .services import (
    UserService,
    ConversionService,
    FavoritesService
)
from .exceptions import (
    AuthenticationError,
    invalid_credentials_error,
    invalid_token_error,
    to_http_exception
)

settings = get_settings()
security = HTTPBearer()


# === Database Dependencies ===

def get_database_session() -> Generator[Session, None, None]:
    """
    データベースセッション依存関数

    Returns:
        データベースセッション
    """
    yield from get_db()


# === Repository Dependencies ===

def get_user_repository(db: Session = Depends(get_database_session)) -> UserRepository:
    """ユーザーリポジトリ依存関数"""
    return UserRepository(db)


def get_conversion_repository(db: Session = Depends(get_database_session)) -> ConversionRepository:
    """変換履歴リポジトリ依存関数"""
    return ConversionRepository(db)


def get_favorite_repository(db: Session = Depends(get_database_session)) -> FavoriteRepository:
    """お気に入りリポジトリ依存関数"""
    return FavoriteRepository(db)


def get_refresh_token_repository(db: Session = Depends(get_database_session)) -> RefreshTokenRepository:
    """リフレッシュトークンリポジトリ依存関数"""
    return RefreshTokenRepository(db)


def get_api_usage_repository(db: Session = Depends(get_database_session)) -> ApiUsageRepository:
    """API使用履歴リポジトリ依存関数"""
    return ApiUsageRepository(db)


# === Service Dependencies ===

def get_user_service(db: Session = Depends(get_database_session)) -> UserService:
    """ユーザーサービス依存関数"""
    return UserService(db)


def get_conversion_service(db: Session = Depends(get_database_session)) -> ConversionService:
    """変換サービス依存関数"""
    return ConversionService(db)


def get_favorites_service(db: Session = Depends(get_database_session)) -> FavoritesService:
    """お気に入りサービス依存関数"""
    return FavoritesService(db)


# === Authentication Dependencies ===

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """
    現在のユーザー取得依存関数（JWT認証）

    Args:
        credentials: HTTPベアラー認証情報
        user_repo: ユーザーリポジトリ

    Returns:
        認証されたユーザー

    Raises:
        HTTPException: 認証エラー
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # アクセストークンであることを確認
        if payload.get("type") != "access":
            raise invalid_token_error("access token")

        username: str = payload.get("sub")
        if username is None:
            raise invalid_token_error("access token")

    except PyJWTError:
        raise to_http_exception(invalid_token_error("access token"))

    user = user_repo.get_by_username(username)
    if user is None:
        raise to_http_exception(invalid_credentials_error())

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    アクティブユーザー取得依存関数

    Args:
        current_user: 現在のユーザー

    Returns:
        アクティブユーザー

    Raises:
        HTTPException: ユーザーが無効またはメール未確認
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なユーザーです"
        )

    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="メールアドレスが確認されていません"
        )

    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    user_repo: UserRepository = Depends(get_user_repository)
) -> Optional[User]:
    """
    現在のユーザー取得依存関数（認証オプショナル）

    Args:
        credentials: HTTPベアラー認証情報（オプショナル）
        user_repo: ユーザーリポジトリ

    Returns:
        認証されたユーザーまたはNone
    """
    if not credentials:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # アクセストークンであることを確認
        if payload.get("type") != "access":
            return None

        username: str = payload.get("sub")
        if username is None:
            return None

        user = user_repo.get_by_username(username)
        if not user or not user.is_active or not user.is_email_verified:
            return None

        return user

    except PyJWTError:
        return None


# === Premium User Dependencies ===

def get_premium_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    プレミアムユーザー取得依存関数

    Args:
        current_user: 現在のアクティブユーザー

    Returns:
        プレミアムユーザー

    Raises:
        HTTPException: プレミアムユーザーでない場合
    """
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この機能はプレミアムユーザー限定です"
        )

    return current_user


# === Admin Dependencies ===

def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    管理者ユーザー取得依存関数

    Args:
        current_user: 現在のアクティブユーザー

    Returns:
        管理者ユーザー

    Raises:
        HTTPException: 管理者でない場合
    """
    # 現在の実装では管理者権限フィールドがないため、
    # 将来の拡張に備えてプレースホルダーとして実装
    # 実際の運用では User モデルに is_admin フィールドを追加することを推奨

    # 仮実装：特定のユーザー名を管理者とする
    admin_usernames = ["admin", "administrator"]
    if current_user.username not in admin_usernames:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )

    return current_user


# === Utility Dependencies ===

def get_pagination_params(
    skip: int = 0,
    limit: int = 100
) -> tuple[int, int]:
    """
    ページネーションパラメータ依存関数

    Args:
        skip: スキップ数
        limit: 取得上限

    Returns:
        (skip, limit) タプル

    Raises:
        HTTPException: パラメータが無効な場合
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip は 0 以上である必要があります"
        )

    if limit <= 0 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit は 1 以上 1000 以下である必要があります"
        )

    return skip, limit


def get_search_params(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[Optional[str], int, int]:
    """
    検索パラメータ依存関数

    Args:
        q: 検索クエリ
        skip: スキップ数
        limit: 取得上限

    Returns:
        (query, skip, limit) タプル

    Raises:
        HTTPException: パラメータが無効な場合
    """
    skip, limit = get_pagination_params(skip, limit)

    if q is not None and len(q.strip()) == 0:
        q = None

    return q, skip, limit