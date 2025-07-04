from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ScreenshotStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    FAILED = "failed"
    DELETED = "deleted"


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Privacy settings
    is_blurred = Column(Boolean, default=False, nullable=False)
    blur_level = Column(Integer, default=0, nullable=False)  # 0-100
    
    # Status and metadata
    status = Column(Enum(ScreenshotStatus), default=ScreenshotStatus.PENDING, nullable=False)
    thumbnail_path = Column(String(1000), nullable=True)
    
    # Timing
    captured_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="screenshots")
    
    time_entry_id = Column(Integer, ForeignKey("time_entries.id"), nullable=True)
    time_entry = relationship("TimeEntry", back_populates="screenshots")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
