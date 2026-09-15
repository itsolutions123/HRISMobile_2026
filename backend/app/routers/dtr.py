from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import io
import openpyxl
from simpleeval import simple_eval

from ..database import get_db
from ..models import Employee, PunchLog, Schedule, ScheduleGroupAssignment
from .auth import get_current_user
from ..dtr_engine import compute_daily_dtr

router = APIRouter(prefix="/api/dtr", tags=["DTR Computation & Export"])

def get_employee_schedule_for_day(db: Session, employee_id: str, day_of_week: int):
    # 1. Direct individual schedule
    sched = db.query(Schedule).filter(
        Schedule.employee_id == employee_id,
        Schedule.day_of_week == day_of_week
    ).first()
    if sched:
        return sched

    # 2. Group schedule fallback
    assignments = db.query(ScheduleGroupAssignment).filter(
        ScheduleGroupAssignment.employee_id == employee_id
    ).all()
    group_ids = [a.group_id for a in assignments]
    if group_ids:
        group_sched = db.query(Schedule).filter(
            Schedule.group_id.in_(group_ids),
            Schedule.day_of_week == day_of_week
        ).first()
        if group_sched:
            return group_sched

    return None

@router.get("/summary/{employee_id}")
def get_dtr_summary(
    employee_id: str,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    if current_user.role not in ["Manager", "Admin"] and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if s_date > e_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date.")

    daily_records = []
    tot_regular_hours = 0.0
    tot_late_minutes = 0
    tot_undertime_minutes = 0
    tot_overtime_hours = 0.0

    curr = s_date
    while curr <= e_date:
        curr_str = curr.strftime("%Y-%m-%d")
        day_start = datetime.combine(curr, datetime.min.time())
        day_end = datetime.combine(curr, datetime.max.time())

        punches = db.query(PunchLog).filter(
            PunchLog.employee_id == employee_id,
            PunchLog.timestamp >= day_start,
            PunchLog.timestamp <= day_end
        ).order_by(PunchLog.timestamp.asc()).all()

        punch_list = [{"punch_type": p.punch_type, "timestamp": p.timestamp} for p in punches]
        sched = get_employee_schedule_for_day(db, employee_id, curr.weekday())

        shift_start = sched.shift_start if sched else "08:00"
        shift_end = sched.shift_end if sched else "17:00"
        break_duration = sched.break_duration_mins if sched else 60

        daily_res = compute_daily_dtr(
            date_str=curr_str,
            punches=punch_list,
            shift_start_str=shift_start,
            shift_end_str=shift_end,
            break_duration_mins=break_duration,
            grace_period_mins=15,
            overtime_approved=False
        )

        daily_records.append(daily_res)
        tot_regular_hours += daily_res["regular_hours"]
        tot_late_minutes += daily_res["late_minutes"]
        tot_undertime_minutes += daily_res["undertime_minutes"]
        tot_overtime_hours += daily_res["overtime_hours"]

        curr += timedelta(days=1)

    return {
        "employee_id": employee_id,
        "start_date": start_date,
        "end_date": end_date,
        "totals": {
            "regular_hours": round(tot_regular_hours, 2),
            "late_minutes": tot_late_minutes,
            "undertime_minutes": tot_undertime_minutes,
            "overtime_hours": round(tot_overtime_hours, 2)
        },
        "daily_details": daily_records
    }

@router.get("/export")
def export_dtr_report(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    employee_id: Optional[str] = Query(None),
    custom_formula: Optional[str] = Query(None, description="E.g., 'regular_hours * 15.5 + overtime_hours * 23.25'"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    if current_user.role not in ["Manager", "Admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin privileges required.")

    if employee_id:
        employees = db.query(Employee).filter(Employee.employee_id == employee_id).all()
    else:
        employees = db.query(Employee).all()

    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Timesheet Export"

    headers = [
        "Type", "Sub-job", "Total number of shifts", "Total shift hours",
        "First name", "Last name", "Start Date", "In", "Start - location",
        "End Date", "Out", "End - location", "Shift hours"
    ]
    if custom_formula:
        headers.append("Custom Calc Result")

    ws.append(headers)

    for emp in employees:
        curr = s_date
        while curr <= e_date:
            curr_str = curr.strftime("%Y-%m-%d")
            day_start = datetime.combine(curr, datetime.min.time())
            day_end = datetime.combine(curr, datetime.max.time())

            punches = db.query(PunchLog).filter(
                PunchLog.employee_id == emp.employee_id,
                PunchLog.timestamp >= day_start,
                PunchLog.timestamp <= day_end
            ).order_by(PunchLog.timestamp.asc()).all()

            punch_list = [{"punch_type": p.punch_type, "timestamp": p.timestamp} for p in punches]
            sched = get_employee_schedule_for_day(db, emp.employee_id, curr.weekday())

            shift_start = sched.shift_start if sched else "08:00"
            shift_end = sched.shift_end if sched else "17:00"
            break_duration = sched.break_duration_mins if sched else 60

            res = compute_daily_dtr(
                date_str=curr_str,
                punches=punch_list,
                shift_start_str=shift_start,
                shift_end_str=shift_end,
                break_duration_mins=break_duration,
                grace_period_mins=15,
                overtime_approved=False
            )

            start_loc = ""
            end_loc = ""
            if punches:
                first_p = punches[0]
                last_p = punches[-1]
                start_loc = f"{getattr(first_p, 'latitude', '')}, {getattr(first_p, 'longitude', '')}".strip(', ')
                end_loc = f"{getattr(last_p, 'latitude', '')}, {getattr(last_p, 'longitude', '')}".strip(', ')

            worked_hours = res.get("regular_hours", 0.0)
            shift_count = 1 if worked_hours > 0 else 0
            
            # Use fallback on name splits if actual first_name/last_name attributes are unexpectedly missing on legacy entries
            f_name = getattr(emp, "first_name", emp.name.split()[0] if emp.name else "")
            l_name = getattr(emp, "last_name", emp.name.split()[-1] if emp.name and " " in emp.name else "")

            row = [
                "Regular",
                emp.position or "",
                shift_count,
                worked_hours,
                f_name,
                l_name,
                res["date"],
                res["clock_in"] or "",
                start_loc,
                res["date"],
                res["clock_out"] or "",
                end_loc,
                worked_hours
            ]

            if custom_formula:
                eval_vars = {
                    "regular_hours": res.get("regular_hours", 0.0),
                    "late_minutes": res.get("late_minutes", 0),
                    "undertime_minutes": res.get("undertime_minutes", 0),
                    "overtime_hours": res.get("overtime_hours", 0.0),
                }
                try:
                    calc_result = simple_eval(custom_formula, names=eval_vars)
                    row.append(calc_result)
                except Exception as e:
                    row.append(f"ERR: {str(e)}")

            ws.append(row)
            curr += timedelta(days=1)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"dtr_report_{start_date}_to_{end_date}.xlsx"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
