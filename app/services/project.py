from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate, ProjectMemberUpdate


class ProjectService:
    @staticmethod
    def get_project(db: Session, project_id: int) -> Optional[Project]:
        """Get project by ID"""
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def get_project_with_details(db: Session, project_id: int) -> Optional[Project]:
        """Get project by ID with all related data"""
        return (
            db.query(Project)
            .options(
                joinedload(Project.owner),
                joinedload(Project.tasks),
                joinedload(Project.project_members).joinedload(ProjectMember.user),
                joinedload(Project.time_entries)
            )
            .filter(Project.id == project_id)
            .first()
        )

    @staticmethod
    def get_projects(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        owner_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Project]:
        """Get all projects with optional filtering"""
        query = db.query(Project)
        
        if owner_id:
            query = query.filter(Project.owner_id == owner_id)
        if status:
            query = query.filter(Project.status == status)
            
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_user_projects(db: Session, user_id: int, include_owned: bool = True, include_member: bool = True) -> List[Project]:
        """Get all projects where user is owner or member"""
        projects = []
        
        if include_owned:
            owned_projects = db.query(Project).filter(Project.owner_id == user_id).all()
            projects.extend(owned_projects)
        
        if include_member:
            member_projects = (
                db.query(Project)
                .join(ProjectMember)
                .filter(
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_active == True
                )
                .all()
            )
            # Avoid duplicates if user owns and is member
            project_ids = {p.id for p in projects}
            for project in member_projects:
                if project.id not in project_ids:
                    projects.append(project)
        
        return projects

    @staticmethod
    def create_project(db: Session, project: ProjectCreate, owner_id: int) -> Project:
        """Create new project"""
        db_project = Project(
            **project.model_dump(),
            owner_id=owner_id
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project

    @staticmethod
    def update_project(db: Session, project_id: int, project_update: ProjectUpdate) -> Optional[Project]:
        """Update project"""
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if not db_project:
            return None

        update_data = project_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_project, field, value)

        db.commit()
        db.refresh(db_project)
        return db_project

    @staticmethod
    def delete_project(db: Session, project_id: int) -> bool:
        """Delete project"""
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if not db_project:
            return False

        db.delete(db_project)
        db.commit()
        return True

    @staticmethod
    def add_project_member(
        db: Session, 
        project_id: int, 
        member_data: ProjectMemberCreate, 
        added_by_id: int
    ) -> Optional[ProjectMember]:
        """Add member to project"""
        # Check if member already exists
        existing_member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == member_data.user_id
            )
            .first()
        )
        
        if existing_member:
            # Reactivate if inactive
            if not existing_member.is_active:
                existing_member.is_active = True
                existing_member.role = member_data.role
                existing_member.hourly_rate = member_data.hourly_rate
                db.commit()
                db.refresh(existing_member)
            return existing_member

        db_member = ProjectMember(
            **member_data.model_dump(),
            project_id=project_id,
            added_by_id=added_by_id
        )
        db.add(db_member)
        db.commit()
        db.refresh(db_member)
        return db_member

    @staticmethod
    def update_project_member(
        db: Session, 
        project_id: int, 
        user_id: int, 
        member_update: ProjectMemberUpdate
    ) -> Optional[ProjectMember]:
        """Update project member"""
        db_member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
            .first()
        )
        
        if not db_member:
            return None

        update_data = member_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_member, field, value)

        db.commit()
        db.refresh(db_member)
        return db_member

    @staticmethod
    def remove_project_member(db: Session, project_id: int, user_id: int) -> bool:
        """Remove member from project"""
        db_member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
            .first()
        )
        
        if not db_member:
            return False

        db.delete(db_member)
        db.commit()
        return True

    @staticmethod
    def get_project_members(db: Session, project_id: int) -> List[ProjectMember]:
        """Get all project members"""
        return (
            db.query(ProjectMember)
            .options(joinedload(ProjectMember.user))
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.is_active == True
            )
            .all()
        )

    @staticmethod
    def is_project_member(db: Session, project_id: int, user_id: int) -> bool:
        """Check if user is a member of the project"""
        member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.is_active == True
            )
            .first()
        )
        return member is not None

    @staticmethod
    def is_project_owner(db: Session, project_id: int, user_id: int) -> bool:
        """Check if user is the owner of the project"""
        project = db.query(Project).filter(Project.id == project_id).first()
        return project and project.owner_id == user_id
