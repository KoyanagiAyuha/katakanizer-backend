"""
認証ルーター

ユーザー認証関連のエンドポイントを提供します。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import (
    get_database_session,
    get_user_service,
    get_current_active_user
)
from ..services import UserService
from ..database import User
from ..config import get_settings
from ..models.auth import (
    UserRegisterRequest, UserLoginRequest, UserResponse,
    Token, RefreshTokenRequest, EmailVerificationRequest,
    PasswordResetRequest, PasswordResetConfirmRequest,
    ResendVerificationRequest, RegistrationResponse
)
from ..exceptions import (
    ValidationError,
    ConflictError,
    AuthenticationError,
    NotFoundError,
    to_http_exception,
    username_taken_error,
    email_taken_error,
    invalid_credentials_error,
    email_not_verified_error,
    user_not_found_error,
    invalid_token_error
)

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegistrationResponse)
async def register_user(
    request: UserRegisterRequest,
    user_service: UserService = Depends(get_user_service)
):
    """ユーザー登録"""
    try:
        user, message = user_service.register_user(
            username=request.username,
            email=request.email,
            password=request.password
        )

        # メール確認用メールを送信
        try:
            await user_service.send_verification_email(user)
        except Exception as e:
            print(f"メール送信エラー: {e}")

        return RegistrationResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at.isoformat(),
            message=message
        )

    except (ValidationError, ConflictError) as e:
        raise to_http_exception(e)
    except RuntimeError as e:
        error_msg = str(e)
        if "ユーザー名" in error_msg:
            raise to_http_exception(username_taken_error(request.username))
        elif "メールアドレス" in error_msg:
            raise to_http_exception(email_taken_error(request.email))
        else:
            raise HTTPException(status_code=500, detail=error_msg)


@router.post("/login", response_model=Token)
def login_user(
    request: UserLoginRequest,
    user_service: UserService = Depends(get_user_service)
):
    """ユーザーログイン"""
    # ユーザー認証
    user = user_service.authenticate_user(request.username, request.password)
    if not user:
        raise to_http_exception(invalid_credentials_error())

    # メール確認チェック
    if not user.is_email_verified:
        raise to_http_exception(email_not_verified_error())

    # 既存のリフレッシュトークンを無効化
    user_service.revoke_user_tokens(user.id)

    # 新しいトークンペアを生成
    access_token, refresh_token = user_service.create_tokens(user)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    request: RefreshTokenRequest,
    user_service: UserService = Depends(get_user_service)
):
    """リフレッシュトークンを使用してアクセストークンを再発行"""
    user = user_service.verify_refresh_token(request.refresh_token)
    if not user:
        raise to_http_exception(invalid_token_error("refresh token"))

    # 古いリフレッシュトークンを無効化
    user_service.revoke_token(request.refresh_token)

    # 新しいトークンペアを生成
    access_token, refresh_token = user_service.create_tokens(user)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/logout")
def logout_user(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """ログアウト（全リフレッシュトークンを無効化）"""
    user_service.revoke_user_tokens(current_user.id)
    return {"message": "ログアウトしました"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """現在のユーザー情報取得（要認証）"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    user_service: UserService = Depends(get_user_service)
):
    """メールアドレス確認"""
    user = await user_service.verify_email(request.token)
    if not user:
        raise to_http_exception(invalid_token_error("verification token"))

    return {"message": "メールアドレスの確認が完了しました"}


@router.post("/resend-verification")
async def resend_verification_email(
    request: ResendVerificationRequest,
    user_service: UserService = Depends(get_user_service)
):
    """メール確認メール再送信"""
    try:
        # パブリックエンドポイントなので、ユーザーサービスを通じて処理
        # セキュリティ上、常に成功レスポンスを返す
        await user_service.request_password_reset(request.email)
        return {"message": "確認メールを送信しました"}
    except Exception:
        # エラーが発生してもセキュリティ上成功レスポンスを返す
        return {"message": "確認メールを送信しました"}


@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    user_service: UserService = Depends(get_user_service)
):
    """パスワードリセットリクエスト"""
    try:
        await user_service.request_password_reset(request.email)
        # セキュリティ上、メールアドレスが存在しなくても成功レスポンスを返す
        return {"message": "該当するメールアドレスのアカウントが存在する場合、パスワードリセットリンクを送信しました"}
    except Exception:
        # エラーが発生してもセキュリティ上成功レスポンスを返す
        return {"message": "該当するメールアドレスのアカウントが存在する場合、パスワードリセットリンクを送信しました"}


@router.post("/reset-password")
def reset_user_password(
    request: PasswordResetConfirmRequest,
    user_service: UserService = Depends(get_user_service)
):
    """パスワードリセット実行"""
    try:
        success = user_service.reset_password(request.token, request.new_password)
        if not success:
            raise to_http_exception(invalid_token_error("reset token"))

        return {"message": "パスワードのリセットが完了しました"}
    except ValidationError as e:
        raise to_http_exception(e)