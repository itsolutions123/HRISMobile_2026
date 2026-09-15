from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..models import Employee
from ..auth_utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    require_roles
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    employee_id: str
    password: str

class UserCreateRequest(BaseModel):
    employee_id: str
    name: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = "Employee"
    email: Optional[str] = None
    mobile_phone: Optional[str] = None

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
    role: Optional[str] = None

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Employee ID or Password"
        )
    
    access_token = create_access_token(
        data={"sub": user.employee_id, "role": user.role}
    )
    
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "employee_id": user.employee_id,
            "name": user.name,
            "position": user.position,
            "department": user.department,
            "role": user.role
        }
    }

@router.get("/me")
def get_me(current_user: Employee = Depends(get_current_user)):
    return {
        "employee_id": current_user.employee_id,
        "name": current_user.name,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "position": current_user.position,
        "department": current_user.department,
        "role": current_user.role,
        "email": current_user.email,
        "mobile_phone": current_user.mobile_phone
    }

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(["Admin", "Manager"]))
):
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
            "position": u.position or "Staff",
            "department": u.department or "General",
            "mobile_phone": u.mobile_phone or "",
            "email": u.email or "",
            "birthday": u.birthday or "",
            "gender": u.gender or "",
            "civil_status": u.civil_status or "",
            "agency": u.agency or "",
            "role": u.role,
            "kiosk_code": u.employee_id.zfill(4)
        })
    return results

@router.post("/users")
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(["Admin"]))
):
    existing = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID already exists")

    hashed_pwd = get_password_hash(payload.password)
    new_user = Employee(
        employee_id=payload.employee_id,
        name=payload.name,
        first_name=payload.first_name,
        last_name=payload.last_name,
        position=payload.position,
        department=payload.department,
        password_hash=hashed_pwd,
        role=payload.role or "Employee",
        email=payload.email,
        mobile_phone=payload.mobile_phone
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "success", "message": "User created", "employee_id": new_user.employee_id}

@router.put("/users/{emp_id}")
def update_user_details(
    emp_id: str,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(["Admin"]))
):
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
    if payload.role is not None: user.role = payload.role

    db.commit()
    db.refresh(user)
    return {"status": "success", "message": "User information updated"}
