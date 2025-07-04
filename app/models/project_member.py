from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ProjectRole(str, enum.Enum):
    MEMBER = "member"
    MANAGER = "manager"
    ADMIN = "admin"


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='unique_project_member'),
    )

    id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(ProjectRole), default=ProjectRole.MEMBER, nullable=False)
    hourly_rate = Column(Integer, nullable=True)  # in cents, overrides project rate
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="project_members")
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="project_memberships")
    
    # Who added this member
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_by = relationship("User", foreign_keys=[added_by_id])
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
