from sqlalchemy import Column, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from .base import Base, IdMixin, TimestampMixin


class Favorite(Base, IdMixin, TimestampMixin):
    __tablename__ = "favorites"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversion_id = Column(Integer, ForeignKey("conversion_history.id"), nullable=False)

    user = relationship("User", back_populates="favorites")
    conversion = relationship("ConversionHistory", back_populates="favorited_by")

    __table_args__ = (
        Index("idx_favorite_user_conversion", "user_id", "conversion_id", unique=True),
        Index("idx_favorite_created", "created_at"),
    )
