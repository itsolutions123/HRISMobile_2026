from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..models import Employee

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    employee_id: str
    password: str

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile_phone: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    birthday: Optional[str] = None
    gender: Optional[str] = None
    civil_status: Optional[str] = None
    agency: Optional[str] = None

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if not user or user.password_hash != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Employee ID or Password"
        )
    return {
        "status": "success",
        "user": {
            "employee_id": user.employee_id,
            "name": user.name,
            "position": user.position,
            "department": user.department
        }
    }

@router.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(Employee).all()
    results = []
    for u in users:
        first = u.first_name or (u.name.split(" ")[0] if u.name else "")
        last = u.last_name or (u.name.split(" ")[-1] if len(u.name.split(" ")) > 1 else "")
        results.append({
            "employee_id": u.employee_id,
            "name": u.name,
            "first_name": first,
            "last_name": last,
            "position": u.position or "IT System Administrator",
            "department": u.department or "Admin",
            "mobile_phone": u.mobile_phone or "+63 998 940 0957",
            "email": u.email or "itsupport.associate@bigtimeempire.com",
            "birthday": u.birthday or "1994-08-15",
            "gender": u.gender or "Male",
            "civil_status": u.civil_status or "Single",
            "agency": u.agency or "Direct Hire",
            "kiosk_code": u.employee_id.zfill(4),
            "last_login": "09/14/2026",
            "date_added": "06/05/2023"
        })
    return results

@router.put("/users/{emp_id}")
def update_user_details(emp_id: str, payload: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.employee_id == emp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.first_name is not None: user.first_name = payload.first_name
    if payload.last_name is not None: user.last_name = payload.last_name
    if payload.first_name or payload.last_name:
        user.name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if payload.mobile_phone is not None: user.mobile_phone = payload.mobile_phone
    if payload.email is not None: user.email = payload.email
    if payload.position is not None: user.position = payload.position
    if payload.department is not None: user.department = payload.department
    if payload.birthday is not None: user.birthday = payload.birthday
    if payload.gender is not None: user.gender = payload.gender
    if payload.civil_status is not None: user.civil_status = payload.civil_status
    if payload.agency is not None: user.agency = payload.agency

    db.commit()
    db.refresh(user)
    return {"status": "success", "message": "User information updated"}
