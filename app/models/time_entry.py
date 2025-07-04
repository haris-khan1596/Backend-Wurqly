from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class TimeEntryStatus(str, enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    APPROVED = "approved"
    REJECTED = "rejected"


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    status = Column(Enum(TimeEntryStatus), default=TimeEntryStatus.RUNNING, nullable=False)
    is_billable = Column(Boolean, default=True, nullable=False)
    hourly_rate = Column(Integer, nullable=True)  # in cents, overrides project rate
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="time_entries")
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="time_entries")
    
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    task = relationship("Task", back_populates="time_entries")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    activity_logs = relationship("ActivityLog", back_populates="time_entry", cascade="all, delete-orphan")
    screenshots = relationship("Screenshot", back_populates="time_entry", cascade="all, delete-orphan")
