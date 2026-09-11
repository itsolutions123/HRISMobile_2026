import os
import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict
from . import models

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hrisuser:hrispassword@hris-db:5432/hrisdb")
MANILA_TZ = ZoneInfo("Asia/Manila")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS Core API & Admin Suite (GMT+8)", version="2.1.0")

MAX_SHIFT_SECONDS = 20 * 3600

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_now_manila():
    return datetime.now(MANILA_TZ)

# --- Pydantic Schemas ---
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

class EditPunchRequest(BaseModel):
    punch_type: str
    timestamp: str
    address: Optional[str] = None

class CreatePunchAdminRequest(BaseModel):
    employee_id: str
    punch_type: str
    timestamp: str
    latitude: float = 0.0
    longitude: float = 0.0
    address: Optional[str] = "Manual Admin Entry"

# --- Authentication & Seeding ---
@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == req.employee_id).first()
    
    if not user:
        if req.employee_id.upper() in ["ADMIN", "SUPERADMIN", "SA-001"]:
            user = models.User(
                employee_id=req.employee_id,
                name="Super Admin",
                department="Executive",
                position="System Administrator",
                role="super_admin",
                hashed_password="password123"
            )
        else:
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

# --- Punch Endpoints ---
@app.get("/api/punch/active/{employee_id}")
def get_active_punch(employee_id: str, db: Session = Depends(get_db)):
    last_punch = db.query(models.TimePunch)\
        .filter(models.TimePunch.employee_id == employee_id)\
        .order_by(desc(models.TimePunch.timestamp))\
        .first()

    if not last_punch or last_punch.punch_type == "CLOCK_OUT":
        return {"is_clocked_in": False, "last_punch": last_punch}

    now_manila = get_now_manila().replace(tzinfo=None)
    elapsed_seconds = int((now_manila - last_punch.timestamp).total_seconds())

    if elapsed_seconds >= MAX_SHIFT_SECONDS:
        auto_out = models.TimePunch(
            employee_id=employee_id,
            punch_type="CLOCK_OUT",
            latitude=last_punch.latitude,
            longitude=last_punch.longitude,
            accuracy=0.0,
            address="AUTO CLOCK-OUT (20hr Limit Exceeded)",
            timestamp=get_now_manila().replace(tzinfo=None)
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
        address=req.address,
        timestamp=get_now_manila().replace(tzinfo=None)
    )
    db.add(punch)
    db.commit()
    db.refresh(punch)
    return {"status": "success", "punch_id": punch.id, "timestamp": punch.timestamp.isoformat()}

@app.get("/api/timesheet/{employee_id}")
def get_employee_timesheet(employee_id: str, db: Session = Depends(get_db)):
    punches = db.query(models.TimePunch)\
        .filter(models.TimePunch.employee_id == employee_id)\
        .order_by(desc(models.TimePunch.timestamp))\
        .all()

    timesheet_by_date = defaultdict(list)
    raw_list = []

    for p in punches:
        date_str = p.timestamp.strftime("%Y-%m-%d")
        punch_obj = {
            "id": p.id,
            "punch_type": p.punch_type,
            "time": p.timestamp.strftime("%I:%M:%S %p"),
            "timestamp": p.timestamp.isoformat(),
            "date": date_str,
            "address": p.address or "Location Captured",
            "lat": p.latitude,
            "lng": p.longitude
        }
        timesheet_by_date[date_str].append(punch_obj)
        raw_list.append(punch_obj)

    formatted_history = []
    for date_key, day_punches in timesheet_by_date.items():
        total_seconds = 0
        in_time = None
        chronological = sorted(day_punches, key=lambda x: x["timestamp"])

        for p in chronological:
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

    return {
        "employee_id": employee_id,
        "timesheet": formatted_history,
        "all_punches": raw_list
    }

# --- Super Admin DTR CRUD API ---
@app.get("/api/admin/dtr")
def list_all_dtr(employee_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.TimePunch)
    if employee_id:
        query = query.filter(models.TimePunch.employee_id == employee_id)
    punches = query.order_by(desc(models.TimePunch.timestamp)).all()
    return punches

@app.post("/api/admin/dtr")
def create_dtr_entry(req: CreatePunchAdminRequest, db: Session = Depends(get_db)):
    try:
        ts = datetime.fromisoformat(req.timestamp).replace(tzinfo=None)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ISO timestamp format")

    punch = models.TimePunch(
        employee_id=req.employee_id,
        punch_type=req.punch_type,
        timestamp=ts,
        latitude=req.latitude,
        longitude=req.longitude,
        address=req.address
    )
    db.add(punch)
    db.commit()
    db.refresh(punch)
    return {"status": "created", "punch": punch}

@app.put("/api/admin/dtr/{punch_id}")
def update_dtr_entry(punch_id: int, req: EditPunchRequest, db: Session = Depends(get_db)):
    punch = db.query(models.TimePunch).filter(models.TimePunch.id == punch_id).first()
    if not punch:
        raise HTTPException(status_code=404, detail="Punch record not found")

    try:
        ts = datetime.fromisoformat(req.timestamp).replace(tzinfo=None)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ISO timestamp format")

    punch.punch_type = req.punch_type
    punch.timestamp = ts
    if req.address:
        punch.address = req.address

    db.commit()
    db.refresh(punch)
    return {"status": "updated", "punch": punch}

