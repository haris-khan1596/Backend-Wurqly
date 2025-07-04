from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.models.time_entry import TimeEntry, TimeEntryStatus
from app.schemas.time_entry import TimeEntryCreate, TimeEntryUpdate, TimeEntryStart, TimeEntryStop


class TimeEntryService:
    @staticmethod
    def get_time_entry(db: Session, time_entry_id: int) -> Optional[TimeEntry]:
        """Get time entry by ID"""
        return db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()

    @staticmethod
    def get_time_entry_with_details(db: Session, time_entry_id: int) -> Optional[TimeEntry]:
        """Get time entry by ID with all related data"""
        return (
            db.query(TimeEntry)
            .options(
                joinedload(TimeEntry.user),
                joinedload(TimeEntry.project),
                joinedload(TimeEntry.task),
                joinedload(TimeEntry.activity_logs),
                joinedload(TimeEntry.screenshots)
            )
            .filter(TimeEntry.id == time_entry_id)
            .first()
        )

    @staticmethod
    def get_time_entries(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        task_id: Optional[int] = None,
        status: Optional[TimeEntryStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TimeEntry]:
        """Get time entries with optional filtering"""
        query = db.query(TimeEntry)
        
        if user_id:
            query = query.filter(TimeEntry.user_id == user_id)
        if project_id:
            query = query.filter(TimeEntry.project_id == project_id)
        if task_id:
            query = query.filter(TimeEntry.task_id == task_id)
        if status:
            query = query.filter(TimeEntry.status == status)
        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)
        if end_date:
            query = query.filter(
                or_(
                    TimeEntry.end_time <= end_date,
                    and_(TimeEntry.end_time.is_(None), TimeEntry.start_time <= end_date)
                )
            )
            
        return query.order_by(TimeEntry.start_time.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_time_entries(
        db: Session, 
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TimeEntry]:
        """Get all time entries for a specific user"""
        query = db.query(TimeEntry).filter(TimeEntry.user_id == user_id)
        
        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)
        if end_date:
            query = query.filter(
                or_(
                    TimeEntry.end_time <= end_date,
                    and_(TimeEntry.end_time.is_(None), TimeEntry.start_time <= end_date)
                )
            )
        
        return query.order_by(TimeEntry.start_time.desc()).all()

    @staticmethod
    def get_active_time_entry(db: Session, user_id: int) -> Optional[TimeEntry]:
        """Get currently running time entry for user"""
        return (
            db.query(TimeEntry)
            .filter(
                TimeEntry.user_id == user_id,
                TimeEntry.status == TimeEntryStatus.RUNNING
            )
            .first()
        )

    @staticmethod
    def create_time_entry(db: Session, time_entry: TimeEntryCreate, user_id: int) -> TimeEntry:
        """Create new time entry"""
        db_time_entry = TimeEntry(
            **time_entry.model_dump(),
            user_id=user_id
        )
        db.add(db_time_entry)
        db.commit()
        db.refresh(db_time_entry)
        return db_time_entry

    @staticmethod
    def start_timer(db: Session, timer_data: TimeEntryStart, user_id: int) -> Optional[TimeEntry]:
        """Start a new timer (stop any existing running timer first)"""
        # Stop any running timer first
        active_entry = TimeEntryService.get_active_time_entry(db, user_id)
        if active_entry:
            TimeEntryService.stop_timer(db, active_entry.id)
        
        # Create new time entry
        start_time = datetime.now(timezone.utc)
        db_time_entry = TimeEntry(
            user_id=user_id,
            project_id=timer_data.project_id,
            task_id=timer_data.task_id,
            description=timer_data.description,
            start_time=start_time,
            status=TimeEntryStatus.RUNNING
        )
        db.add(db_time_entry)
        db.commit()
        db.refresh(db_time_entry)
        return db_time_entry

    @staticmethod
    def stop_timer(db: Session, time_entry_id: int, stop_data: Optional[TimeEntryStop] = None) -> Optional[TimeEntry]:
        """Stop a running timer"""
        db_time_entry = db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
        if not db_time_entry or db_time_entry.status != TimeEntryStatus.RUNNING:
            return None

        end_time = datetime.now(timezone.utc)
        duration = int((end_time - db_time_entry.start_time).total_seconds())

        db_time_entry.end_time = end_time
        db_time_entry.duration = duration
        db_time_entry.status = TimeEntryStatus.STOPPED
        
        if stop_data and stop_data.description:
            db_time_entry.description = stop_data.description

        db.commit()
        db.refresh(db_time_entry)
        return db_time_entry

    @staticmethod
    def update_time_entry(db: Session, time_entry_id: int, time_entry_update: TimeEntryUpdate) -> Optional[TimeEntry]:
        """Update time entry"""
        db_time_entry = db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
        if not db_time_entry:
            return None

        update_data = time_entry_update.model_dump(exclude_unset=True)
        
        # Recalculate duration if start_time or end_time changed
        if "start_time" in update_data or "end_time" in update_data:
            start_time = update_data.get("start_time", db_time_entry.start_time)
            end_time = update_data.get("end_time", db_time_entry.end_time)
            
            if start_time and end_time:
                duration = int((end_time - start_time).total_seconds())
                update_data["duration"] = duration

        for field, value in update_data.items():
            setattr(db_time_entry, field, value)

        db.commit()
        db.refresh(db_time_entry)
        return db_time_entry

    @staticmethod
    def delete_time_entry(db: Session, time_entry_id: int) -> bool:
        """Delete time entry"""
        db_time_entry = db.query(TimeEntry).filter(TimeEntry.id == time_entry_id).first()
        if not db_time_entry:
            return False

        db.delete(db_time_entry)
        db.commit()
        return True

    @staticmethod
    def get_time_summary(
        db: Session, 
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get time tracking summary statistics"""
        query = db.query(TimeEntry)
        
        if user_id:
            query = query.filter(TimeEntry.user_id == user_id)
        if project_id:
            query = query.filter(TimeEntry.project_id == project_id)
        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)
        if end_date:
            query = query.filter(
                or_(
                    TimeEntry.end_time <= end_date,
                    and_(TimeEntry.end_time.is_(None), TimeEntry.start_time <= end_date)
                )
            )
        
        # Only include completed entries for summary
        entries = query.filter(TimeEntry.status != TimeEntryStatus.RUNNING).all()
        
        total_duration = sum(entry.duration or 0 for entry in entries)
        billable_duration = sum(entry.duration or 0 for entry in entries if entry.is_billable)
        
        return {
            "total_entries": len(entries),
            "total_duration": total_duration,  # in seconds
            "billable_duration": billable_duration,  # in seconds
            "total_hours": round(total_duration / 3600, 2),
            "billable_hours": round(billable_duration / 3600, 2),
            "billable_percentage": round((billable_duration / total_duration * 100), 2) if total_duration > 0 else 0,
        }

    @staticmethod
    def calculate_earnings(
        db: Session,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Calculate earnings from time entries"""
        query = db.query(TimeEntry)
        
        if user_id:
            query = query.filter(TimeEntry.user_id == user_id)
        if project_id:
            query = query.filter(TimeEntry.project_id == project_id)
        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)
        if end_date:
            query = query.filter(
                or_(
                    TimeEntry.end_time <= end_date,
                    and_(TimeEntry.end_time.is_(None), TimeEntry.start_time <= end_date)
                )
            )
        
        entries = query.filter(
            TimeEntry.status != TimeEntryStatus.RUNNING,
            TimeEntry.is_billable == True
        ).all()
        
        total_earnings = 0
        for entry in entries:
            if entry.duration and entry.hourly_rate:
                hours = entry.duration / 3600
                earnings = int(hours * entry.hourly_rate)  # hourly_rate is in cents
                total_earnings += earnings
            elif entry.duration and entry.project and entry.project.hourly_rate:
                hours = entry.duration / 3600
                earnings = int(hours * entry.project.hourly_rate)  # hourly_rate is in cents
                total_earnings += earnings
        
        return {
            "total_earnings": total_earnings,  # in cents
            "billable_entries": len(entries),
            "currency": "USD"  # This could be configurable
        }
