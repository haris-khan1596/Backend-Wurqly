from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User as UserModel
from app.models.screenshot import ScreenshotStatus
from app.schemas.screenshot import (
    Screenshot, ScreenshotCreate, ScreenshotUpdate, ScreenshotWithDetails,
    ScreenshotUpload, ScreenshotResponse
)
from app.services.screenshot import ScreenshotService
from app.services.websocket import websocket_service

router = APIRouter()


@router.get("/", response_model=List[Screenshot])
async def read_screenshots(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    time_entry_id: Optional[int] = None,
    status: Optional[ScreenshotStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_blurred: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get screenshots with optional filtering"""
    # Regular users can only see their own screenshots
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    screenshots = ScreenshotService.get_screenshots(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        time_entry_id=time_entry_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        is_blurred=is_blurred
    )
    return screenshots


@router.get("/my", response_model=List[Screenshot])
async def read_my_screenshots(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get current user's screenshots"""
    screenshots = ScreenshotService.get_user_screenshots(
        db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )
    return screenshots[skip:skip + limit]


@router.get("/{screenshot_id}", response_model=ScreenshotWithDetails)
async def read_screenshot(
    screenshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get screenshot by ID with details"""
    screenshot = ScreenshotService.get_screenshot_with_details(db, screenshot_id=screenshot_id)
    if screenshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        screenshot.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return screenshot


@router.post("/upload", response_model=ScreenshotResponse)
async def upload_screenshot(
    file: UploadFile = File(...),
    time_entry_id: Optional[int] = Form(None),
    is_blurred: bool = Form(False),
    blur_level: int = Form(0),
    captured_at: Optional[datetime] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Upload a screenshot file"""
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Create upload data
    upload_data = ScreenshotUpload(
        time_entry_id=time_entry_id,
        is_blurred=is_blurred,
        blur_level=blur_level,
        captured_at=captured_at
    )
    
    try:
        screenshot = await ScreenshotService.upload_screenshot(
            db=db,
            file=file,
            user_id=current_user.id,
            upload_data=upload_data
        )
        
        # Send WebSocket notification
        await websocket_service.notify_screenshot_taken(
            current_user.id,
            {
                "id": screenshot.id,
                "filename": screenshot.filename,
                "captured_at": screenshot.captured_at.isoformat(),
                "is_blurred": screenshot.is_blurred
            }
        )
        
        return ScreenshotResponse(
            id=screenshot.id,
            filename=screenshot.filename,
            file_path=screenshot.file_path,
            thumbnail_path=screenshot.thumbnail_path,
            status=screenshot.status,
            captured_at=screenshot.captured_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload screenshot: {str(e)}"
        )


@router.post("/", response_model=Screenshot)
async def create_screenshot(
    screenshot: ScreenshotCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create new screenshot record (for API-created screenshots)"""
    created_screenshot = ScreenshotService.create_screenshot(
        db=db, 
        screenshot=screenshot, 
        user_id=current_user.id
    )
    
    return created_screenshot


@router.put("/{screenshot_id}", response_model=Screenshot)
async def update_screenshot(
    screenshot_id: int,
    screenshot_update: ScreenshotUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update screenshot"""
    # Check if screenshot exists
    screenshot = ScreenshotService.get_screenshot(db, screenshot_id=screenshot_id)
    if screenshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        screenshot.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    updated_screenshot = ScreenshotService.update_screenshot(
        db, screenshot_id=screenshot_id, screenshot_update=screenshot_update
    )
    if updated_screenshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    return updated_screenshot


@router.delete("/{screenshot_id}")
async def delete_screenshot(
    screenshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Delete screenshot and associated files"""
    # Check if screenshot exists
    screenshot = ScreenshotService.get_screenshot(db, screenshot_id=screenshot_id)
    if screenshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    # Check permissions (only owner or admins can delete)
    if (current_user.role.value != "admin" and 
        not current_user.is_superuser and
        screenshot.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    success = await ScreenshotService.delete_screenshot(db, screenshot_id=screenshot_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    return {"message": "Screenshot deleted successfully"}


@router.get("/{screenshot_id}/file")
async def get_screenshot_file(
    screenshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Download screenshot file"""
    # Check if screenshot exists
    screenshot = ScreenshotService.get_screenshot(db, screenshot_id=screenshot_id)
    if screenshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        screenshot.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get file content
    file_content = await ScreenshotService.get_screenshot_file(db, screenshot_id)
    if file_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot file not found"
        )
    
    # Return file as streaming response
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={screenshot.filename}"}
    )


@router.get("/{screenshot_id}/url")
async def get_screenshot_url(
    screenshot_id: int,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get URL for accessing screenshot"""
    # Check if screenshot exists
    screenshot = ScreenshotService.get_screenshot(db, screenshot_id=screenshot_id)
    if screenshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        screenshot.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    url = await ScreenshotService.get_screenshot_url(db, screenshot_id, expires_in)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot file not found"
        )
    
    return {"url": url, "expires_in": expires_in}


@router.get("/{screenshot_id}/thumbnail")
async def get_screenshot_thumbnail_url(
    screenshot_id: int,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get URL for accessing screenshot thumbnail"""
    # Check if screenshot exists
    screenshot = ScreenshotService.get_screenshot(db, screenshot_id=screenshot_id)
    if screenshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    # Check permissions
    if (current_user.role.value not in ["manager", "admin"] and 
        not current_user.is_superuser and
        screenshot.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    url = await ScreenshotService.get_thumbnail_url(db, screenshot_id, expires_in)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot thumbnail not found"
        )
    
    return {"url": url, "expires_in": expires_in}


@router.get("/statistics", response_model=dict)
async def get_screenshot_statistics(
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get screenshot statistics"""
    # Regular users can only see their own statistics
    if current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        user_id = current_user.id
    
    stats = ScreenshotService.get_screenshot_statistics(
        db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    return stats


@router.get("/time-entry/{time_entry_id}", response_model=List[Screenshot])
async def get_screenshots_by_time_entry(
    time_entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get all screenshots for a specific time entry"""
    screenshots = ScreenshotService.get_screenshots_by_time_entry(db, time_entry_id)
    
    # Check permissions - user can only see screenshots from their own time entries
    if screenshots and current_user.role.value not in ["manager", "admin"] and not current_user.is_superuser:
        # Check if any screenshot belongs to the current user
        if screenshots[0].user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    return screenshots
