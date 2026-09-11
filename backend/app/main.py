import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
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
    address: Optional[str] = None

@app.get("/health")
def health_check():
    return {"status": "online", "service": "HRIS FastAPI Backend"}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == req.employee_id).first()
    if not user:
        if req.employee_id == "EMP-1001":
            user = models.User(
                employee_id="EMP-1001",
                name="John Doe",
                department="IT Operations",
                position="Systems Administrator",
                role="employee",
                hashed_password="password123"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        elif req.employee_id == "MGR-2001":
            user = models.User(
                employee_id="MGR-2001",
                name="Jane Doe",
                department="IT Operations",
                position="IT Operations Manager",
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
        "position": user.position,
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
        accuracy=req.accuracy,
        address=req.address
    )
    db.add(punch)
    db.commit()
    db.refresh(punch)
    return {"status": "success", "punch_id": punch.id, "timestamp": punch.timestamp}
