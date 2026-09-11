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

app = FastAPI(title="HRIS Core API & Admin Suite", version="2.2.0")

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

# --- Mobile Punch Endpoints ---
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
    
    # Clean formatted response
    result = []
    for p in punches:
        result.append({
            "id": p.id,
            "employee_id": p.employee_id,
            "punch_type": p.punch_type,
            "raw_timestamp": p.timestamp.isoformat(),
            "formatted_time": p.timestamp.strftime("%Y-%m-%d %I:%M:%S %p"),
            "address": p.address or " Pasig, Metro Manila",
            "latitude": p.latitude,
            "longitude": p.longitude
        })
    return result

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
    return {"status": "created", "punch_id": punch.id}

@app.delete("/api/admin/dtr/{punch_id}")
def delete_dtr_entry(punch_id: int, db: Session = Depends(get_db)):
    punch = db.query(models.TimePunch).filter(models.TimePunch.id == punch_id).first()
    if not punch:
        raise HTTPException(status_code=404, detail="Punch record not found")

    db.delete(punch)
    db.commit()
    return {"status": "deleted", "punch_id": punch_id}

@app.get("/api/admin/export/csv")
def export_dtr_csv(employee_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.TimePunch)
    if employee_id:
        query = query.filter(models.TimePunch.employee_id == employee_id)
    punches = query.order_by(models.TimePunch.employee_id.asc(), models.TimePunch.timestamp.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Punch ID", "Employee ID", "Punch Type", "Timestamp", "Address", "Latitude", "Longitude"])

    for p in punches:
        formatted_ts = p.timestamp.strftime("%Y-%m-%d %I:%M:%S %p")
        writer.writerow([p.id, p.employee_id, p.punch_type, formatted_ts, p.address, p.latitude, p.longitude])

    response = Response(content=output.getvalue(), media_type="text/csv")
    filename = f"DTR_Export_{employee_id or 'ALL'}_{get_now_manila().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

# --- Modernized & Responsive Super Admin Web Portal ---
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HRIS Administration Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; }
        </style>
    </head>
    <body class="bg-slate-50 text-slate-900 min-h-screen antialiased">

        <!-- Login Overlay Guard -->
        <div id="loginOverlay" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-sm w-full p-6 space-y-5">
                <div class="text-center space-y-1">
                    <div class="w-12 h-12 bg-blue-600 text-white rounded-xl mx-auto flex items-center justify-center font-bold text-xl shadow-lg shadow-blue-500/30">H</div>
                    <h2 class="text-xl font-bold text-slate-800">Admin Sign In</h2>
                    <p class="text-xs text-slate-500">Enter Super Admin ID to unlock portal</p>
                </div>
                <form id="adminLoginForm" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Admin ID</label>
                        <input type="text" id="adminIdInput" value="ADMIN" placeholder="e.g. ADMIN" required class="w-full border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Password</label>
                        <input type="password" id="adminPassInput" value="password123" required class="w-full border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg text-sm transition shadow-sm">Authenticate</button>
                </form>
            </div>
        </div>

        <!-- Main Workspace (Hidden until Auth) -->
        <div id="adminWorkspace" class="hidden min-h-screen flex flex-col">
            <!-- Navigation Header -->
            <header class="bg-white border-b border-slate-200 sticky top-0 z-30">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold text-lg shadow-sm">H</div>
                        <div>
                            <h1 class="text-base font-bold text-slate-800 leading-tight">HRIS Portal</h1>
                            <p class="text-xs text-slate-500">Super Admin Workspace</p>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-3">
                        <a href="/api/admin/export/csv" class="inline-flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition shadow-sm">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=" "></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                            Export CSV
                        </a>
                        <button onclick="logoutAdmin()" class="text-slate-400 hover:text-slate-600 p-2 rounded-lg transition">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
                        </button>
                    </div>
                </div>
            </header>

            <!-- Dashboard Content -->
            <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

                <!-- Manual Insertion Card -->
                <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm space-y-4">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                        <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider">Manual DTR Entry</h2>
                        <span class="text-xs bg-blue-50 text-blue-700 font-semibold px-2.5 py-1 rounded-full">RBAC Override</span>
                    </div>
                    
                    <form id="addForm" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        <div>
                            <label class="block text-xs font-semibold text-slate-500 mb-1">Employee ID</label>
                            <input type="text" id="addEmpId" placeholder="e.g. 3286" required class="w-full border border-slate-200 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                        </div>

                        <div>
                            <label class="block text-xs font-semibold text-slate-500 mb-1">Punch Type</label>
                            <select id="addType" class="w-full border border-slate-200 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                                <option value="CLOCK_IN">CLOCK_IN</option>
                                <option value="CLOCK_OUT">CLOCK_OUT</option>
                            </select>
                        </div>

                        <div>
                            <label class="block text-xs font-semibold text-slate-500 mb-1">Date & Time</label>
                            <input type="datetime-local" id="addTime" required class="w-full border border-slate-200 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                        </div>

                        <div class="flex items-end">
                            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg text-sm transition shadow-sm">
                                Create Entry
                            </button>
                        </div>
                    </form>
                </div>

                <!-- Audit Log Table Card -->
                <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                    <div class="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
                        <div>
                            <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider">DTR Audit Records</h2>
                            <p class="text-xs text-slate-500">Live attendance database logs</p>
                        </div>
                        <button onclick="loadPunches()" class="inline-flex items-center gap-1 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg transition">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                            Refresh
                        </button>
                    </div>

                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm">
                            <thead>
                                <tr class="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs font-bold uppercase tracking-wider">
                                    <th class="p-3.5 pl-5">ID</th>
                                    <th class="p-3.5">Employee</th>
                                    <th class="p-3.5">Type</th>
                                    <th class="p-3.5">Timestamp</th>
                                    <th class="p-3.5">Location</th>
                                    <th class="p-3.5 pr-5 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="dtrTableBody" class="divide-y divide-slate-100">
                                <tr><td colspan="6" class="p-6 text-center text-slate-400 text-xs">Loading audit records...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

            </main>
        </div>

        <script>
            const API_BASE = "/api";

            // Initialize Form Date Default
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            document.getElementById('addTime').value = now.toISOString().slice(0, 16);

            document.getElementById("adminLoginForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const empId = document.getElementById("adminIdInput").value;
                const pass = document.getElementById("adminPassInput").value;

                try {
                    const res = await fetch(`${API_BASE}/login`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ employee_id: empId, password: pass })
                    });

                    if (res.ok) {
                        const data = await res.json();
                        if (data.role === "super_admin") {
                            document.getElementById("loginOverlay").classList.add("hidden");
                            document.getElementById("adminWorkspace").classList.remove("hidden");
                            loadPunches();
                        } else {
                            alert("Access Denied: Super Admin permissions required.");
                        }
                    } else {
                        alert("Invalid Administrator Credentials");
                    }
                } catch (err) {
                    alert("Unable to connect to HRIS Backend Server.");
                }
            });

            function logoutAdmin() {
                document.getElementById("adminWorkspace").classList.add("hidden");
                document.getElementById("loginOverlay").classList.remove("hidden");
            }

            async function loadPunches() {
                try {
                    const res = await fetch(`${API_BASE}/admin/dtr`);
                    const data = await res.json();
                    const tbody = document.getElementById("dtrTableBody");
                    tbody.innerHTML = "";

                    if (data.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400 text-xs">No attendance records found.</td></tr>`;
                        return;
                    }

                    data.forEach(p => {
                        const row = document.createElement("tr");
                        row.className = "hover:bg-slate-50/80 transition";
                        const isClockIn = p.punch_type === 'CLOCK_IN';

                        row.innerHTML = `
                            <td class="p-3.5 pl-5 font-mono text-xs text-slate-400">#${p.id}</td>
                            <td class="p-3.5 font-bold text-slate-800">${p.employee_id}</td>
                            <td class="p-3.5">
                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${isClockIn ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}">
                                    ${p.punch_type}
                                </span>
                            </td>
                            <td class="p-3.5 text-xs font-semibold text-slate-700 font-mono">${p.formatted_time}</td>
                            <td class="p-3.5 text-xs text-slate-500">${p.address}</td>
                            <td class="p-3.5 pr-5 text-right">
                                <button onclick="deletePunch(${p.id})" class="text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-600 border border-rose-200 px-2.5 py-1 rounded-md transition">
                                    Delete
                                </button>
                            </td>
                        `;
                        tbody.appendChild(row);
                    });
                } catch (err) {
                    console.log("Error loading punches:", err);
                }
            }

            document.getElementById("addForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const empId = document.getElementById("addEmpId").value;
                const type = document.getElementById("addType").value;
                const timeVal = document.getElementById("addTime").value;

                await fetch(`${API_BASE}/admin/dtr`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        employee_id: empId,
                        punch_type: type,
                        timestamp: timeVal + ":00",
                        address: "Manual Admin Entry"
                    })
                });
                loadPunches();
            });

            async function deletePunch(id) {
                if (confirm(`Delete DTR Entry #${id}?`)) {
                    await fetch(`${API_BASE}/admin/dtr/${id}`, { method: "DELETE" });
                    loadPunches();
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
