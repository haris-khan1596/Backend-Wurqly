from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User as UserModel
from app.models.task import TaskStatus, TaskPriority
from app.schemas.task import Task, TaskCreate, TaskUpdate, TaskWithDetails
from app.services.task import TaskService
from app.services.websocket import websocket_service

router = APIRouter()


@router.get("/", response_model=List[Task])
async def read_tasks(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee_id: Optional[int] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get all tasks with optional filtering"""
    # Regular users can only see tasks they are assigned to or created
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        tasks = TaskService.get_user_tasks(db, user_id=current_user.id)
        return tasks[skip:skip + limit]
    
    # Managers and admins can see all tasks with optional filtering
    tasks = TaskService.get_tasks(
        db, 
        skip=skip, 
        limit=limit, 
        assignee_id=assignee_id, 
        project_id=project_id, 
        status=status.value if status else None, 
        priority=priority.value if priority else None
    )
    return tasks


@router.get("/{task_id}", response_model=TaskWithDetails)
async def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get task by ID with details"""
    task = TaskService.get_task_with_details(db, task_id=task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        task.assignee_id != current_user.id and
        task.created_by_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return task


@router.post("/", response_model=Task)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create new task"""
    # Only managers and admins can create tasks
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create tasks"
        )
    
    created_task = TaskService.create_task(db=db, task=task, created_by_id=current_user.id)
    
    # Send WebSocket notification
    await websocket_service.notify_task_update(
        created_task.project_id,
        {
            "action": "created",
            "task": {
                "id": created_task.id,
                "title": created_task.title,
                "project_id": created_task.project_id
            }
        }
    )
    
    return created_task


@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update task"""
    # Check if task exists
    task = TaskService.get_task(db, task_id=task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions (only assignee, creator, managers, or admins can update)
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and 
        task.assignee_id != current_user.id and 
        task.created_by_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    updated_task = TaskService.update_task(db=db, task_id=task_id, task_update=task_update)
    if updated_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_task_update(
        updated_task.project_id,
        {
            "action": "updated",
            "task": {
                "id": updated_task.id,
                "title": updated_task.title,
                "updated_at": updated_task.updated_at.isoformat() if updated_task.updated_at else None
            }
        }
    )
    
    return updated_task


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Delete task"""
    # Check if task exists
    task = TaskService.get_task(db, task_id=task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions (only creator or admins can delete)
    if (current_user.role.value != "admin" and 
        not current_user.is_superuser and
        task.created_by_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    success = TaskService.delete_task(db=db, task_id=task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_task_update(
        task.project_id,
        {
            "action": "deleted",
            "task": {
                "id": task.id,
                "title": task.title
            }
        }
    )
    
    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/assign/{assignee_id}", response_model=Task)
async def assign_task(
    task_id: int,
    assignee_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Assign task to a user"""
    # Check if task exists
    task = TaskService.get_task(db, task_id=task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions (only managers or admins can assign)
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to assign tasks"
        )
    
    updated_task = TaskService.assign_task(db=db, task_id=task_id, assignee_id=assignee_id)
    if updated_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_task_update(
        updated_task.project_id,
        {
            "action": "assigned",
            "task": {
                "id": updated_task.id,
                "title": updated_task.title,
                "assignee_id": assignee_id
            }
        }
    )
    
    return updated_task


@router.post("/{task_id}/unassign", response_model=Task)
async def unassign_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Unassign task from current assignee"""
    # Check if task exists
    task = TaskService.get_task(db, task_id=task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions (only managers, assignees or admins can unassign)
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        task.assignee_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to unassign tasks"
        )
    
    updated_task = TaskService.unassign_task(db=db, task_id=task_id)
    if updated_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_task_update(
        updated_task.project_id,
        {
            "action": "unassigned",
            "task": {
                "id": updated_task.id,
                "title": updated_task.title
            }
        }
    )
    
    return updated_task


@router.get("/statistics", response_model=dict)
async def get_task_statistics(
    project_id: Optional[int] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get task statistics"""
    # Regular users can only see their own stats
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    stats = TaskService.get_task_statistics(db, project_id=project_id, user_id=user_id)
    return stats
