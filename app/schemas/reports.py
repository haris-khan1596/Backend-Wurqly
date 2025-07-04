from datetime import datetime, date
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class ReportFilter(BaseModel):
    """Base filter for reports"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_ids: Optional[List[int]] = None
    project_ids: Optional[List[int]] = None
    task_ids: Optional[List[int]] = None


class TimeReportEntry(BaseModel):
    """Individual entry in time report"""
    user_id: int
    user_name: str
    project_id: int
    project_name: str
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    date: date
    total_duration: int  # in seconds
    billable_duration: int  # in seconds
    entries_count: int
    hourly_rate: Optional[int] = None  # in cents
    total_earnings: Optional[int] = None  # in cents


class TimeReport(BaseModel):
    """Time tracking report"""
    report_period: ReportFilter
    entries: List[TimeReportEntry]
    summary: Dict[str, Any]


class ProductivityReportEntry(BaseModel):
    """Individual entry in productivity report"""
    user_id: int
    user_name: str
    date: date
    total_time: int  # in seconds
    productive_time: int  # in seconds
    productivity_percentage: float
    keyboard_strokes: int
    mouse_clicks: int
    screenshots_count: int
    apps_used: int
    top_applications: List[Dict[str, Any]]


class ProductivityReport(BaseModel):
    """Productivity report"""
    report_period: ReportFilter
    entries: List[ProductivityReportEntry]
    summary: Dict[str, Any]


class ProjectReportEntry(BaseModel):
    """Individual entry in project report"""
    project_id: int
    project_name: str
    total_time: int  # in seconds
    billable_time: int  # in seconds
    total_earnings: Optional[int] = None  # in cents
    tasks_count: int
    completed_tasks: int
    team_members: int
    budget_used_percentage: Optional[float] = None


class ProjectReport(BaseModel):
    """Project report"""
    report_period: ReportFilter
    entries: List[ProjectReportEntry]
    summary: Dict[str, Any]


class TeamMemberSummary(BaseModel):
    """Team member summary for reports"""
    user_id: int
    user_name: str
    total_hours: float
    productive_hours: float
    productivity_percentage: float
    total_earnings: Optional[int] = None  # in cents


class DailyTimeEntry(BaseModel):
    """Daily time entry for calendar view"""
    date: date
    total_duration: int  # in seconds
    billable_duration: int  # in seconds
    projects_count: int
    productivity_score: Optional[float] = None


class WeeklyTimeReport(BaseModel):
    """Weekly time report"""
    week_start: date
    week_end: date
    user_id: int
    user_name: str
    daily_entries: List[DailyTimeEntry]
    weekly_total: int  # in seconds
    weekly_billable: int  # in seconds
    weekly_productivity: Optional[float] = None


class AppUsageEntry(BaseModel):
    """Application usage entry"""
    application_name: str
    total_time: int  # in seconds
    percentage: float
    productivity_score: Optional[float] = None


class AppUsageReport(BaseModel):
    """Application usage report"""
    report_period: ReportFilter
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    applications: List[AppUsageEntry]
    most_productive_app: Optional[str] = None
    least_productive_app: Optional[str] = None
