"""
アプリケーション設定管理

Pydantic BaseSettingsを使用した型安全な設定管理を提供します。
環境変数の自動検証とデフォルト値の管理を行います。
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    """アプリケーション設定クラス"""

    # Database settings
    database_url: str = Field(
        default="sqlite:///./katakanizer.db",
        env="DATABASE_URL",
        description="データベース接続URL"
    )

    # JWT settings
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY",
        description="JWT署名用秘密鍵"
    )
    jwt_refresh_secret_key: str = Field(
        default="your-refresh-secret-key-change-in-production",
        env="JWT_REFRESH_SECRET_KEY",
        description="JWT リフレッシュトークン署名用秘密鍵"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        env="JWT_ALGORITHM",
        description="JWT暗号化アルゴリズム"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=15,
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        description="アクセストークン有効期限（分）"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        env="JWT_REFRESH_TOKEN_EXPIRE_DAYS",
        description="リフレッシュトークン有効期限（日）"
    )

    # OpenAI settings
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API キー"
    )

    # Email settings
    resend_api_key: Optional[str] = Field(
        default=None,
        env="RESEND_API_KEY",
        description="Resend メールサービス API キー"
    )
    from_email: str = Field(
        default="noreply@katakanizer.com",
        env="FROM_EMAIL",
        description="送信元メールアドレス"
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        env="FRONTEND_URL",
        description="フロントエンドURL（メール内リンク用）"
    )

    # CORS settings
    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
        description="CORS許可オリジン"
    )

    # Database connection pool settings (for PostgreSQL)
    db_pool_size: int = Field(
        default=2,
        env="DB_POOL_SIZE",
        description="データベース接続プールサイズ"
    )
    db_max_overflow: int = Field(
        default=3,
        env="DB_MAX_OVERFLOW",
        description="データベース接続プール最大オーバーフロー"
    )
    db_pool_timeout: int = Field(
        default=30,
        env="DB_POOL_TIMEOUT",
        description="データベース接続プールタイムアウト（秒）"
    )
    db_pool_recycle: int = Field(
        default=300,
        env="DB_POOL_RECYCLE",
        description="データベース接続再利用時間（秒）"
    )

    # Rate limiting settings
    free_user_daily_limit: int = Field(
        default=5,
        env="FREE_USER_DAILY_LIMIT",
        description="無料ユーザーの日次変換制限"
    )

    # Application settings
    debug: bool = Field(
        default=False,
        env="DEBUG",
        description="デバッグモード"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS設定をリストとして取得"""
        if not self.cors_origins:
            return ["http://localhost:3000"]

        # JSON配列形式の場合
        if self.cors_origins.startswith('[') and self.cors_origins.endswith(']'):
            try:
                return json.loads(self.cors_origins)
            except (json.JSONDecodeError, TypeError):
                pass

        # カンマ区切りとして処理
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator('database_url', mode='before')
    @classmethod
    def fix_database_url(cls, v):
        """PostgreSQL URLをpsycopg3用に調整"""
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://")
        return v

    @property
    def is_postgresql(self) -> bool:
        """PostgreSQLデータベースかどうか判定"""
        return self.database_url and not self.database_url.startswith("sqlite")

    @property
    def is_sqlite(self) -> bool:
        """SQLiteデータベースかどうか判定"""
        return self.database_url and self.database_url.startswith("sqlite")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


# グローバル設定インスタンス
settings = Settings()


def get_settings() -> Settings:
    """設定インスタンスを取得"""
    return settings