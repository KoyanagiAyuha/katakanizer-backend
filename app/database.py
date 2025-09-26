import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import OperationalError
from datetime import datetime

from .config import get_settings

settings = get_settings()

if settings.is_sqlite:
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
else:
    # PostgreSQL用の接続プール設定を改善（Neon対応）
    engine = create_engine(
        settings.database_url,
        # 接続プールの設定（Neonのアイドル対策）
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # 接続前にpingして死んだ接続を検出（重要）
        connect_args={
            "keepalives": 1,
            "keepalives_idle": 10,  # より短い間隔でキープアライブ
            "keepalives_interval": 5,
            "keepalives_count": 3,
            "connect_timeout": 10,  # 接続タイムアウト設定
        }
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_premium = Column(Boolean, default=False)
    premium_expires_at = Column(DateTime, nullable=True)
    daily_conversion_count = Column(Integer, default=0)
    last_conversion_reset = Column(DateTime, default=datetime.utcnow)

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    api_usage = relationship("ApiUsage", back_populates="user", cascade="all, delete-orphan")


class ConversionHistory(Base):
    __tablename__ = "conversion_history"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    original_text = Column(Text)
    language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, default=True)  # 公開設定
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # ユーザーID（既存レコード対応でnullable=True）
    
    # Relationships
    line_mappings = relationship("LineMapping", back_populates="conversion", cascade="all, delete-orphan", order_by="LineMapping.line_order")
    user = relationship("User")
    favorited_by = relationship("Favorite", back_populates="conversion", cascade="all, delete-orphan")

class LineMapping(Base):
    __tablename__ = "line_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    conversion_id = Column(Integer, ForeignKey("conversion_history.id"), nullable=False)
    line_text = Column(Text, nullable=False)
    casual_katakana = Column(Text, nullable=False)
    formal_katakana = Column(Text, nullable=False)
    line_order = Column(Integer, nullable=False)  # 行の順序
    
    # Relationship
    conversion = relationship("ConversionHistory", back_populates="line_mappings")
    
    # Index for faster lookups
    __table_args__ = (
        Index('idx_line_mapping_conversion', 'conversion_id', 'line_order'),
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    
    # Relationship
    user = relationship("User", back_populates="refresh_tokens")
    
    # Index for faster lookups
    __table_args__ = (
        Index('idx_refresh_token_user', 'user_id', 'revoked'),
    )


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversion_id = Column(Integer, ForeignKey("conversion_history.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="favorites")
    conversion = relationship("ConversionHistory", back_populates="favorited_by")

    # Indexes and Constraints
    __table_args__ = (
        Index('idx_favorite_user_conversion', 'user_id', 'conversion_id', unique=True),
        Index('idx_favorite_created', 'created_at'),
    )


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    request_date = Column(DateTime, default=datetime.utcnow)
    response_time_ms = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_usage")

    # Indexes
    __table_args__ = (
        Index('idx_api_usage_user_date', 'user_id', 'request_date'),
    )


def get_db():
    """データベースセッションを取得（リトライ機能付き）"""
    retries = 3
    for attempt in range(retries):
        try:
            db = SessionLocal()
            # 接続確認のためのテストクエリ
            db.execute(text("SELECT 1"))
            try:
                yield db
            finally:
                db.close()
            break
        except OperationalError as e:
            if attempt < retries - 1:
                time.sleep(1)  # リトライ前に少し待機
                continue
            else:
                raise e

def create_tables():
    Base.metadata.create_all(bind=engine)