import re

from pydantic import BaseModel, field_validator


class SignupRequest(BaseModel):
    """サインアップリクエスト"""

    username: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 30:
            raise ValueError("ユーザー名は3〜30文字である必要があります")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("ユーザー名は英数字とアンダースコアのみ使用できます")
        return v


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
