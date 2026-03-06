from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func, Index
from sqlalchemy.orm import relationship
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    qrcodes = relationship("QRCode", back_populates="user", cascade="all, delete-orphan")

class QRCode(Base):
    __tablename__ = "qrcodes"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="qrcodes")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

Index("ix_qrcodes_user_created", QRCode.user_id, QRCode.created_at)