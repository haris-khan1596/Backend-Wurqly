from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.screenshot import ScreenshotStatus


class ScreenshotBase(BaseModel):
    filename: str
    file_path: str
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_blurred: bool = False
    blur_level: int = 0
    status: ScreenshotStatus = ScreenshotStatus.PENDING
    thumbnail_path: Optional[str] = None
    captured_at: datetime


class ScreenshotCreate(ScreenshotBase):
    time_entry_id: Optional[int] = None


class ScreenshotUpdate(BaseModel):
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_blurred: Optional[bool] = None
    blur_level: Optional[int] = None
    status: Optional[ScreenshotStatus] = None
    thumbnail_path: Optional[str] = None


class ScreenshotInDBBase(ScreenshotBase):
    id: int
    user_id: int
    time_entry_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Screenshot(ScreenshotInDBBase):
    pass


class ScreenshotWithDetails(Screenshot):
    from app.schemas.user import User
    from app.schemas.time_entry import TimeEntry
    
    user: Optional[User] = None
    time_entry: Optional[TimeEntry] = None


class ScreenshotUpload(BaseModel):
    """Schema for screenshot upload request"""
    time_entry_id: Optional[int] = None
    is_blurred: bool = False
    blur_level: int = 0
    captured_at: Optional[datetime] = None


class ScreenshotResponse(BaseModel):
    """Schema for screenshot upload response"""
    id: int
    filename: str
    file_path: str
    thumbnail_path: Optional[str] = None
    status: ScreenshotStatus
    captured_at: datetime
