"""
カスタム例外クラス

アプリケーション固有の例外を定義し、一貫したエラーハンドリングを提供します。
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseKatakanizerException(Exception):
    """基底例外クラス"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(BaseKatakanizerException):
    """バリデーションエラー"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details,
            error_code="VALIDATION_ERROR"
        )
        self.field = field


class AuthenticationError(BaseKatakanizerException):
    """認証エラー"""

    def __init__(
        self,
        message: str = "認証に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(BaseKatakanizerException):
    """認可エラー"""

    def __init__(
        self,
        message: str = "この操作を実行する権限がありません",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details,
            error_code="AUTHORIZATION_ERROR"
        )


class NotFoundError(BaseKatakanizerException):
    """リソース未発見エラー"""

    def __init__(
        self,
        message: str = "要求されたリソースが見つかりません",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            details=details,
            error_code="NOT_FOUND_ERROR"
        )


class ConflictError(BaseKatakanizerException):
    """競合エラー"""

    def __init__(
        self,
        message: str = "リソースの競合が発生しました",
        conflicting_field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if conflicting_field:
            details["conflicting_field"] = conflicting_field

        super().__init__(
            message=message,
            details=details,
            error_code="CONFLICT_ERROR"
        )


class RateLimitError(BaseKatakanizerException):
    """レート制限エラー"""

    def __init__(
        self,
        message: str = "API利用制限に達しました",
        remaining_requests: Optional[int] = None,
        reset_time: Optional[str] = None,
        is_premium: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if remaining_requests is not None:
            details["remaining_requests"] = remaining_requests
        if reset_time:
            details["reset_time"] = reset_time
        details["is_premium"] = is_premium

        super().__init__(
            message=message,
            details=details,
            error_code="RATE_LIMIT_ERROR"
        )


class ConversionError(BaseKatakanizerException):
    """変換処理エラー"""

    def __init__(
        self,
        message: str = "変換処理中にエラーが発生しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details,
            error_code="CONVERSION_ERROR"
        )


class EmailError(BaseKatakanizerException):
    """メール送信エラー"""

    def __init__(
        self,
        message: str = "メール送信に失敗しました",
        email_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if email_type:
            details["email_type"] = email_type

        super().__init__(
            message=message,
            details=details,
            error_code="EMAIL_ERROR"
        )


class DatabaseError(BaseKatakanizerException):
    """データベースエラー"""

    def __init__(
        self,
        message: str = "データベース操作中にエラーが発生しました",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            details=details,
            error_code="DATABASE_ERROR"
        )


class ExternalServiceError(BaseKatakanizerException):
    """外部サービスエラー"""

    def __init__(
        self,
        message: str = "外部サービスとの通信中にエラーが発生しました",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if service_name:
            details["service_name"] = service_name

        super().__init__(
            message=message,
            details=details,
            error_code="EXTERNAL_SERVICE_ERROR"
        )


# HTTPException変換マッピング
EXCEPTION_STATUS_MAP = {
    ValidationError: status.HTTP_400_BAD_REQUEST,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    ConversionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    EmailError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
}


def to_http_exception(exception: BaseKatakanizerException) -> HTTPException:
    """
    カスタム例外をHTTPExceptionに変換

    Args:
        exception: カスタム例外

    Returns:
        HTTPException
    """
    status_code = EXCEPTION_STATUS_MAP.get(
        type(exception),
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    detail = {
        "message": exception.message,
        "error_code": exception.error_code,
        "details": exception.details
    }

    return HTTPException(
        status_code=status_code,
        detail=detail
    )


# 便利な例外生成関数
def username_taken_error(username: str) -> ConflictError:
    """ユーザー名重複エラー"""
    return ConflictError(
        message="このユーザー名は既に使用されています",
        conflicting_field="username",
        details={"username": username}
    )


def email_taken_error(email: str) -> ConflictError:
    """メールアドレス重複エラー"""
    return ConflictError(
        message="このメールアドレスは既に登録されています",
        conflicting_field="email",
        details={"email": email}
    )


def invalid_credentials_error() -> AuthenticationError:
    """認証情報無効エラー"""
    return AuthenticationError(
        message="ユーザー名またはパスワードが間違っています"
    )


def email_not_verified_error() -> AuthenticationError:
    """メール未確認エラー"""
    return AuthenticationError(
        message="メールアドレスが確認されていません。メールを確認して、アカウントを認証してからログインしてください。"
    )


def user_not_found_error(identifier: str) -> NotFoundError:
    """ユーザー未発見エラー"""
    return NotFoundError(
        message="ユーザーが見つかりません",
        resource_type="user",
        resource_id=identifier
    )


def conversion_not_found_error(conversion_id: int) -> NotFoundError:
    """変換履歴未発見エラー"""
    return NotFoundError(
        message="変換履歴が見つかりません",
        resource_type="conversion",
        resource_id=str(conversion_id)
    )


def invalid_token_error(token_type: str = "token") -> AuthenticationError:
    """無効トークンエラー"""
    return AuthenticationError(
        message=f"無効または期限切れの{token_type}です",
        details={"token_type": token_type}
    )


def rate_limit_exceeded_error(
    remaining: int,
    reset_time: str,
    is_premium: bool = False
) -> RateLimitError:
    """レート制限超過エラー"""
    message = "本日の変換回数制限に達しました"
    upgrade_message = "プレミアムプランにアップグレードすると無制限に変換できます" if not is_premium else None

    details = {
        "remaining_conversions": remaining,
        "reset_time": reset_time,
        "is_premium": is_premium
    }
    if upgrade_message:
        details["upgrade_message"] = upgrade_message

    return RateLimitError(
        message=message,
        remaining_requests=remaining,
        reset_time=reset_time,
        is_premium=is_premium,
        details=details
    )