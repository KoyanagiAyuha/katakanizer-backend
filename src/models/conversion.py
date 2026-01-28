from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base, IdMixin, TimestampMixin


class ConversionHistory(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversion_history"

    title = Column(String, index=True)
    original_text = Column(Text)
    language = Column(String, default="en")
    is_public = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    line_mappings = relationship(
        "LineMapping",
        back_populates="conversion",
        cascade="all, delete-orphan",
        order_by="LineMapping.line_order",
    )
    user = relationship("User")
    favorited_by = relationship(
        "Favorite", back_populates="conversion", cascade="all, delete-orphan"
    )


class LineMapping(Base, IdMixin):
    __tablename__ = "line_mappings"

    conversion_id = Column(Integer, ForeignKey("conversion_history.id"), nullable=False)
    line_text = Column(Text, nullable=False)
    casual_katakana = Column(Text, nullable=False)
    formal_katakana = Column(Text, nullable=False)
    line_order = Column(Integer, nullable=False)

    conversion = relationship("ConversionHistory", back_populates="line_mappings")

    __table_args__ = (Index("idx_line_mapping_conversion", "conversion_id", "line_order"),)
