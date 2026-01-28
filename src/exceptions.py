from fastapi import HTTPException, status


class BaseKatakanizerException(Exception):
    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str | None = None,
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(BaseKatakanizerException):
    def __init__(self, message: str, field: str | None = None, details: dict | None = None):
        super().__init__(message=message, details=details, error_code="VALIDATION_ERROR")
        self.field = field


class AuthenticationError(BaseKatakanizerException):
    def __init__(self, message: str = "認証に失敗しました", details: dict | None = None):
        super().__init__(message=message, details=details, error_code="AUTHENTICATION_ERROR")


class AuthorizationError(BaseKatakanizerException):
    def __init__(
        self, message: str = "この操作を実行する権限がありません", details: dict | None = None
    ):
        super().__init__(message=message, details=details, error_code="AUTHORIZATION_ERROR")


class NotFoundError(BaseKatakanizerException):
    def __init__(
        self,
        message: str = "要求されたリソースが見つかりません",
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
    ):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message=message, details=details, error_code="NOT_FOUND_ERROR")


class ConflictError(BaseKatakanizerException):
    def __init__(
        self,
        message: str = "リソースの競合が発生しました",
        conflicting_field: str | None = None,
        details: dict | None = None,
    ):
        details = details or {}
        if conflicting_field:
            details["conflicting_field"] = conflicting_field
        super().__init__(message=message, details=details, error_code="CONFLICT_ERROR")


class RateLimitError(BaseKatakanizerException):
    def __init__(
        self,
        message: str = "API利用制限に達しました",
        remaining_requests: int | None = None,
        reset_time: str | None = None,
        is_premium: bool = False,
        details: dict | None = None,
    ):
        details = details or {}
        if remaining_requests is not None:
            details["remaining_requests"] = remaining_requests
        if reset_time:
            details["reset_time"] = reset_time
        details["is_premium"] = is_premium
        super().__init__(message=message, details=details, error_code="RATE_LIMIT_ERROR")


class ConversionError(BaseKatakanizerException):
    def __init__(
        self, message: str = "変換処理中にエラーが発生しました", details: dict | None = None
    ):
        super().__init__(message=message, details=details, error_code="CONVERSION_ERROR")


class ExternalServiceError(BaseKatakanizerException):
    def __init__(
        self,
        message: str = "外部サービスとの通信中にエラーが発生しました",
        service_name: str | None = None,
        details: dict | None = None,
    ):
        details = details or {}
        if service_name:
            details["service_name"] = service_name
        super().__init__(message=message, details=details, error_code="EXTERNAL_SERVICE_ERROR")


EXCEPTION_STATUS_MAP = {
    ValidationError: status.HTTP_400_BAD_REQUEST,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    ConversionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
}


def to_http_exception(exception: BaseKatakanizerException) -> HTTPException:
    status_code = EXCEPTION_STATUS_MAP.get(type(exception), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return HTTPException(
        status_code=status_code,
        detail={
            "message": exception.message,
            "error_code": exception.error_code,
            "details": exception.details,
        },
    )


def username_taken_error(username: str) -> ConflictError:
    return ConflictError(
        message="このユーザー名は既に使用されています",
        conflicting_field="username",
        details={"username": username},
    )


def email_taken_error(email: str) -> ConflictError:
    return ConflictError(
        message="このメールアドレスは既に登録されています",
        conflicting_field="email",
        details={"email": email},
    )


def user_not_found_error(identifier: str) -> NotFoundError:
    return NotFoundError(
        message="ユーザーが見つかりません",
        resource_type="user",
        resource_id=identifier,
    )


def conversion_not_found_error(conversion_id: int) -> NotFoundError:
    return NotFoundError(
        message="変換履歴が見つかりません",
        resource_type="conversion",
        resource_id=str(conversion_id),
    )


def rate_limit_exceeded_error(
    remaining: int, reset_time: str, is_premium: bool = False
) -> RateLimitError:
    details = {
        "remaining_conversions": remaining,
        "reset_time": reset_time,
        "is_premium": is_premium,
    }
    if not is_premium:
        details["upgrade_message"] = "プレミアムプランにアップグレードすると無制限に変換できます"

    return RateLimitError(
        message="本日の変換回数制限に達しました",
        remaining_requests=remaining,
        reset_time=reset_time,
        is_premium=is_premium,
        details=details,
    )
