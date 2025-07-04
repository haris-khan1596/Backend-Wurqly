from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.time_entry import TimeEntryStatus


class TimeEntryBase(BaseModel):
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None  # in seconds
    status: TimeEntryStatus = TimeEntryStatus.RUNNING
    is_billable: bool = True
    hourly_rate: Optional[int] = None  # in cents


class TimeEntryCreate(TimeEntryBase):
    project_id: int
    task_id: Optional[int] = None


class TimeEntryUpdate(BaseModel):
    description: Optional[str] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    status: Optional[TimeEntryStatus] = None
    is_billable: Optional[bool] = None
    hourly_rate: Optional[int] = None


class TimeEntryInDBBase(TimeEntryBase):
    id: int
    user_id: int
    project_id: int
    task_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TimeEntry(TimeEntryInDBBase):
    pass


class TimeEntryWithDetails(TimeEntry):
    from app.schemas.user import User
    from app.schemas.project import Project
    from app.schemas.task import Task
    from app.schemas.activity_log import ActivityLog
    from app.schemas.screenshot import Screenshot
    
    user: Optional[User] = None
    project: Optional[Project] = None
    task: Optional[Task] = None
    activity_logs: List[ActivityLog] = []
    screenshots: List[Screenshot] = []


class TimeEntryStart(BaseModel):
    project_id: int
    task_id: Optional[int] = None
    description: Optional[str] = None


class TimeEntryStop(BaseModel):
    description: Optional[str] = None
