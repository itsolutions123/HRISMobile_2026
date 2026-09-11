import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List
from . import models

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hrisuser:hrispassword@hris-db:5432/hrisdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS Core API", version="1.0.0")

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

@app.get("/health")
def health_check():
    return {"status": "online", "service": "HRIS FastAPI Backend"}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == req.employee_id).first()
    if not user:
        # Seed default test accounts on first login attempt
        if req.employee_id == "EMP-1001":
            user = models.User(
                employee_id="EMP-1001",
                name="John Doe (Employee)",
                department="IT Operations",
                role="employee",
                hashed_password="password123"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        elif req.employee_id == "MGR-2001":
            user = models.User(
                employee_id="MGR-2001",
                name="Jane Doe (Manager)",
                department="IT Operations",
                role="manager",
                hashed_password="password123"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(status_code=400, detail="Invalid Employee ID")

    return {
        "employee_id": user.employee_id,
        "name": user.name,
        "department": user.department,
        "role": user.role,
        "token": f"fake-jwt-token-{user.employee_id}"
    }

@app.post("/api/punch")
def record_punch(req: PunchRequest, db: Session = Depends(get_db)):
    punch = models.TimePunch(
        employee_id=req.employee_id,
        punch_type=req.punch_type,
        latitude=req.latitude,
        longitude=req.longitude,
        accuracy=req.accuracy
    )
    db.add(punch)
    db.commit()
    db.refresh(punch)
    return {"status": "success", "punch_id": punch.id, "timestamp": punch.timestamp}

@app.get("/api/manager/punches")
def get_department_punches(department: str, db: Session = Depends(get_db)):
    punches = db.query(models.TimePunch).all()
    return {"department": department, "total_records": len(punches), "punches": punches}
