from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import zoneinfo
import io
import csv
from ..database import get_db
from ..models import PunchLog, Employee

router = APIRouter(prefix="/api/punch", tags=["DTR Punch"])

MANILA_TZ = zoneinfo.ZoneInfo("Asia/Manila")

def get_manila_now():
    return datetime.now(MANILA_TZ)

class PunchRequest(BaseModel):
    employee_id: str
    punch_type: str  # CLOCK_IN, CLOCK_OUT, BREAK_IN, BREAK_OUT
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    address: Optional[str] = None
    is_mock: Optional[bool] = False  # Client spoof detection flag

@router.get("/active/{employee_id}")
def get_active_punch(employee_id: str, db: Session = Depends(get_db)):
    last_punch = db.query(PunchLog).filter(
        PunchLog.employee_id == employee_id
    ).order_by(PunchLog.id.desc()).first()

    if not last_punch or last_punch.punch_type.upper() == "CLOCK_OUT":
        return {"is_clocked_in": False, "elapsed_seconds": 0}

    now = get_manila_now().replace(tzinfo=None)
    last_ts = last_punch.timestamp.replace(tzinfo=None) if last_punch.timestamp else now
    elapsed = max(0, int((now - last_ts).total_seconds()))
    
    return {
        "is_clocked_in": True,
        "elapsed_seconds": elapsed,
        "clock_in_time": last_ts.isoformat(),
        "job_name": last_punch.address
    }

@router.get("/logs")
def get_all_punch_logs(db: Session = Depends(get_db)):
    logs = db.query(PunchLog).order_by(PunchLog.id.desc()).all()
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
    # 1. Reject if GPS data is missing/denied
    if payload.latitude is None or payload.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="GPS coordinates are required. Please enable location permissions to punch."
        )

    # 2. Reject mock location / anti-spoofing check
    if payload.is_mock:
        raise HTTPException(
            status_code=400,
            detail="Mock location or spoofed GPS detected. Punch rejected."
        )

    # 3. Reject invalid lat/long ranges
    if not (-90.0 <= payload.latitude <= 90.0) or not (-180.0 <= payload.longitude <= 180.0):
        raise HTTPException(
            status_code=400,
            detail="Invalid GPS coordinates supplied."
        )

    # 4. Strict duplicate / sequence validation ordering by primary key ID
    last_punch = db.query(PunchLog).filter(
        PunchLog.employee_id == payload.employee_id
    ).order_by(PunchLog.id.desc()).first()

    requested_type = payload.punch_type.strip().upper()

    if last_punch and last_punch.punch_type.strip().upper() == requested_type:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate punch rejected. You are already recorded as {requested_type}."
        )

    # 5. Record punch using Philippine Standard Time
    now_pst = get_manila_now().replace(tzinfo=None)

    new_punch = PunchLog(
        employee_id=payload.employee_id,
        punch_type=requested_type,
        timestamp=now_pst,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        address=payload.address
    )
    db.add(new_punch)
    db.commit()
    db.refresh(new_punch)
    return {"status": "success", "punch_id": new_punch.id, "timestamp": now_pst.isoformat()}

@router.get("/export")
def export_punch_logs(db: Session = Depends(get_db)):
    logs = db.query(PunchLog).order_by(PunchLog.id.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log ID", "Employee ID", "Punch Type", "Timestamp (PST)", "Latitude", "Longitude", "Accuracy", "Role/Note"])

    for log in logs:
        writer.writerow([
            log.id,
            log.employee_id,
            log.punch_type,
            log.timestamp.isoformat() if log.timestamp else "",
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
