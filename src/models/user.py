from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from .base import Base, IdMixin, TimestampMixin


class User(Base, IdMixin, TimestampMixin):
    """ユーザーモデル

    email は Firebase が管理するためここでは持たない。
    日次変換回数は api_usage テーブルから集計する。
    """

    __tablename__ = "users"

    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    is_premium = Column(Boolean, default=False)
    premium_expires_at = Column(DateTime, nullable=True)

    # リレーション
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    api_usage = relationship("ApiUsage", back_populates="user", cascade="all, delete-orphan")
