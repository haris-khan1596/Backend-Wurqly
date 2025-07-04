from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Activity metrics
    keyboard_strokes = Column(Integer, default=0, nullable=False)
    mouse_clicks = Column(Integer, default=0, nullable=False)
    mouse_moves = Column(Integer, default=0, nullable=False)
    scroll_events = Column(Integer, default=0, nullable=False)
    
    # Application tracking
    active_window_title = Column(String(500), nullable=True)
    active_application = Column(String(255), nullable=True)
    url_visited = Column(String(1000), nullable=True)
    
    # Productivity metrics
    productivity_score = Column(Float, nullable=True)  # 0.0 to 1.0
    is_productive = Column(Boolean, default=True, nullable=False)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="activity_logs")
    
    time_entry_id = Column(Integer, ForeignKey("time_entries.id"), nullable=True)
    time_entry = relationship("TimeEntry", back_populates="activity_logs")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
