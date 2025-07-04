from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User as UserModel
from app.schemas.activity_log import (
    ActivityLog, ActivityLogCreate, ActivityLogUpdate, ActivityLogWithDetails,
    ActivityLogBatch, ActivityLogSummary
)
from app.services.activity_log import ActivityLogService
from app.services.websocket import websocket_service

router = APIRouter()


@router.get("/", response_model=List[ActivityLog])
async def read_activity_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    time_entry_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_productive: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get activity logs with optional filtering"""
    # Regular users can only see their own activity logs
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    activity_logs = ActivityLogService.get_activity_logs(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        time_entry_id=time_entry_id,
        start_date=start_date,
        end_date=end_date,
        is_productive=is_productive
    )
    return activity_logs


@router.get("/{activity_log_id}", response_model=ActivityLog)
async def read_activity_log(
    activity_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get activity log by ID"""
    activity_log = ActivityLogService.get_activity_log(db, activity_log_id=activity_log_id)
    if activity_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity log not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        activity_log.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return activity_log


@router.post("/", response_model=ActivityLog)
async def create_activity_log(
    activity_log: ActivityLogCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create new activity log"""
    created_activity_log = ActivityLogService.create_activity_log(
        db=db, 
        activity_log=activity_log, 
        user_id=current_user.id
    )
    
    # Send WebSocket notification
    await websocket_service.notify_activity_update(
        current_user.id,
        {
            "id": created_activity_log.id,
            "timestamp": created_activity_log.timestamp.isoformat(),
            "is_productive": created_activity_log.is_productive,
            "productivity_score": created_activity_log.productivity_score
        }
    )
    
    return created_activity_log


@router.post("/batch", response_model=List[ActivityLog])
async def create_activity_logs_batch(
    batch: ActivityLogBatch,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create multiple activity logs in batch"""
    created_logs = ActivityLogService.create_activity_logs_batch(
        db=db, 
        batch=batch, 
        user_id=current_user.id
    )
    
    # Send WebSocket notification for batch update
    await websocket_service.notify_activity_update(
        current_user.id,
        {
            "batch_count": len(created_logs),
            "timestamp": datetime.utcnow().isoformat(),
            "type": "batch_update"
        }
    )
    
    return created_logs


@router.put("/{activity_log_id}", response_model=ActivityLog)
async def update_activity_log(
    activity_log_id: int,
    activity_log_update: ActivityLogUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update activity log"""
    # Check if activity log exists
    activity_log = ActivityLogService.get_activity_log(db, activity_log_id=activity_log_id)
    if activity_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity log not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        activity_log.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    updated_activity_log = ActivityLogService.update_activity_log(
        db, activity_log_id=activity_log_id, activity_log_update=activity_log_update
    )
    if updated_activity_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity log not found"
        )
    
    return updated_activity_log


@router.delete("/{activity_log_id}")
async def delete_activity_log(
    activity_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Delete activity log"""
    # Check if activity log exists
    activity_log = ActivityLogService.get_activity_log(db, activity_log_id=activity_log_id)
    if activity_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity log not found"
        )
    
    # Check permissions (only owner or admins can delete)
    if (current_user.role.value != "admin" and 
        not current_user.is_superuser and
        activity_log.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    success = ActivityLogService.delete_activity_log(db, activity_log_id=activity_log_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity log not found"
        )
    
    return {"message": "Activity log deleted successfully"}


@router.get("/summary", response_model=dict)
async def get_activity_summary(
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get activity summary statistics"""
    # Regular users can only see their own summary
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    summary = ActivityLogService.get_activity_summary(
        db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    return summary


@router.get("/hourly/{date}", response_model=List[dict])
async def get_hourly_activity(
    date: datetime,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get hourly activity breakdown for a specific date"""
    # Regular users can only see their own data
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    elif user_id is None:
        user_id = current_user.id
    
    hourly_data = ActivityLogService.get_hourly_activity(
        db,
        user_id=user_id,
        date=date
    )
    return hourly_data


@router.get("/applications", response_model=List[dict])
async def get_application_usage(
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get application usage statistics"""
    # Regular users can only see their own data
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    app_usage = ActivityLogService.get_application_usage(
        db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return app_usage
