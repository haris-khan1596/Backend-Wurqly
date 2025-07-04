from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    @staticmethod
    def get_task(db: Session, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_task_with_details(db: Session, task_id: int) -> Optional[Task]:
        """Get task by ID with all related data"""
        return (
            db.query(Task)
            .options(
                joinedload(Task.project),
                joinedload(Task.assignee),
                joinedload(Task.created_by),
                joinedload(Task.time_entries)
            )
            .filter(Task.id == task_id)
            .first()
        )

    @staticmethod
    def get_tasks(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        project_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Task]:
        """Get all tasks with optional filtering"""
        query = db.query(Task)
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
            
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_project_tasks(db: Session, project_id: int) -> List[Task]:
        """Get all tasks for a specific project"""
        return db.query(Task).filter(Task.project_id == project_id).all()

    @staticmethod
    def get_user_tasks(
        db: Session, 
        user_id: int, 
        include_assigned: bool = True, 
        include_created: bool = False
    ) -> List[Task]:
        """Get all tasks assigned to or created by user"""
        tasks = []
        
        if include_assigned:
            assigned_tasks = db.query(Task).filter(Task.assignee_id == user_id).all()
            tasks.extend(assigned_tasks)
        
        if include_created:
            created_tasks = db.query(Task).filter(Task.created_by_id == user_id).all()
            # Avoid duplicates if user created and is assigned
            task_ids = {t.id for t in tasks}
            for task in created_tasks:
                if task.id not in task_ids:
                    tasks.append(task)
        
        return tasks

    @staticmethod
    def create_task(db: Session, task: TaskCreate, created_by_id: int) -> Task:
        """Create new task"""
        db_task = Task(
            **task.model_dump(),
            created_by_id=created_by_id
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def update_task(db: Session, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
        """Update task"""
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if not db_task:
            return None

        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_task, field, value)

        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        """Delete task"""
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if not db_task:
            return False

        db.delete(db_task)
        db.commit()
        return True

    @staticmethod
    def assign_task(db: Session, task_id: int, assignee_id: int) -> Optional[Task]:
        """Assign task to a user"""
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if not db_task:
            return None

        db_task.assignee_id = assignee_id
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def unassign_task(db: Session, task_id: int) -> Optional[Task]:
        """Unassign task from current assignee"""
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if not db_task:
            return None

        db_task.assignee_id = None
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def get_task_statistics(db: Session, project_id: Optional[int] = None, user_id: Optional[int] = None) -> dict:
        """Get task statistics"""
        from app.models.task import TaskStatus
        
        query = db.query(Task)
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if user_id:
            query = query.filter(Task.assignee_id == user_id)
        
        tasks = query.all()
        
        stats = {
            "total": len(tasks),
            "todo": len([t for t in tasks if t.status == TaskStatus.TODO]),
            "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
            "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
            "archived": len([t for t in tasks if t.status == TaskStatus.ARCHIVED]),
        }
        
        if stats["total"] > 0:
            stats["completion_rate"] = round((stats["completed"] / stats["total"]) * 100, 2)
        else:
            stats["completion_rate"] = 0.0
        
        return stats
