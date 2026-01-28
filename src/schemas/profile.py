from pydantic import BaseModel


class UserResponse(BaseModel):
    """ユーザーレスポンス"""

    id: int
    username: str
    is_premium: bool
    created_at: str


class UserProfileResponse(BaseModel):
    """プロフィールレスポンス"""

    id: int
    username: str
    is_premium: bool
    premium_expires_at: str | None = None
    daily_usage: int
    daily_limit: int
    remaining_conversions: int
    created_at: str


class UpdateUsernameRequest(BaseModel):
    """ユーザー名更新リクエスト"""

    new_username: str
