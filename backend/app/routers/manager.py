from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Employee, PunchLog, Schedule, ScheduleGroup, ScheduleGroupAssignment, DtrRevision
from .auth import get_current_user

router = APIRouter(prefix="/api/manager", tags=["Manager & Scheduling"])

# Pydantic Schemas
class DtrRevisionAction(BaseModel):
    action: str  # APPROVED or REJECTED

class CreateRevisionRequest(BaseModel):
    punch_log_id: Optional[int] = None
    requested_punch_type: str
    requested_timestamp: datetime
    reason: str

class ScheduleGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    employee_ids: List[str] = []

class ShiftScheduleCreate(BaseModel):
    employee_id: Optional[str] = None
    group_id: Optional[int] = None
    day_of_week: int
    shift_start: str
    shift_end: str
    break_duration_mins: int = 60

# Helper to verify Manager or Admin role
def verify_manager_or_admin(current_user: Employee):
    if current_user.role not in ["Manager", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Manager or Admin privileges required."
        )

@router.get("/team")
def get_team_members(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    verify_manager_or_admin(current_user)
    
    if current_user.role == "Admin":
        team = db.query(Employee).all()
    else:
        team = db.query(Employee).filter(Employee.manager_id == current_user.employee_id).all()
        
    return [
        {
            "employee_id": emp.employee_id,
            "name": emp.name,
            "position": emp.position,
            "department": emp.department,
            "role": emp.role,
            "email": emp.email,
            "mobile_phone": emp.mobile_phone
        }
        for emp in team
    ]

# DTR Revision Request (Submitted by Employee)
@router.post("/revisions/request")
def submit_dtr_revision(
    req: CreateRevisionRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    revision = DtrRevision(
        employee_id=current_user.employee_id,
        punch_log_id=req.punch_log_id,
        requested_punch_type=req.requested_punch_type,
        requested_timestamp=req.requested_timestamp,
        reason=req.reason,
        status="PENDING"
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return {"message": "DTR revision submitted successfully", "revision_id": revision.id}

# List Pending Revisions for Manager's Team
@router.get("/revisions")
def list_pending_revisions(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    verify_manager_or_admin(current_user)
    
    if current_user.role == "Admin":
        revisions = db.query(DtrRevision).filter(DtrRevision.status == "PENDING").all()
    else:
        team_emp_ids = [
            emp.employee_id for emp in db.query(Employee).filter(Employee.manager_id == current_user.employee_id).all()
        ]
        revisions = db.query(DtrRevision).filter(
            DtrRevision.employee_id.in_(team_emp_ids),
            DtrRevision.status == "PENDING"
        ).all()
        
    result = []
    for rev in revisions:
        emp = db.query(Employee).filter(Employee.employee_id == rev.employee_id).first()
        result.append({
            "id": rev.id,
            "employee_id": rev.employee_id,
            "employee_name": emp.name if emp else rev.employee_id,
            "punch_log_id": rev.punch_log_id,
            "requested_punch_type": rev.requested_punch_type,
            "requested_timestamp": rev.requested_timestamp.isoformat(),
            "reason": rev.reason,
            "status": rev.status,
            "created_at": rev.created_at.isoformat()
        })
    return result

# Manager Approve or Reject Revision
@router.post("/revisions/{revision_id}/action")
def review_dtr_revision(
    revision_id: int,
    action_req: DtrRevisionAction,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    verify_manager_or_admin(current_user)
    
    revision = db.query(DtrRevision).filter(DtrRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision request not found")
        
    if action_req.action not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Action must be APPROVED or REJECTED")
        
    revision.status = action_req.action
    revision.reviewed_by = current_user.employee_id
    revision.reviewed_at = datetime.utcnow()
    
    # If approved, update existing punch log or insert new punch log
    if action_req.action == "APPROVED":
        if revision.punch_log_id:
            punch = db.query(PunchLog).filter(PunchLog.id == revision.punch_log_id).first()
            if punch:
                punch.timestamp = revision.requested_timestamp
                punch.punch_type = revision.requested_punch_type
        else:
            new_punch = PunchLog(
                employee_id=revision.employee_id,
                punch_type=revision.requested_punch_type,
                timestamp=revision.requested_timestamp
            )
            db.add(new_punch)
            
    db.commit()
    return {"message": f"DTR revision {action_req.action.lower()} successfully"}

# Group Scheduling Endpoints
@router.get("/groups")
def list_schedule_groups(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    verify_manager_or_admin(current_user)
    groups = db.query(ScheduleGroup).all()
    result = []
    for g in groups:
        assignments = db.query(ScheduleGroupAssignment).filter(ScheduleGroupAssignment.group_id == g.id).all()
        emp_ids = [a.employee_id for a in assignments]
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "assigned_count": len(emp_ids),
            "employee_ids": emp_ids
        })
    return result

@router.post("/groups")
def create_schedule_group(
    req: ScheduleGroupCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    verify_manager_or_admin(current_user)
    group = ScheduleGroup(name=req.name, description=req.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    
    for emp_id in req.employee_ids:
        assignment = ScheduleGroupAssignment(group_id=group.id, employee_id=emp_id)
        db.add(assignment)
    db.commit()
    
    return {"message": "Schedule group created successfully", "group_id": group.id}

# Shift Schedules
@router.get("/schedules")
def list_schedules(
    employee_id: Optional[str] = None,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    query = db.query(Schedule)
    if employee_id:
        query = query.filter(Schedule.employee_id == employee_id)
    if group_id:
        query = query.filter(Schedule.group_id == group_id)
        
    schedules = query.all()
    return [
        {
            "id": s.id,
            "employee_id": s.employee_id,
            "group_id": s.group_id,
            "day_of_week": s.day_of_week,
            "shift_start": s.shift_start,
            "shift_end": s.shift_end,
            "break_duration_mins": s.break_duration_mins
        }
        for s in schedules
    ]

@router.post("/schedules")
def create_or_update_schedule(
    req: ShiftScheduleCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    verify_manager_or_admin(current_user)
    sched = Schedule(
        employee_id=req.employee_id,
        group_id=req.group_id,
        day_of_week=req.day_of_week,
        shift_start=req.shift_start,
        shift_end=req.shift_end,
        break_duration_mins=req.break_duration_mins
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return {"message": "Shift schedule saved successfully", "schedule_id": sched.id}
