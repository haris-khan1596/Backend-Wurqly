from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ActivityLogBase(BaseModel):
    timestamp: datetime
    keyboard_strokes: int = 0
    mouse_clicks: int = 0
    mouse_moves: int = 0
    scroll_events: int = 0
    active_window_title: Optional[str] = None
    active_application: Optional[str] = None
    url_visited: Optional[str] = None
    productivity_score: Optional[float] = None
    is_productive: bool = True
    metadata: Optional[Dict[str, Any]] = None


class ActivityLogCreate(ActivityLogBase):
    time_entry_id: Optional[int] = None


class ActivityLogUpdate(BaseModel):
    keyboard_strokes: Optional[int] = None
    mouse_clicks: Optional[int] = None
    mouse_moves: Optional[int] = None
    scroll_events: Optional[int] = None
    active_window_title: Optional[str] = None
    active_application: Optional[str] = None
    url_visited: Optional[str] = None
    productivity_score: Optional[float] = None
    is_productive: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ActivityLogInDBBase(ActivityLogBase):
    id: int
    user_id: int
    time_entry_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ActivityLog(ActivityLogInDBBase):
    pass


class ActivityLogWithDetails(ActivityLog):
    from app.schemas.user import User
    from app.schemas.time_entry import TimeEntry
    
    user: Optional[User] = None
    time_entry: Optional[TimeEntry] = None


class ActivityLogBatch(BaseModel):
    """Schema for batch uploading activity logs"""
    activity_logs: list[ActivityLogCreate]
    
    
class ActivityLogSummary(BaseModel):
    """Schema for activity summary statistics"""
    total_keyboard_strokes: int
    total_mouse_clicks: int
    total_mouse_moves: int
    total_scroll_events: int
    average_productivity_score: Optional[float]
    productive_time_percentage: float
    most_used_applications: list[dict]
    time_period_start: datetime
    time_period_end: datetime
