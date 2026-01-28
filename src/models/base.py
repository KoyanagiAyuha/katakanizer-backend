from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """created_at を自動付与する Mixin"""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class IdMixin:
    """id を自動付与する Mixin"""

    id = Column(Integer, primary_key=True, index=True)
