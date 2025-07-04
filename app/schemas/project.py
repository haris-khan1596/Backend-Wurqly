from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    hourly_rate: Optional[int] = None  # in cents
    budget: Optional[int] = None  # in cents
    deadline: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    status: Optional[ProjectStatus] = None
    hourly_rate: Optional[int] = None
    budget: Optional[int] = None
    deadline: Optional[datetime] = None


class ProjectInDBBase(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Project(ProjectInDBBase):
    pass


class ProjectWithDetails(Project):
    # Include related data when needed
    from app.schemas.user import User
    from app.schemas.task import Task
    from app.schemas.time_entry import TimeEntry
    
    owner: Optional[User] = None
    tasks: List[Task] = []
    time_entries: List[TimeEntry] = []


class ProjectMemberBase(BaseModel):
    from app.models.project_member import ProjectRole
    
    role: ProjectRole
    hourly_rate: Optional[int] = None
    is_active: bool = True


class ProjectMemberCreate(ProjectMemberBase):
    user_id: int


class ProjectMemberUpdate(BaseModel):
    from app.models.project_member import ProjectRole
    
    role: Optional[ProjectRole] = None
    hourly_rate: Optional[int] = None
    is_active: Optional[bool] = None


class ProjectMemberInDBBase(ProjectMemberBase):
    id: int
    project_id: int
    user_id: int
    added_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectMember(ProjectMemberInDBBase):
    pass


class ProjectMemberWithDetails(ProjectMember):
    from app.schemas.user import User
    
    user: Optional[User] = None
    added_by: Optional[User] = None