@app.delete("/api/admin/dtr/{punch_id}")
def delete_dtr_entry(punch_id: int, db: Session = Depends(get_db)):
    punch = db.query(models.TimePunch).filter(models.TimePunch.id == punch_id).first()
    if not punch:
        raise HTTPException(status_code=404, detail="Punch record not found")

    db.delete(punch)
    db.commit()
    return {"status": "deleted", "punch_id": punch_id}

# --- CSV Export Endpoint ---
@app.get("/api/admin/export/csv")
def export_dtr_csv(employee_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.TimePunch)
    if employee_id:
        query = query.filter(models.TimePunch.employee_id == employee_id)
    punches = query.order_by(models.TimePunch.employee_id.asc(), models.TimePunch.timestamp.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Punch ID", "Employee ID", "Punch Type", "Timestamp (GMT+8)", "Address", "Latitude", "Longitude"])

    for p in punches:
        formatted_ts = p.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([p.id, p.employee_id, p.punch_type, formatted_ts, p.address, p.latitude, p.longitude])

    response = Response(content=output.getvalue(), media_type="text/csv")
    filename = f"DTR_Export_{employee_id or 'ALL'}_{get_now_manila().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

# --- Mobile & Desktop Responsive Web Admin Portal (GMT+8 Manila Time) ---
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HRIS Super Admin Web Portal (GMT+8)</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 text-slate-800 antialiased min-h-screen">
        <nav class="bg-blue-600 text-white p-4 shadow-md flex justify-between items-center">
            <div>
                <h1 class="text-xl font-bold">HRIS Super Admin Portal</h1>
                <p class="text-xs text-blue-100">Timezone: Asia/Manila (GMT+8 / PHT)</p>
            </div>
            <a href="/api/admin/export/csv" class="bg-green-500 hover:bg-green-600 px-3 py-2 rounded text-sm font-semibold transition">Export CSV</a>
        </nav>

        <main class="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
            <div class="bg-white p-5 rounded-lg shadow-sm border border-slate-200">
                <h2 class="text-lg font-bold mb-4 text-slate-700">Add Manual DTR Entry (GMT+8)</h2>
                <form id="addForm" class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <input type="text" id="addEmpId" placeholder="Employee ID (e.g., 3286)" required class="border p-2 rounded text-sm">
                    <select id="addType" class="border p-2 rounded text-sm">
                        <option value="CLOCK_IN">CLOCK_IN</option>
                        <option value="CLOCK_OUT">CLOCK_OUT</option>
                    </select>
                    <input type="datetime-local" id="addTime" required class="border p-2 rounded text-sm">
                    <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded text-sm transition">Create Entry</button>
                </form>
            </div>

            <div class="bg-white p-5 rounded-lg shadow-sm border border-slate-200 overflow-x-auto">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-bold text-slate-700">DTR Audit Records</h2>
                    <button onclick="loadPunches()" class="text-sm bg-slate-200 hover:bg-slate-300 px-3 py-1 rounded">Refresh</button>
                </div>
                <table class="w-full text-left text-sm border-collapse">
                    <thead>
                        <tr class="bg-slate-50 border-b">
                            <th class="p-3">ID</th>
                            <th class="p-3">Employee</th>
                            <th class="p-3">Type</th>
                            <th class="p-3">Timestamp (GMT+8)</th>
                            <th class="p-3">Location</th>
                            <th class="p-3">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="dtrTableBody">
                        <tr><td colspan="6" class="p-4 text-center text-slate-400">Loading records...</td></tr>
                    </tbody>
                </table>
            </div>
        </main>

        <script>
            const API_BASE = "/api/admin";

            async function loadPunches() {
                const res = await fetch(`${API_BASE}/dtr`);
                const data = await res.json();
                const tbody = document.getElementById("dtrTableBody");
                tbody.innerHTML = "";

                data.forEach(p => {
                    const row = document.createElement("tr");
                    row.className = "border-b hover:bg-slate-50";
                    row.innerHTML = `
                        <td class="p-3 font-mono text-xs">${p.id}</td>
                        <td class="p-3 font-bold">${p.employee_id}</td>
                        <td class="p-3"><span class="px-2 py-1 text-xs rounded font-bold ${p.punch_type === 'CLOCK_IN' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${p.punch_type}</span></td>
                        <td class="p-3 text-xs font-mono">${p.timestamp.replace('T', ' ')}</td>
                        <td class="p-3 text-xs text-slate-500">${p.address || 'N/A'}</td>
                        <td class="p-3 space-x-2">
                            <button onclick="deletePunch(${p.id})" class="text-xs bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }

            document.getElementById("addForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const empId = document.getElementById("addEmpId").value;
                const type = document.getElementById("addType").value;
                const timeVal = document.getElementById("addTime").value;

                await fetch(`${API_BASE}/dtr`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        employee_id: empId,
                        punch_type: type,
                        timestamp: timeVal + ":00",
                        address: "Manual Web Admin Entry"
                    })
                });
                loadPunches();
            });

            async function deletePunch(id) {
                if (confirm(`Delete DTR Entry #${id}?`)) {
                    await fetch(`${API_BASE}/dtr/${id}`, { method: "DELETE" });
                    loadPunches();
                }
            }

            loadPunches();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
