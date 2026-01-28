from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from .base import Base, IdMixin, TimestampMixin


class ApiUsage(Base, IdMixin, TimestampMixin):
    __tablename__ = "api_usage"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)

    user = relationship("User", back_populates="api_usage")

    __table_args__ = (Index("idx_api_usage_user_date", "user_id", "created_at"),)
