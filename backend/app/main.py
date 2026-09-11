import os
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional, List
from collections import defaultdict
from . import models

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hrisuser:hrispassword@hris-db:5432/hrisdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS Core API", version="1.2.0")

MAX_SHIFT_SECONDS = 20 * 3600

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
    last_punch = db.query(models.TimePunch)\
        .filter(models.TimePunch.employee_id == employee_id)\
        .order_by(desc(models.TimePunch.timestamp))\
        .first()

    if not last_punch or last_punch.punch_type == "CLOCK_OUT":
        return {"is_clocked_in": False, "last_punch": last_punch}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    elapsed_seconds = int((now - last_punch.timestamp).total_seconds())

    if elapsed_seconds >= MAX_SHIFT_SECONDS:
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

@app.get("/api/timesheet/{employee_id}")
def get_employee_timesheet(employee_id: str, db: Session = Depends(get_db)):
    punches = db.query(models.TimePunch)\
        .filter(models.TimePunch.employee_id == employee_id)\
        .order_by(models.TimePunch.timestamp.asc())\
        .all()

    # Group punches by YYYY-MM-DD
    timesheet_by_date = defaultdict(list)
    for p in punches:
        date_str = p.timestamp.strftime("%Y-%m-%d")
        timesheet_by_date[date_str].append({
            "id": p.id,
            "punch_type": p.punch_type,
            "time": p.timestamp.strftime("%I:%M:%S %p"),
            "timestamp": p.timestamp.isoformat(),
            "address": p.address or "Location Captured",
            "lat": p.latitude,
            "lng": p.longitude
        })

    formatted_history = []
    for date_key, day_punches in timesheet_by_date.items():
        # Calculate daily hours worked based on clock-in / clock-out pairs
        total_seconds = 0
        in_time = None

        for p in day_punches:
            dt = datetime.fromisoformat(p["timestamp"])
            if p["punch_type"] == "CLOCK_IN":
                in_time = dt
            elif p["punch_type"] == "CLOCK_OUT" and in_time:
                total_seconds += (dt - in_time).total_seconds()
                in_time = None

        hrs = int(total_seconds // 3600)
        mins = int((total_seconds % 3600) // 60)

        formatted_history.append({
            "date": date_key,
            "display_date": datetime.strptime(date_key, "%Y-%m-%d").strftime("%A, %b %d, %Y"),
            "total_duration": f"{hrs}h {mins}m",
            "punches": day_punches
        })

    # Return reverse chronological order
    return {"employee_id": employee_id, "timesheet": list(reversed(formatted_history))}
