from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User as UserModel
from app.models.time_entry import TimeEntryStatus
from app.schemas.time_entry import (
    TimeEntry, TimeEntryCreate, TimeEntryUpdate, TimeEntryWithDetails,
    TimeEntryStart, TimeEntryStop
)
from app.services.time_entry import TimeEntryService
from app.services.websocket import websocket_service

router = APIRouter()


@router.get("/", response_model=List[TimeEntry])
async def read_time_entries(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    status: Optional[TimeEntryStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get time entries with optional filtering"""
    # Regular users can only see their own time entries
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    time_entries = TimeEntryService.get_time_entries(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
        status=status,
        start_date=start_date,
        end_date=end_date
    )
    return time_entries


@router.get("/my", response_model=List[TimeEntry])
async def read_my_time_entries(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get current user's time entries"""
    time_entries = TimeEntryService.get_user_time_entries(
        db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )
    return time_entries[skip:skip + limit]


@router.get("/active", response_model=Optional[TimeEntry])
async def get_active_time_entry(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get currently active time entry for the user"""
    active_entry = TimeEntryService.get_active_time_entry(db, current_user.id)
    return active_entry


@router.get("/{time_entry_id}", response_model=TimeEntryWithDetails)
async def read_time_entry(
    time_entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get time entry by ID with details"""
    time_entry = TimeEntryService.get_time_entry_with_details(db, time_entry_id=time_entry_id)
    if time_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        time_entry.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return time_entry


@router.post("/", response_model=TimeEntry)
async def create_time_entry(
    time_entry: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create new time entry"""
    created_time_entry = TimeEntryService.create_time_entry(
        db=db, 
        time_entry=time_entry, 
        user_id=current_user.id
    )
    
    # Send WebSocket notification
    await websocket_service.notify_time_entry_started(
        current_user.id,
        {
            "id": created_time_entry.id,
            "project_id": created_time_entry.project_id,
            "task_id": created_time_entry.task_id,
            "start_time": created_time_entry.start_time.isoformat()
        }
    )
    
    return created_time_entry


@router.post("/start", response_model=TimeEntry)
async def start_timer(
    timer_data: TimeEntryStart,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Start a new timer"""
    time_entry = TimeEntryService.start_timer(
        db=db, 
        timer_data=timer_data, 
        user_id=current_user.id
    )
    
    if time_entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to start timer"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_time_entry_started(
        current_user.id,
        {
            "id": time_entry.id,
            "project_id": time_entry.project_id,
            "task_id": time_entry.task_id,
            "start_time": time_entry.start_time.isoformat()
        }
    )
    
    return time_entry


@router.post("/stop", response_model=TimeEntry)
async def stop_timer(
    stop_data: Optional[TimeEntryStop] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Stop the currently running timer"""
    # Get active time entry
    active_entry = TimeEntryService.get_active_time_entry(db, current_user.id)
    if active_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active timer found"
        )
    
    stopped_entry = TimeEntryService.stop_timer(
        db=db, 
        time_entry_id=active_entry.id, 
        stop_data=stop_data
    )
    
    if stopped_entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to stop timer"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_time_entry_stopped(
        current_user.id,
        {
            "id": stopped_entry.id,
            "project_id": stopped_entry.project_id,
            "task_id": stopped_entry.task_id,
            "end_time": stopped_entry.end_time.isoformat() if stopped_entry.end_time else None,
            "duration": stopped_entry.duration
        }
    )
    
    return stopped_entry


@router.post("/{time_entry_id}/stop", response_model=TimeEntry)
async def stop_specific_timer(
    time_entry_id: int,
    stop_data: Optional[TimeEntryStop] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Stop a specific timer by ID"""
    # Check if time entry exists and belongs to user
    time_entry = TimeEntryService.get_time_entry(db, time_entry_id)
    if time_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        time_entry.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    stopped_entry = TimeEntryService.stop_timer(
        db=db, 
        time_entry_id=time_entry_id, 
        stop_data=stop_data
    )
    
    if stopped_entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to stop timer"
        )
    
    # Send WebSocket notification
    await websocket_service.notify_time_entry_stopped(
        stopped_entry.user_id,
        {
            "id": stopped_entry.id,
            "project_id": stopped_entry.project_id,
            "task_id": stopped_entry.task_id,
            "end_time": stopped_entry.end_time.isoformat() if stopped_entry.end_time else None,
            "duration": stopped_entry.duration
        }
    )
    
    return stopped_entry


@router.put("/{time_entry_id}", response_model=TimeEntry)
async def update_time_entry(
    time_entry_id: int,
    time_entry_update: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update time entry"""
    # Check if time entry exists
    time_entry = TimeEntryService.get_time_entry(db, time_entry_id=time_entry_id)
    if time_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        time_entry.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    updated_time_entry = TimeEntryService.update_time_entry(
        db, time_entry_id=time_entry_id, time_entry_update=time_entry_update
    )
    if updated_time_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    return updated_time_entry


@router.delete("/{time_entry_id}")
async def delete_time_entry(
    time_entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Delete time entry"""
    # Check if time entry exists
    time_entry = TimeEntryService.get_time_entry(db, time_entry_id=time_entry_id)
    if time_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    # Check permissions (only owner or admins can delete)
    if (current_user.role.value != "admin" and 
        not current_user.is_superuser and
        time_entry.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    success = TimeEntryService.delete_time_entry(db, time_entry_id=time_entry_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    return {"message": "Time entry deleted successfully"}


@router.get("/summary", response_model=dict)
async def get_time_summary(
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get time tracking summary"""
    # Regular users can only see their own summary
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    summary = TimeEntryService.get_time_summary(
        db,
        user_id=user_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date
    )
    return summary


@router.get("/earnings", response_model=dict)
async def get_earnings(
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Calculate earnings from time entries"""
    # Regular users can only see their own earnings
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    earnings = TimeEntryService.calculate_earnings(
        db,
        user_id=user_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date
    )
    return earnings
