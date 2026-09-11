import os
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
from . import models

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hrisuser:hrispassword@hris-db:5432/hrisdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS Core API", version="1.1.0")

MAX_SHIFT_SECONDS = 20 * 3600  # 20 hours limit

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LoginRequest(BaseModel):
    employee_id: str
    password: str

class PunchRequest(BaseModel):
    employee_id: str
    punch_type: str
    latitude: float
    longitude: float
    accuracy: float
    address: Optional[str] = None

@app.get("/health")
def health_check():
    return {"status": "online", "service": "HRIS FastAPI Backend"}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == req.employee_id).first()
    
    if not user:
        is_manager = req.employee_id.startswith("MGR")
        user = models.User(
            employee_id=req.employee_id,
            name=f"Employee #{req.employee_id}",
            department="IT Operations",
            position="IT Specialist" if not is_manager else "Operations Manager",
            role="manager" if is_manager else "employee",
            hashed_password="password123"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "employee_id": user.employee_id,
        "name": user.name,
        "department": user.department,
        "position": user.position,
        "role": user.role,
        "token": f"fake-jwt-token-{user.employee_id}"
    }

@app.get("/api/punch/active/{employee_id}")
def get_active_punch(employee_id: str, db: Session = Depends(get_db)):
    # Retrieve the latest punch for this employee
    last_punch = db.query(models.TimePunch)\
        .filter(models.TimePunch.employee_id == employee_id)\
        .order_by(desc(models.TimePunch.timestamp))\
        .first()

    if not last_punch or last_punch.punch_type == "CLOCK_OUT":
        return {"is_clocked_in": False, "last_punch": last_punch}

    # Evaluate 20-Hour Auto-Checkout Rule
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    elapsed_seconds = int((now - last_punch.timestamp).total_seconds())

    if elapsed_seconds >= MAX_SHIFT_SECONDS:
        # Auto-Clock Out
        auto_out = models.TimePunch(
            employee_id=employee_id,
            punch_type="CLOCK_OUT",
            latitude=last_punch.latitude,
            longitude=last_punch.longitude,
            accuracy=0.0,
            address="AUTO CLOCK-OUT (20hr Limit Exceeded)",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(auto_out)
        db.commit()
        db.refresh(auto_out)
        return {"is_clocked_in": False, "last_punch": auto_out, "auto_clocked_out": True}

    return {
        "is_clocked_in": True,
        "elapsed_seconds": elapsed_seconds,
        "clock_in_time": last_punch.timestamp.isoformat(),
        "last_punch": last_punch
    }

@app.post("/api/punch")
def record_punch(req: PunchRequest, db: Session = Depends(get_db)):
    punch = models.TimePunch(
        employee_id=req.employee_id,
        punch_type=req.punch_type,
        latitude=req.latitude,
        longitude=req.longitude,
        accuracy=req.accuracy,
        address=req.address
    )
    db.add(punch)
    db.commit()
    db.refresh(punch)
    return {"status": "success", "punch_id": punch.id, "timestamp": punch.timestamp}
