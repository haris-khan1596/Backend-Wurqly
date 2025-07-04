from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_hours: Optional[int] = None  # in minutes
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None


class TaskCreate(TaskBase):
    project_id: int


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    estimated_hours: Optional[int] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None


class TaskInDBBase(TaskBase):
    id: int
    project_id: int
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Task(TaskInDBBase):
    pass


class TaskWithDetails(Task):
    from app.schemas.user import User
    from app.schemas.project import Project
    from app.schemas.time_entry import TimeEntry
    
    project: Optional[Project] = None
    assignee: Optional[User] = None
    created_by: Optional[User] = None
    time_entries: List[TimeEntry] = []
