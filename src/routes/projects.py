"""Project CRUD and membership routes for Phase 7.

Implements campaigns targeting one of the five trained priority pathogens.
Membership is many-to-many via ProjectMember.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import get_current_user
import config as C
from db import get_db
from models_db import Project, ProjectMember, Run, Scientist
from schemas import ProjectCreate, ProjectMemberAdd, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_out(db: Session, project: Project) -> ProjectOut:
    """Helper to compute run and member counts for a project."""
    n_runs = db.scalar(
        select(func.count(Run.id)).where(Run.project_id == project.id)
    ) or 0
    n_members = db.scalar(
        select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project.id)
    ) or 0

    return ProjectOut(
        id=project.id,
        lab_id=project.lab_id,
        name=project.name,
        target_species=project.target_species,
        status=project.status,
        created_by=project.created_by,
        is_seeded=project.is_seeded,
        created_at=project.created_at,
        n_runs=n_runs,
        n_members=n_members,
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    current_user: Scientist = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all projects within the authenticated scientist's lab."""
    stmt = (
        select(Project)
        .where(Project.lab_id == current_user.lab_id)
        .order_by(Project.created_at.desc())
    )
    projects = db.execute(stmt).scalars().all()
    return [_project_out(db, p) for p in projects]


@router.get("/mine", response_model=list[ProjectOut])
def list_my_projects(
    current_user: Scientist = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists projects where the current scientist is an assigned member or creator."""
    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.scientist_id == current_user.id
    )
    stmt = (
        select(Project)
        .where(
            Project.lab_id == current_user.lab_id,
            (Project.id.in_(member_project_ids)) | (Project.created_by == current_user.id),
        )
        .order_by(Project.created_at.desc())
    )
    projects = db.execute(stmt).scalars().all()
    return [_project_out(db, p) for p in projects]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    current_user: Scientist = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new campaign project targeted at exactly one trained priority pathogen."""
    if body.target_species not in C.PRIORITY_SPECIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid target_species '{body.target_species}'. Must be one of: "
                f"{', '.join(C.PRIORITY_SPECIES)}"
            ),
        )

    project = Project(
        lab_id=current_user.lab_id,
        name=body.name.strip(),
        target_species=body.target_species,
        status=body.status,
        created_by=current_user.id,
        is_seeded=False,
    )
    db.add(project)
    db.flush()

    # Automatically add the creator as lead member
    member = ProjectMember(
        project_id=project.id,
        scientist_id=current_user.id,
        role="lead",
    )
    db.add(member)
    db.commit()
    db.refresh(project)

    return _project_out(db, project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    current_user: Scientist = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves a single project by ID."""
    project = db.get(Project, project_id)
    if project is None or project.lab_id != current_user.lab_id:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return _project_out(db, project)


@router.post("/{project_id}/members", status_code=status.HTTP_200_OK)
def add_project_member(
    project_id: int,
    body: ProjectMemberAdd,
    current_user: Scientist = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adds a scientist as a member of this project."""
    project = db.get(Project, project_id)
    if project is None or project.lab_id != current_user.lab_id:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    target_scientist = db.get(Scientist, body.scientist_id)
    if target_scientist is None or target_scientist.lab_id != current_user.lab_id:
        raise HTTPException(status_code=400, detail="Scientist not found in this lab")

    existing = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.scientist_id == body.scientist_id,
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.role = body.role
    else:
        member = ProjectMember(
            project_id=project_id,
            scientist_id=body.scientist_id,
            role=body.role,
        )
        db.add(member)

    db.commit()
    return {"message": "Member added successfully", "project_id": project_id, "scientist_id": body.scientist_id}


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: int,
    current_user: Scientist = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Destructive delete: only project creators or lead scientists can delete a project."""
    project = db.get(Project, project_id)
    if project is None or project.lab_id != current_user.lab_id:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Check destructive role permission
    is_creator = project.created_by == current_user.id
    is_lab_lead = current_user.role == "lead"
    if not (is_creator or is_lab_lead):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project creator or a lab lead can delete this project",
        )

    db.delete(project)
    db.commit()
    return {"deleted": project_id}
