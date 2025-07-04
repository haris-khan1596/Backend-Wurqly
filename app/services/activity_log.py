from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.models.activity_log import ActivityLog
from app.schemas.activity_log import ActivityLogCreate, ActivityLogUpdate, ActivityLogBatch


class ActivityLogService:
    @staticmethod
    def get_activity_log(db: Session, activity_log_id: int) -> Optional[ActivityLog]:
        """Get activity log by ID"""
        return db.query(ActivityLog).filter(ActivityLog.id == activity_log_id).first()

    @staticmethod
    def get_activity_logs(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[int] = None,
        time_entry_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        is_productive: Optional[bool] = None
    ) -> List[ActivityLog]:
        """Get activity logs with optional filtering"""
        query = db.query(ActivityLog)
        
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if time_entry_id:
            query = query.filter(ActivityLog.time_entry_id == time_entry_id)
        if start_date:
            query = query.filter(ActivityLog.timestamp >= start_date)
        if end_date:
            query = query.filter(ActivityLog.timestamp <= end_date)
        if is_productive is not None:
            query = query.filter(ActivityLog.is_productive == is_productive)
            
        return query.order_by(ActivityLog.timestamp.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_activity_log(db: Session, activity_log: ActivityLogCreate, user_id: int) -> ActivityLog:
        """Create new activity log"""
        db_activity_log = ActivityLog(
            **activity_log.model_dump(),
            user_id=user_id
        )
        db.add(db_activity_log)
        db.commit()
        db.refresh(db_activity_log)
        return db_activity_log

    @staticmethod
    def create_activity_logs_batch(db: Session, batch: ActivityLogBatch, user_id: int) -> List[ActivityLog]:
        """Create multiple activity logs in batch"""
        db_activity_logs = []
        for activity_log_data in batch.activity_logs:
            db_activity_log = ActivityLog(
                **activity_log_data.model_dump(),
                user_id=user_id
            )
            db_activity_logs.append(db_activity_log)
        
        db.add_all(db_activity_logs)
        db.commit()
        
        for log in db_activity_logs:
            db.refresh(log)
        
        return db_activity_logs

    @staticmethod
    def update_activity_log(db: Session, activity_log_id: int, activity_log_update: ActivityLogUpdate) -> Optional[ActivityLog]:
        """Update activity log"""
        db_activity_log = db.query(ActivityLog).filter(ActivityLog.id == activity_log_id).first()
        if not db_activity_log:
            return None

        update_data = activity_log_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_activity_log, field, value)

        db.commit()
        db.refresh(db_activity_log)
        return db_activity_log

    @staticmethod
    def delete_activity_log(db: Session, activity_log_id: int) -> bool:
        """Delete activity log"""
        db_activity_log = db.query(ActivityLog).filter(ActivityLog.id == activity_log_id).first()
        if not db_activity_log:
            return False

        db.delete(db_activity_log)
        db.commit()
        return True

    @staticmethod
    def get_activity_summary(
        db: Session,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get activity summary statistics"""
        query = db.query(ActivityLog)
        
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if start_date:
            query = query.filter(ActivityLog.timestamp >= start_date)
        if end_date:
            query = query.filter(ActivityLog.timestamp <= end_date)
        
        logs = query.all()
        
        if not logs:
            return {
                "total_logs": 0,
                "total_keyboard_strokes": 0,
                "total_mouse_clicks": 0,
                "total_mouse_moves": 0,
                "total_scroll_events": 0,
                "average_productivity_score": 0.0,
                "productive_time_percentage": 0.0,
                "most_used_applications": []
            }
        
        total_keyboard_strokes = sum(log.keyboard_strokes for log in logs)
        total_mouse_clicks = sum(log.mouse_clicks for log in logs)
        total_mouse_moves = sum(log.mouse_moves for log in logs)
        total_scroll_events = sum(log.scroll_events for log in logs)
        
        productive_logs = [log for log in logs if log.is_productive]
        productive_time_percentage = (len(productive_logs) / len(logs)) * 100 if logs else 0
        
        productivity_scores = [log.productivity_score for log in logs if log.productivity_score is not None]
        average_productivity_score = sum(productivity_scores) / len(productivity_scores) if productivity_scores else 0.0
        
        # Most used applications
        app_usage = {}
        for log in logs:
            if log.active_application:
                app_usage[log.active_application] = app_usage.get(log.active_application, 0) + 1
        
        most_used_applications = [
            {"application": app, "count": count}
            for app, count in sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return {
            "total_logs": len(logs),
            "total_keyboard_strokes": total_keyboard_strokes,
            "total_mouse_clicks": total_mouse_clicks,
            "total_mouse_moves": total_mouse_moves,
            "total_scroll_events": total_scroll_events,
            "average_productivity_score": round(average_productivity_score, 2),
            "productive_time_percentage": round(productive_time_percentage, 2),
            "most_used_applications": most_used_applications
        }

    @staticmethod
    def get_hourly_activity(
        db: Session,
        user_id: int,
        date: datetime
    ) -> List[dict]:
        """Get hourly activity breakdown for a specific date"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.timestamp >= start_of_day,
                ActivityLog.timestamp <= end_of_day
            )
            .all()
        )
        
        hourly_data = {}
        for hour in range(24):
            hourly_data[hour] = {
                "hour": hour,
                "keyboard_strokes": 0,
                "mouse_clicks": 0,
                "mouse_moves": 0,
                "scroll_events": 0,
                "activity_count": 0,
                "productive_percentage": 0.0
            }
        
        for log in logs:
            hour = log.timestamp.hour
            hourly_data[hour]["keyboard_strokes"] += log.keyboard_strokes
            hourly_data[hour]["mouse_clicks"] += log.mouse_clicks
            hourly_data[hour]["mouse_moves"] += log.mouse_moves
            hourly_data[hour]["scroll_events"] += log.scroll_events
            hourly_data[hour]["activity_count"] += 1
        
        # Calculate productive percentage for each hour
        for hour in range(24):
            hour_logs = [log for log in logs if log.timestamp.hour == hour]
            if hour_logs:
                productive_logs = [log for log in hour_logs if log.is_productive]
                hourly_data[hour]["productive_percentage"] = (len(productive_logs) / len(hour_logs)) * 100
        
        return list(hourly_data.values())

    @staticmethod
    def get_application_usage(
        db: Session,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[dict]:
        """Get application usage statistics"""
        query = db.query(ActivityLog)
        
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if start_date:
            query = query.filter(ActivityLog.timestamp >= start_date)
        if end_date:
            query = query.filter(ActivityLog.timestamp <= end_date)
        
        logs = query.filter(ActivityLog.active_application.isnot(None)).all()
        
        app_stats = {}
        total_logs = len(logs)
        
        for log in logs:
            app = log.active_application
            if app not in app_stats:
                app_stats[app] = {
                    "application_name": app,
                    "total_time": 0,
                    "log_count": 0,
                    "productive_time": 0,
                    "productivity_scores": []
                }
            
            app_stats[app]["log_count"] += 1
            if log.is_productive:
                app_stats[app]["productive_time"] += 1
            if log.productivity_score is not None:
                app_stats[app]["productivity_scores"].append(log.productivity_score)
        
        # Calculate final statistics
        result = []
        for app, stats in app_stats.items():
            percentage = (stats["log_count"] / total_logs) * 100 if total_logs > 0 else 0
            productivity_score = (
                sum(stats["productivity_scores"]) / len(stats["productivity_scores"])
                if stats["productivity_scores"] else None
            )
            
            result.append({
                "application_name": app,
                "usage_count": stats["log_count"],
                "percentage": round(percentage, 2),
                "productive_percentage": round((stats["productive_time"] / stats["log_count"]) * 100, 2) if stats["log_count"] > 0 else 0,
                "average_productivity_score": round(productivity_score, 2) if productivity_score else None
            })
        
        return sorted(result, key=lambda x: x["usage_count"], reverse=True)[:limit]
