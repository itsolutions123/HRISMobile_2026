from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import io
import csv
from ..database import get_db
from ..models import PunchLog, Employee

router = APIRouter(prefix="/api/punch", tags=["DTR Punch"])

class PunchRequest(BaseModel):
    employee_id: str
    punch_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    address: Optional[str] = None

@router.get("/active/{employee_id}")
def get_active_punch(employee_id: str, db: Session = Depends(get_db)):
    last_punch = db.query(PunchLog).filter(
        PunchLog.employee_id == employee_id
    ).order_by(PunchLog.timestamp.desc()).first()

    if not last_punch or last_punch.punch_type == "CLOCK_OUT":
        return {"is_clocked_in": False, "elapsed_seconds": 0}

    elapsed = int((datetime.utcnow() - last_punch.timestamp).total_seconds())
    return {
        "is_clocked_in": True,
        "elapsed_seconds": elapsed,
        "clock_in_time": last_punch.timestamp.isoformat(),
        "job_name": last_punch.address
    }

@router.get("/logs")
def get_all_punch_logs(db: Session = Depends(get_db)):
    logs = db.query(PunchLog).order_by(PunchLog.timestamp.desc()).all()
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "employee_id": log.employee_id,
            "punch_type": log.punch_type,
            "timestamp": log.timestamp.strftime("%m/%d/%Y, %I:%M:%S %p") if log.timestamp else "N/A",
            "latitude": log.latitude,
            "longitude": log.longitude,
            "accuracy": log.accuracy or 10,
            "address": log.address or "Duty Shift"
        })
    return results

@router.post("")
def record_punch(payload: PunchRequest, db: Session = Depends(get_db)):
    new_punch = PunchLog(
        employee_id=payload.employee_id,
        punch_type=payload.punch_type,
        timestamp=datetime.utcnow(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        address=payload.address
    )
    db.add(new_punch)
    db.commit()
    db.refresh(new_punch)
    return {"status": "success", "punch_id": new_punch.id}

@router.get("/export")
def export_punch_logs(db: Session = Depends(get_db)):
    logs = db.query(PunchLog).order_by(PunchLog.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log ID", "Employee ID", "Punch Type", "Timestamp (UTC)", "Latitude", "Longitude", "Accuracy", "Role/Note"])

    for log in logs:
        writer.writerow([
            log.id,
            log.employee_id,
            log.punch_type,
            log.timestamp.isoformat(),
            log.latitude,
            log.longitude,
            log.accuracy,
            log.address
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dtr_timesheet_export.csv"}
    )
