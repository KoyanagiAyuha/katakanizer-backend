import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./katakanizer.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)