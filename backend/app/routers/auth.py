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

class UserRegisterRequest(BaseModel):
    first_name: str
    last_name: str
    suffix: Optional[str] = None
    email: str
    password: str
    department: str
    mobile_phone: Optional[str] = None
    name: Optional[str] = None

class UserCreateRequest(BaseModel):
    employee_id: str
    name: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    suffix: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = "Employee"
    email: Optional[str] = None
    mobile_phone: Optional[str] = None

class UserUpdateRequest(BaseModel):
    new_employee_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    suffix: Optional[str] = None
    mobile_phone: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    birthday: Optional[str] = None
    gender: Optional[str] = None
    civil_status: Optional[str] = None
    agency: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class UserStatusUpdateRequest(BaseModel):
    status: str  # 'APPROVED', 'DENIED', 'PENDING', 'ARCHIVED'

@router.post("/register")
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    existing_email = db.query(Employee).filter(Employee.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email is already registered")

    full_name_parts = [payload.first_name.strip(), payload.last_name.strip()]
    if payload.suffix and payload.suffix.strip():
        full_name_parts.append(payload.suffix.strip())
    combined_name = payload.name.strip() if payload.name and payload.name.strip() else " ".join(full_name_parts)

    emp_count = db.query(Employee).count() + 1
    generated_emp_id = f"EMP{str(emp_count).zfill(3)}"

    hashed_pwd = get_password_hash(payload.password)
    new_user = Employee(
        employee_id=generated_emp_id,
        name=combined_name,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        suffix=payload.suffix.strip() if payload.suffix else None,
        email=payload.email,
        password_hash=hashed_pwd,
        department=payload.department,
        mobile_phone=payload.mobile_phone,
        role="Employee",
        status="PENDING"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "success",
        "message": "Registration request submitted. Awaiting admin approval.",
        "employee_id": new_user.employee_id
    }

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(
        (Employee.employee_id == payload.employee_id) | (Employee.email == payload.employee_id)
    ).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials"
        )

    if user.status == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account join request is pending approval by the Admin."
        )

    if user.status == "DENIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account join request was denied by the Admin."
        )

    if user.status == "ARCHIVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been archived. Please contact your System Administrator."
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
        "suffix": current_user.suffix,
        "position": current_user.position,
        "department": current_user.department,
        "role": current_user.role,
        "email": current_user.email,
        "mobile_phone": current_user.mobile_phone,
        "status": current_user.status
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
            "suffix": u.suffix or "",
            "position": u.position or "Staff",
            "department": u.department or "General",
            "mobile_phone": u.mobile_phone or "",
            "email": u.email or "",
            "birthday": u.birthday or "",
            "gender": u.gender or "",
            "civil_status": u.civil_status or "",
            "agency": u.agency or "",
            "role": u.role,
            "status": getattr(u, "status", "APPROVED"),
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(u, "created_at", None) else "",
            "date_added": u.created_at.strftime("%b %d, %Y") if getattr(u, "created_at", None) else "N/A",
            "kiosk_code": u.employee_id.zfill(4)
        })
    return results

@router.put("/users/{emp_id}")
def update_user_profile(
    emp_id: str,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(["Admin"]))
):
    user = db.query(Employee).filter(Employee.employee_id == emp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.new_employee_id and payload.new_employee_id.strip() != emp_id:
        existing_emp = db.query(Employee).filter(Employee.employee_id == payload.new_employee_id.strip()).first()
        if existing_emp:
            raise HTTPException(status_code=400, detail="Employee ID already exists")
        user.employee_id = payload.new_employee_id.strip()

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.suffix is not None:
        user.suffix = payload.suffix

    fname = user.first_name or ""
    lname = user.last_name or ""
    sfx = user.suffix or ""
    parts = [fname.strip(), lname.strip()]
    if sfx.strip():
        parts.append(sfx.strip())
    user.name = " ".join(parts) if any(parts) else user.name

    if payload.mobile_phone is not None:
        user.mobile_phone = payload.mobile_phone
    if payload.email is not None:
        user.email = payload.email
    if payload.position is not None:
        user.position = payload.position
    if payload.department is not None:
        user.department = payload.department
    if payload.birthday is not None:
        user.birthday = payload.birthday
    if payload.gender is not None:
        user.gender = payload.gender
    if payload.civil_status is not None:
        user.civil_status = payload.civil_status
    if payload.agency is not None:
        user.agency = payload.agency
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        user.status = payload.status

    db.commit()
    db.refresh(user)
    return {"status": "success", "message": f"User updated successfully", "employee_id": user.employee_id}

@router.put("/users/{emp_id}/status")
def update_user_status(
    emp_id: str,
    payload: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(["Admin"]))
):
    user = db.query(Employee).filter(Employee.employee_id == emp_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = payload.status
    db.commit()
    db.refresh(user)
    return {"status": "success", "message": f"User status updated to {payload.status}"}
