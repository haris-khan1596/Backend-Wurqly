from datetime import datetime
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload

from app.models.screenshot import Screenshot, ScreenshotStatus
from app.schemas.screenshot import ScreenshotCreate, ScreenshotUpdate, ScreenshotUpload
from app.services.storage import screenshot_storage


class ScreenshotService:
    @staticmethod
    def get_screenshot(db: Session, screenshot_id: int) -> Optional[Screenshot]:
        """Get screenshot by ID"""
        return db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()

    @staticmethod
    def get_screenshot_with_details(db: Session, screenshot_id: int) -> Optional[Screenshot]:
        """Get screenshot by ID with all related data"""
        return (
            db.query(Screenshot)
            .options(
                joinedload(Screenshot.user),
                joinedload(Screenshot.time_entry)
            )
            .filter(Screenshot.id == screenshot_id)
            .first()
        )

    @staticmethod
    def get_screenshots(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[int] = None,
        time_entry_id: Optional[int] = None,
        status: Optional[ScreenshotStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        is_blurred: Optional[bool] = None
    ) -> List[Screenshot]:
        """Get screenshots with optional filtering"""
        query = db.query(Screenshot)
        
        if user_id:
            query = query.filter(Screenshot.user_id == user_id)
        if time_entry_id:
            query = query.filter(Screenshot.time_entry_id == time_entry_id)
        if status:
            query = query.filter(Screenshot.status == status)
        if start_date:
            query = query.filter(Screenshot.captured_at >= start_date)
        if end_date:
            query = query.filter(Screenshot.captured_at <= end_date)
        if is_blurred is not None:
            query = query.filter(Screenshot.is_blurred == is_blurred)
            
        return query.order_by(Screenshot.captured_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_screenshots(
        db: Session, 
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Screenshot]:
        """Get all screenshots for a specific user"""
        query = db.query(Screenshot).filter(Screenshot.user_id == user_id)
        
        if start_date:
            query = query.filter(Screenshot.captured_at >= start_date)
        if end_date:
            query = query.filter(Screenshot.captured_at <= end_date)
        
        return query.order_by(Screenshot.captured_at.desc()).all()

    @staticmethod
    async def upload_screenshot(
        db: Session, 
        file: UploadFile, 
        user_id: int, 
        upload_data: ScreenshotUpload
    ) -> Screenshot:
        """Upload and save screenshot file"""
        # Read file content
        file_content = await file.read()
        
        # Get capture time (use current time if not provided)
        captured_at = upload_data.captured_at or datetime.utcnow()
        
        # Save file using storage service
        file_path, thumbnail_path, metadata = await screenshot_storage.save_screenshot(
            image_data=file_content,
            user_id=user_id,
            blur_level=upload_data.blur_level,
            create_thumbnail=True
        )
        
        # Create database record
        db_screenshot = Screenshot(
            filename=file.filename or f"screenshot_{int(captured_at.timestamp())}.png",
            file_path=file_path,
            file_size=metadata["file_size"],
            width=metadata["width"],
            height=metadata["height"],
            is_blurred=upload_data.is_blurred or metadata["is_blurred"],
            blur_level=upload_data.blur_level,
            status=ScreenshotStatus.UPLOADED,
            thumbnail_path=thumbnail_path,
            captured_at=captured_at,
            user_id=user_id,
            time_entry_id=upload_data.time_entry_id
        )
        
        db.add(db_screenshot)
        db.commit()
        db.refresh(db_screenshot)
        return db_screenshot

    @staticmethod
    def create_screenshot(db: Session, screenshot: ScreenshotCreate, user_id: int) -> Screenshot:
        """Create new screenshot record (for API-created screenshots)"""
        db_screenshot = Screenshot(
            **screenshot.model_dump(),
            user_id=user_id
        )
        db.add(db_screenshot)
        db.commit()
        db.refresh(db_screenshot)
        return db_screenshot

    @staticmethod
    def update_screenshot(db: Session, screenshot_id: int, screenshot_update: ScreenshotUpdate) -> Optional[Screenshot]:
        """Update screenshot"""
        db_screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
        if not db_screenshot:
            return None

        update_data = screenshot_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_screenshot, field, value)

        db.commit()
        db.refresh(db_screenshot)
        return db_screenshot

    @staticmethod
    async def delete_screenshot(db: Session, screenshot_id: int) -> bool:
        """Delete screenshot and associated files"""
        db_screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
        if not db_screenshot:
            return False

        # Delete files from storage
        await screenshot_storage.delete_screenshot(
            db_screenshot.file_path, 
            db_screenshot.thumbnail_path
        )

        # Delete database record
        db.delete(db_screenshot)
        db.commit()
        return True

    @staticmethod
    async def get_screenshot_file(db: Session, screenshot_id: int) -> Optional[bytes]:
        """Get screenshot file content"""
        db_screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
        if not db_screenshot:
            return None

        try:
            return await screenshot_storage.get_screenshot(db_screenshot.file_path)
        except FileNotFoundError:
            return None

    @staticmethod
    async def get_screenshot_url(db: Session, screenshot_id: int, expires_in: int = 3600) -> Optional[str]:
        """Get URL for accessing screenshot"""
        db_screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
        if not db_screenshot:
            return None

        try:
            return await screenshot_storage.get_screenshot_url(db_screenshot.file_path, expires_in)
        except Exception:
            return None

    @staticmethod
    async def get_thumbnail_url(db: Session, screenshot_id: int, expires_in: int = 3600) -> Optional[str]:
        """Get URL for accessing screenshot thumbnail"""
        db_screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
        if not db_screenshot or not db_screenshot.thumbnail_path:
            return None

        try:
            return await screenshot_storage.get_screenshot_url(db_screenshot.thumbnail_path, expires_in)
        except Exception:
            return None

    @staticmethod
    def get_screenshot_statistics(
        db: Session, 
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get screenshot statistics"""
        query = db.query(Screenshot)
        
        if user_id:
            query = query.filter(Screenshot.user_id == user_id)
        if start_date:
            query = query.filter(Screenshot.captured_at >= start_date)
        if end_date:
            query = query.filter(Screenshot.captured_at <= end_date)
        
        screenshots = query.all()
        
        if not screenshots:
            return {
                "total_screenshots": 0,
                "blurred_screenshots": 0,
                "blur_percentage": 0.0,
                "total_file_size": 0,
                "average_file_size": 0,
                "status_breakdown": {}
            }
        
        blurred_count = len([s for s in screenshots if s.is_blurred])
        total_file_size = sum(s.file_size or 0 for s in screenshots)
        
        # Status breakdown
        status_breakdown = {}
        for screenshot in screenshots:
            status = screenshot.status.value
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        return {
            "total_screenshots": len(screenshots),
            "blurred_screenshots": blurred_count,
            "blur_percentage": round((blurred_count / len(screenshots)) * 100, 2),
            "total_file_size": total_file_size,
            "average_file_size": round(total_file_size / len(screenshots), 2) if screenshots else 0,
            "status_breakdown": status_breakdown
        }

    @staticmethod
    def get_screenshots_by_time_entry(db: Session, time_entry_id: int) -> List[Screenshot]:
        """Get all screenshots for a specific time entry"""
        return (
            db.query(Screenshot)
            .filter(Screenshot.time_entry_id == time_entry_id)
            .order_by(Screenshot.captured_at.asc())
            .all()
        )

    @staticmethod
    async def process_pending_screenshots(db: Session, limit: int = 50) -> int:
        """Process pending screenshots (for background tasks)"""
        pending_screenshots = (
            db.query(Screenshot)
            .filter(Screenshot.status == ScreenshotStatus.PENDING)
            .limit(limit)
            .all()
        )
        
        processed_count = 0
        
        for screenshot in pending_screenshots:
            try:
                # Here you could add additional processing like:
                # - Image compression
                # - Thumbnail generation
                # - Content analysis
                # - OCR processing
                
                screenshot.status = ScreenshotStatus.UPLOADED
                processed_count += 1
                
            except Exception as e:
                screenshot.status = ScreenshotStatus.FAILED
                # Log error here
                continue
        
        db.commit()
        return processed_count
