from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_manager_or_admin
from app.models.user import User as UserModel
from app.models.project import ProjectStatus
from app.schemas.project import (
    Project, ProjectCreate, ProjectUpdate, ProjectWithDetails,
    ProjectMember, ProjectMemberCreate, ProjectMemberUpdate, ProjectMemberWithDetails
)
from app.services.project import ProjectService
from app.services.websocket import websocket_service

router = APIRouter()


@router.get("/", response_model=List[Project])
async def read_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ProjectStatus] = None,
    owner_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get all projects with optional filtering"""
    # Regular users can only see projects they own or are members of
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        projects = ProjectService.get_user_projects(db, current_user.id)
        return projects[skip:skip + limit]
    
    # Managers and admins can see all projects with optional filtering
    projects = ProjectService.get_projects(
        db, 
        skip=skip, 
        limit=limit, 
        owner_id=owner_id, 
        status=status.value if status else None
    )
    return projects


@router.get("/my", response_model=List[Project])
async def read_my_projects(
    include_owned: bool = True,
    include_member: bool = True,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get projects where current user is owner or member"""
    projects = ProjectService.get_user_projects(
        db, 
        current_user.id, 
        include_owned=include_owned, 
        include_member=include_member
    )
    return projects


@router.get("/{project_id}", response_model=ProjectWithDetails)
async def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get project by ID with details"""
    project = ProjectService.get_project_with_details(db, project_id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        not ProjectService.is_project_owner(db, project_id, current_user.id) and
        not ProjectService.is_project_member(db, project_id, current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return project


@router.post("/", response_model=Project)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create new project"""
    # Only managers and admins can create projects
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create projects"
        )
    
    created_project = ProjectService.create_project(db=db, project=project, owner_id=current_user.id)
    
    # Send WebSocket notification
    await websocket_service.notify_project_update(
        created_project.id,
        {
            "action": "created",
            "project": {
                "id": created_project.id,
                "name": created_project.name,
                "owner_id": created_project.owner_id
            }
        }
    )
    
    return created_project


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update project"""
    # Check if project exists
    project = ProjectService.get_project(db, project_id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions (only owner, managers, or admins can update)
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        not ProjectService.is_project_owner(db, project_id, current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    updated_project = ProjectService.update_project(db, project_id=project_id, project_update=project_update)
    if updated_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_project_update(
        updated_project.id,
        {
            "action": "updated",
            "project": {
                "id": updated_project.id,
                "name": updated_project.name,
                "updated_at": updated_project.updated_at.isoformat() if updated_project.updated_at else None
            }
        }
    )
    
    return updated_project


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Delete project"""
    # Check if project exists
    project = ProjectService.get_project(db, project_id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions (only owner or admins can delete)
    if (current_user.role.value != "admin" and 
        not current_user.is_superuser and
        not ProjectService.is_project_owner(db, project_id, current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    success = ProjectService.delete_project(db, project_id=project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_project_update(
        project_id,
        {
            "action": "deleted",
            "project": {
                "id": project_id,
                "name": project.name
            }
        }
    )
    
    return {"message": "Project deleted successfully"}


# Project Members endpoints
@router.get("/{project_id}/members", response_model=List[ProjectMemberWithDetails])
async def read_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get all project members"""
    # Check if project exists
    project = ProjectService.get_project(db, project_id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        not ProjectService.is_project_owner(db, project_id, current_user.id) and
        not ProjectService.is_project_member(db, project_id, current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    members = ProjectService.get_project_members(db, project_id=project_id)
    return members


@router.post("/{project_id}/members", response_model=ProjectMember)
async def add_project_member(
    project_id: int,
    member_data: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Add member to project"""
    # Check if project exists
    project = ProjectService.get_project(db, project_id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions (only owner, managers, or admins can add members)
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        not ProjectService.is_project_owner(db, project_id, current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    member = ProjectService.add_project_member(
        db, 
        project_id=project_id, 
        member_data=member_data, 
        added_by_id=current_user.id
    )
    
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add member"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_project_update(
        project_id,
        {
            "action": "member_added",
            "member": {
                "user_id": member.user_id,
                "role": member.role.value
            }
        }
    )
    
    return member


@router.put("/{project_id}/members/{user_id}", response_model=ProjectMember)
async def update_project_member(
    project_id: int,
    user_id: int,
    member_update: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update project member"""
    # Check if project exists
    project = ProjectService.get_project(db, project_id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions (only owner, managers, or admins can update members)
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        not ProjectService.is_project_owner(db, project_id, current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    updated_member = ProjectService.update_project_member(
        db, 
        project_id=project_id, 
        user_id=user_id, 
        member_update=member_update
    )
    
    if updated_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_project_update(
        project_id,
        {
            "action": "member_updated",
            "member": {
                "user_id": updated_member.user_id,
                "role": updated_member.role.value
            }
        }
    )
    
    return updated_member


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Remove member from project"""
    # Check if project exists
    project = ProjectService.get_project(db, project_id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions (only owner, managers, or admins can remove members)
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        not ProjectService.is_project_owner(db, project_id, current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Prevent removing project owner
    if ProjectService.is_project_owner(db, project_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove project owner"
        )
    
    success = ProjectService.remove_project_member(db, project_id=project_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_project_update(
        project_id,
        {
            "action": "member_removed",
            "member": {
                "user_id": user_id
            }
        }
    )
    
    return {"message": "Project member removed successfully"}
