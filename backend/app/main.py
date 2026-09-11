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
from typing import Optional, List
from collections import defaultdict
from . import models

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hrisuser:hrispassword@hris-db:5432/hrisdb")
MANILA_TZ = ZoneInfo("Asia/Manila")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS Enterprise API", version="4.0.0")

MAX_SHIFT_SECONDS = 20 * 3600

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_now_manila():
    return datetime.now(MANILA_TZ)

# --- Schemas ---
class LoginRequest(BaseModel):
    employee_id: str
    password: str

class UserCreateRequest(BaseModel):
    employee_id: str
    name: str
    department: str
    position: str
    role: str
    password: str

class UserUpdateRequest(BaseModel):
    new_employee_id: Optional[str] = None
    name: str
    department: str
    position: str
    role: str
    password: Optional[str] = None

class PunchRequest(BaseModel):
    employee_id: str
    punch_type: str
    latitude: float
    longitude: float
    accuracy: float
    address: Optional[str] = None

class ShiftEditSubmitRequest(BaseModel):
    employee_id: str
    requested_punch_type: str
    requested_timestamp: str
    reason: str

class CreatePunchAdminRequest(BaseModel):
    employee_id: str
    punch_type: str
    timestamp: str
    latitude: float = 14.5764
    longitude: float = 121.0851
    address: Optional[str] = "Pasig, Metro Manila"

# --- Health Check ---
@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "online", "service": "HRIS FastAPI Backend", "version": "4.0.0"}

@app.get("/api/departments")
def get_departments(db: Session = Depends(get_db)):
    db_depts = db.query(models.User.department).distinct().all()
    dept_list = [d[0] for d in db_depts if d[0]]
    defaults = ["Admin", "IT Operations", "Executive", "Operations", "Sales"]
    for d in defaults:
        if d not in dept_list:
            dept_list.append(d)
    return sorted(dept_list)

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == req.employee_id).first()
    if not user and req.employee_id.upper() in ["ADMIN", "SUPERADMIN", "SA-001"]:
        user = models.User(
            employee_id=req.employee_id.upper(),
            name="System Administrator",
            department="Executive",
            position="Super Admin",
            role="super_admin",
            hashed_password="password123"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user or user.hashed_password != req.password:
        raise HTTPException(status_code=401, detail="Invalid Employee ID or Password")

    return {
        "employee_id": user.employee_id,
        "name": user.name,
        "department": user.department,
        "position": user.position,
        "role": user.role,
        "token": f"hris-session-{user.employee_id}"
    }

# --- User Management API ---
@app.get("/api/admin/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.department.asc(), models.User.name.asc()).all()

@app.post("/api/admin/users")
def create_user(req: UserCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.employee_id == req.employee_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID already exists")

    user = models.User(
        employee_id=req.employee_id,
        name=req.name,
        department=req.department,
        position=req.position,
        role=req.role,
        hashed_password=req.password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "created", "user": user}

@app.put("/api/admin/users/{employee_id}")
def update_user(employee_id: str, req: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.new_employee_id and req.new_employee_id != employee_id:
        existing = db.query(models.User).filter(models.User.employee_id == req.new_employee_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="New Employee ID already exists")
        user.employee_id = req.new_employee_id

    user.name = req.name
    user.department = req.department
    user.position = req.position
    user.role = req.role
    if req.password:
        user.hashed_password = req.password

    db.commit()
    db.refresh(user)
    return {"status": "updated", "user": user}

@app.delete("/api/admin/users/{employee_id}")
def delete_user(employee_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"status": "deleted", "employee_id": employee_id}

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
        address=req.address or "Captured Location",
        timestamp=get_now_manila().replace(tzinfo=None)
    )
    db.add(punch)
    db.commit()
    db.refresh(punch)
    return {"status": "success", "punch_id": punch.id, "timestamp": punch.timestamp.isoformat()}

# --- Shift Edit Requests API (Approval Workflow) ---
@app.post("/api/shift-request")
def submit_shift_request(req: ShiftEditSubmitRequest, db: Session = Depends(get_db)):
    try:
        ts = datetime.fromisoformat(req.requested_timestamp).replace(tzinfo=None)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ISO timestamp format")

    edit_req = models.ShiftEditRequest(
        employee_id=req.employee_id,
        requested_punch_type=req.requested_punch_type,
        requested_timestamp=ts,
        reason=req.reason,
        status="PENDING"
    )
    db.add(edit_req)
    db.commit()
    return {"status": "submitted", "request_id": edit_req.id}

@app.get("/api/admin/shift-requests")
def list_shift_requests(db: Session = Depends(get_db)):
    reqs = db.query(models.ShiftEditRequest).order_by(desc(models.ShiftEditRequest.created_at)).all()
    result = []
    for r in reqs:
        u = db.query(models.User).filter(models.User.employee_id == r.employee_id).first()
        result.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "employee_name": u.name if u else f"Emp #{r.employee_id}",
            "department": u.department if u else "General",
            "requested_punch_type": r.requested_punch_type,
            "requested_timestamp": r.requested_timestamp.strftime("%Y-%m-%d %I:%M %p"),
            "reason": r.reason,
            "status": r.status
        })
    return result

@app.post("/api/admin/shift-requests/{request_id}/approve")
def approve_shift_request(request_id: int, db: Session = Depends(get_db)):
    req = db.query(models.ShiftEditRequest).filter(models.ShiftEditRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "APPROVED"
    # Insert official punch record
    punch = models.TimePunch(
        employee_id=req.employee_id,
        punch_type=req.requested_punch_type,
        timestamp=req.requested_timestamp,
        latitude=14.5764,
        longitude=121.0851,
        address=f"Approved Shift Edit: {req.reason}"
    )
    db.add(punch)
    db.commit()
    return {"status": "approved", "request_id": request_id}

@app.post("/api/admin/shift-requests/{request_id}/reject")
def reject_shift_request(request_id: int, db: Session = Depends(get_db)):
    req = db.query(models.ShiftEditRequest).filter(models.ShiftEditRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "REJECTED"
    db.commit()
    return {"status": "rejected", "request_id": request_id}

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

# --- DTR Audit & Export ---
@app.get("/api/admin/dtr")
def list_all_dtr(employee_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.TimePunch)
    if employee_id:
        query = query.filter(models.TimePunch.employee_id == employee_id)
    punches = query.order_by(desc(models.TimePunch.timestamp)).all()
    
    result = []
    for p in punches:
        user = db.query(models.User).filter(models.User.employee_id == p.employee_id).first()
        result.append({
            "id": p.id,
            "employee_id": p.employee_id,
            "employee_name": user.name if user else f"Emp #{p.employee_id}",
            "department": user.department if user else "General",
            "position": user.position if user else "Staff",
            "punch_type": p.punch_type,
            "formatted_time": p.timestamp.strftime("%Y-%m-%d %I:%M:%S %p"),
            "address": p.address or f"Lat: {p.latitude:.4f}, Lng: {p.longitude:.4f}",
            "latitude": p.latitude or 14.5764,
            "longitude": p.longitude or 121.0851
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

# --- WEB EMPLOYEE PORTAL UI (WITH REVIEW MODAL & SHIFT EDIT) ---
@app.get("/", response_class=HTMLResponse)
@app.get("/portal", response_class=HTMLResponse)
def employee_portal_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HRIS Employee Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style> body { font-family: 'Inter', sans-serif; } #reviewMap { height: 180px; width: 100%; border-radius: 0.5rem; } </style>
    </head>
    <body class="bg-slate-50 text-slate-900 min-h-screen antialiased flex flex-col justify-between">

        <div id="employeeLoginCard" class="min-h-screen flex items-center justify-center p-4">
            <div class="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-sm w-full p-6 space-y-5">
                <div class="text-center space-y-1">
                    <div class="w-12 h-12 bg-blue-600 text-white rounded-xl mx-auto flex items-center justify-center font-bold text-xl shadow-lg shadow-blue-500/30">H</div>
                    <h2 class="text-xl font-bold text-slate-800">HRIS Employee Portal</h2>
                    <p class="text-xs text-slate-500">Sign in to record your attendance</p>
                </div>
                <form id="empLoginForm" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Employee ID</label>
                        <input type="text" id="loginEmpId" placeholder="e.g. 3286" required class="w-full border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Department</label>
                        <select id="loginDept" class="deptDropdownSelect w-full border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"></select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Password</label>
                        <input type="password" id="loginPass" placeholder="••••••••" required class="w-full border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg text-sm transition shadow-sm">
                        Sign In
                    </button>
                </form>
            </div>
        </div>

        <!-- DTR PUNCH REVIEW MODAL -->
        <div id="punchReviewModal" class="hidden fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-sm w-full p-5 space-y-4">
                <div class="flex justify-between items-center border-b pb-2">
                    <h3 class="font-bold text-slate-800 text-sm">Review DTR Punch Location</h3>
                    <button onclick="closeReviewModal()" class="text-slate-400 hover:text-slate-600 text-lg font-bold">&times;</button>
                </div>

                <div id="reviewMap"></div>

                <div class="space-y-1.5 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <p><b>Action:</b> <span id="revActionText" class="font-bold"></span></p>
                    <p><b>Address:</b> <span id="revAddressText"></span></p>
                    <p><b>Coordinates:</b> <span id="revCoordsText" class="font-mono"></span></p>
                </div>

                <div class="grid grid-cols-2 gap-2 pt-2">
                    <button onclick="openShiftEditModal()" class="w-full py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition">
                        Edit Shift
                    </button>
                    <button onclick="confirmPunchAction()" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs shadow-md transition">
                        Confirm Punch
                    </button>
                </div>
            </div>
        </div>

        <!-- SHIFT EDIT APPROVAL MODAL -->
        <div id="shiftEditModal" class="hidden fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-sm w-full p-5 space-y-4">
                <div class="flex justify-between items-center border-b pb-2">
                    <h3 class="font-bold text-slate-800 text-sm">Submit Shift Edit Request</h3>
                    <button onclick="closeShiftEditModal()" class="text-slate-400 hover:text-slate-600 text-lg font-bold">&times;</button>
                </div>

                <form id="shiftEditForm" class="space-y-3 text-xs">
                    <div>
                        <label class="block font-semibold text-slate-600 mb-1">Requested Time</label>
                        <input type="datetime-local" id="reqTime" required class="w-full border p-2 rounded-lg">
                    </div>
                    <div>
                        <label class="block font-semibold text-slate-600 mb-1">Reason for Manager Approval</label>
                        <textarea id="reqReason" rows="3" placeholder="Forgot to punch, field work, etc." required class="w-full border p-2 rounded-lg"></textarea>
                    </div>
                    <div class="flex justify-end gap-2 pt-2">
                        <button type="button" onclick="closeShiftEditModal()" class="px-3 py-2 bg-slate-100 rounded-lg font-semibold">Cancel</button>
                        <button type="submit" class="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg">Send Request</button>
                    </div>
                </form>
            </div>
        </div>

        <div id="employeeWorkspace" class="hidden min-h-screen flex flex-col">
            <header class="bg-white border-b border-slate-200 sticky top-0 z-30">
                <div class="max-w-md mx-auto px-4 h-16 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold text-base shadow-sm">H</div>
                        <div>
                            <h1 id="userDisplayName" class="text-sm font-bold text-slate-800 leading-tight">Employee Workspace</h1>
                            <p id="userDeptTitle" class="text-[11px] text-slate-500">Active Session</p>
                        </div>
                    </div>
                    <button onclick="logoutEmployee()" class="text-xs text-slate-400 hover:text-slate-600 font-semibold transition">Sign Out</button>
                </div>
            </header>

            <main class="flex-1 max-w-md w-full mx-auto px-4 py-6 space-y-6">
                <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 text-center space-y-5">
                    <div>
                        <span id="statusBadge" class="inline-block px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600">OFF DUTY</span>
                        <h2 id="liveTimerText" class="text-3xl font-extrabold text-slate-800 font-mono mt-3">00:00:00</h2>
                        <p id="shiftSubText" class="text-xs text-slate-500 mt-1">Ready to start shift</p>
                    </div>

                    <button id="punchActionBtn" onclick="initiatePunchReview()" class="w-full py-4 rounded-xl font-bold text-base text-white bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/25 transition">
                        CLOCK IN NOW
                    </button>

                    <p id="geoStatusText" class="text-[11px] text-slate-400">GPS location verification enabled</p>
                </div>

                <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-3">
                    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Today's Activity Log</h3>
                    <div id="timesheetLogContainer" class="space-y-2 text-xs divide-y divide-slate-100"></div>
                </div>
            </main>
        </div>

        <script>
            const API_BASE = "/api";
            let currentUser = null;
            let activeTimerInterval = null;
            let autoSyncPoller = null;
            let currentIsClockedIn = false;
            let elapsedShiftSeconds = 0;
            let currentLat = 14.5764;
            let currentLng = 121.0851;
            let reviewMapInstance = null;

            async function requestHardwareGPS() {
                if ("geolocation" in navigator) {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => {
                            currentLat = pos.coords.latitude;
                            currentLng = pos.coords.longitude;
                            document.getElementById("geoStatusText").innerText = `High-Accuracy GPS: ${currentLat.toFixed(5)}, ${currentLng.toFixed(5)} (±${Math.round(pos.coords.accuracy)}m)`;
                        },
                        (err) => {
                            document.getElementById("geoStatusText").innerText = "HTTP Unsecure Context: Coarse Location";
                        },
                        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                    );
                }
            }

            async function initPortal() {
                try {
                    const res = await fetch(`${API_BASE}/departments`);
                    const depts = await res.json();
                    const sel = document.getElementById("loginDept");
                    sel.innerHTML = "";
                    depts.forEach(d => {
                        sel.innerHTML += `<option value="${d}">${d}</option>`;
                    });
                } catch(e) {}

                const savedEmpId = localStorage.getItem("hris_emp_id");
                if (savedEmpId) document.getElementById("loginEmpId").value = savedEmpId;
                requestHardwareGPS();
            }

            document.getElementById("empLoginForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const empId = document.getElementById("loginEmpId").value;
                const pass = document.getElementById("loginPass").value;

                try {
                    const res = await fetch(`${API_BASE}/login`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ employee_id: empId, password: pass })
                    });

                    if (res.ok) {
                        currentUser = await res.json();
                        localStorage.setItem("hris_emp_id", currentUser.employee_id);
                        document.getElementById("employeeLoginCard").classList.add("hidden");
                        document.getElementById("employeeWorkspace").classList.remove("hidden");
                        document.getElementById("userDisplayName").innerText = currentUser.name;
                        document.getElementById("userDeptTitle").innerText = `${currentUser.department} • ${currentUser.position}`;
                        
                        await loadActiveStatus();
                        await loadTimesheet();

                        clearInterval(autoSyncPoller);
                        autoSyncPoller = setInterval(loadActiveStatus, 3000);
                    } else {
                        alert("Invalid Employee ID or Password");
                    }
                } catch (err) {
                    alert("Unable to reach HRIS server");
                }
            });

            function logoutEmployee() {
                clearInterval(activeTimerInterval);
                clearInterval(autoSyncPoller);
                currentUser = null;
                document.getElementById("employeeWorkspace").classList.add("hidden");
                document.getElementById("employeeLoginCard").classList.remove("hidden");
            }

            async function initiatePunchReview() {
                await requestHardwareGPS();
                const punchType = currentIsClockedIn ? "CLOCK_OUT" : "CLOCK_IN";
                
                document.getElementById("revActionText").innerText = punchType;
                document.getElementById("revActionText").className = punchType === 'CLOCK_IN' ? 'font-bold text-emerald-600' : 'font-bold text-rose-600';
                document.getElementById("revAddressText").innerText = "Pasig, Metro Manila";
                document.getElementById("revCoordsText").innerText = `${currentLat.toFixed(5)}, ${currentLng.toFixed(5)}`;

                document.getElementById("punchReviewModal").classList.remove("hidden");

                setTimeout(() => {
                    if (!reviewMapInstance) {
                        reviewMapInstance = L.map('reviewMap').setView([currentLat, currentLng], 14);
                        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(reviewMapInstance);
                    } else {
                        reviewMapInstance.setView([currentLat, currentLng], 14);
                    }
                    L.marker([currentLat, currentLng]).addTo(reviewMapInstance);
                    reviewMapInstance.invalidateSize();
                }, 200);
            }

            function closeReviewModal() {
                document.getElementById("punchReviewModal").classList.add("hidden");
            }

            async function confirmPunchAction() {
                closeReviewModal();
                const punchType = currentIsClockedIn ? "CLOCK_OUT" : "CLOCK_IN";

                const res = await fetch(`${API_BASE}/punch`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        employee_id: currentUser.employee_id,
                        punch_type: punchType,
                        latitude: currentLat,
                        longitude: currentLng,
                        accuracy: 10.0,
                        address: "Pasig, Metro Manila"
                    })
                });

                if (res.ok) {
                    await loadActiveStatus();
                    await loadTimesheet();
                } else {
                    alert("Failed to submit punch");
                }
            }

            function openShiftEditModal() {
                closeReviewModal();
                const now = new Date();
                now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
                document.getElementById('reqTime').value = now.toISOString().slice(0, 16);
                document.getElementById("shiftEditModal").classList.remove("hidden");
            }

            function closeShiftEditModal() {
                document.getElementById("shiftEditModal").classList.add("hidden");
            }

            document.getElementById("shiftEditForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const punchType = currentIsClockedIn ? "CLOCK_OUT" : "CLOCK_IN";
                const reqTime = document.getElementById("reqTime").value + ":00";
                const reason = document.getElementById("reqReason").value;

                const res = await fetch(`${API_BASE}/shift-request`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        employee_id: currentUser.employee_id,
                        requested_punch_type: punchType,
                        requested_timestamp: reqTime,
                        reason: reason
                    })
                });

                if (res.ok) {
                    closeShiftEditModal();
                    alert("Shift edit request sent for Manager approval!");
                } else {
                    alert("Failed to submit shift edit request");
                }
            });

            async function loadActiveStatus() {
                if (!currentUser) return;
                try {
                    const res = await fetch(`${API_BASE}/punch/active/${currentUser.employee_id}`);
                    const data = await res.json();
                    
                    const badge = document.getElementById("statusBadge");
                    const btn = document.getElementById("punchActionBtn");
                    const subText = document.getElementById("shiftSubText");

                    if (data.is_clocked_in) {
                        if (!currentIsClockedIn) {
                            currentIsClockedIn = true;
                            loadTimesheet();
                        }
                        badge.innerText = "ON DUTY";
                        badge.className = "inline-block px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800";
                        btn.innerText = "CLOCK OUT NOW";
                        btn.className = "w-full py-4 rounded-xl font-bold text-base text-white bg-rose-600 hover:bg-rose-700 shadow-lg shadow-rose-500/25 transition";
                        subText.innerText = "Active shift running";
                        
                        elapsedShiftSeconds = data.elapsed_seconds || 0;
                        if (!activeTimerInterval) {
                            activeTimerInterval = setInterval(() => {
                                elapsedShiftSeconds++;
                                updateTimerDisplay(elapsedShiftSeconds);
                            }, 1000);
                        }
                    } else {
                        if (currentIsClockedIn) {
                            currentIsClockedIn = false;
                            loadTimesheet();
                        }
                        badge.innerText = "OFF DUTY";
                        badge.className = "inline-block px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600";
                        btn.innerText = "CLOCK IN NOW";
                        btn.className = "w-full py-4 rounded-xl font-bold text-base text-white bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/25 transition";
                        document.getElementById("liveTimerText").innerText = "00:00:00";
                        subText.innerText = "Ready to start shift";
                        clearInterval(activeTimerInterval);
                        activeTimerInterval = null;
                    }
                } catch(e) {}
            }

            function updateTimerDisplay(seconds) {
                const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
                const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
                const s = String(seconds % 60).padStart(2, '0');
                document.getElementById("liveTimerText").innerText = `${h}:${m}:${s}`;
            }

            async function loadTimesheet() {
                if (!currentUser) return;
                try {
                    const res = await fetch(`${API_BASE}/timesheet/${currentUser.employee_id}`);
                    const data = await res.json();
                    const container = document.getElementById("timesheetLogContainer");
                    container.innerHTML = "";

                    if (!data.all_punches || data.all_punches.length === 0) {
                        container.innerHTML = `<p class="text-slate-400 text-center py-2">No punches recorded today</p>`;
                        return;
                    }

                    data.all_punches.slice(0, 5).forEach(p => {
                        const isIn = p.punch_type === 'CLOCK_IN';
                        container.innerHTML += `
                            <div class="pt-2 flex justify-between items-center">
                                <div>
                                    <span class="font-bold ${isIn ? 'text-emerald-700' : 'text-rose-700'}">${p.punch_type}</span>
                                    <p class="text-[10px] text-slate-400">${p.address}</p>
                                </div>
                                <span class="font-mono text-slate-600 font-bold">${p.time}</span>
                            </div>
                        `;
                    });
                } catch(e) {}
            }

            initPortal();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# --- WEB ADMIN PORTAL UI (WITH MANAGER SHIFT APPROVAL TAB) ---
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
        
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

        <style> body { font-family: 'Inter', sans-serif; } #map { height: 420px; width: 100%; border-radius: 0.75rem; z-index: 10; } </style>
    </head>
    <body class="bg-slate-50 text-slate-900 min-h-screen antialiased">

        <div id="loginOverlay" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-sm w-full p-6 space-y-5">
                <div class="text-center space-y-1">
                    <div class="w-12 h-12 bg-blue-600 text-white rounded-xl mx-auto flex items-center justify-center font-bold text-xl shadow-lg shadow-blue-500/30">H</div>
                    <h2 class="text-xl font-bold text-slate-800">Admin Sign In</h2>
                    <p class="text-xs text-slate-500">Super Admin credentials required</p>
                </div>
                <form id="adminLoginForm" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Employee / Admin ID</label>
                        <input type="text" id="adminIdInput" value="ADMIN" required class="w-full border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Password</label>
                        <input type="password" id="adminPassInput" value="password123" required class="w-full border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg text-sm transition shadow-sm">Authenticate</button>
                </form>
            </div>
        </div>

        <div id="adminWorkspace" class="hidden min-h-screen flex flex-col">
            <header class="bg-white border-b border-slate-200 sticky top-0 z-30">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div class="flex items-center gap-6">
                        <div class="flex items-center gap-3">
                            <div class="w-9 h-9 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold text-lg shadow-sm">H</div>
                            <div>
                                <h1 class="text-base font-bold text-slate-800 leading-tight">HRIS Portal</h1>
                                <p class="text-xs text-slate-500">Super Admin Workspace</p>
                            </div>
                        </div>

                        <nav class="hidden md:flex gap-1 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                            <button id="tabBtnClocks" onclick="switchTab('clocks')" class="px-3 py-1.5 rounded-md bg-white text-blue-600 shadow-sm transition">Time Clocks & Map</button>
                            <button id="tabBtnRequests" onclick="switchTab('requests')" class="px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition">Shift Edit Requests</button>
                            <button id="tabBtnUsers" onclick="switchTab('users')" class="px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition">User Directory & RBAC</button>
                        </nav>
                    </div>
                    
                    <div class="flex items-center gap-3">
                        <a href="/api/admin/export/csv" class="inline-flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition shadow-sm">
                            Export CSV
                        </a>
                        <button onclick="logoutAdmin()" class="text-slate-400 hover:text-slate-600 p-2 rounded-lg text-xs font-semibold transition">Sign Out</button>
                    </div>
                </div>
            </header>

            <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

                <div id="tabContentClocks" class="space-y-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex items-center justify-between">
                            <div>
                                <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Clocked In Now</p>
                                <h3 id="statClockedInCount" class="text-2xl font-bold text-slate-800 mt-1">0</h3>
                            </div>
                            <div class="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center font-bold">✓</div>
                        </div>

                        <div class="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex items-center justify-between">
                            <div>
                                <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Active Users</p>
                                <h3 id="statTotalUsersCount" class="text-2xl font-bold text-slate-800 mt-1">0</h3>
                            </div>
                            <div class="w-10 h-10 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center font-bold">👥</div>
                        </div>
                    </div>

                    <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-3">
                            <div>
                                <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider">Live Geo-Location GPS Tracker</h2>
                                <p class="text-xs text-slate-500">Real-time GPS punch locations mapped across Metro Manila</p>
                            </div>
                            <button onclick="loadDashboard()" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-3 py-1.5 rounded-lg transition">Refresh Map Pins</button>
                        </div>

                        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
                            <div class="lg:col-span-1 bg-slate-50 p-3 rounded-xl border border-slate-200/60 max-h-[420px] overflow-y-auto space-y-2">
                                <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Active Punch Locations</h3>
                                <div id="mapUserList" class="space-y-1.5"></div>
                            </div>

                            <div class="lg:col-span-3">
                                <div id="map"></div>
                            </div>
                        </div>
                    </div>

                    <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                        <div class="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
                            <div>
                                <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider">DTR Audit Logs</h2>
                                <p class="text-xs text-slate-500">Raw timestamp records from PostgreSQL</p>
                            </div>
                            <button onclick="loadPunches()" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-3 py-1.5 rounded-lg transition">Refresh</button>
                        </div>

                        <div id="auditTableBody" class="overflow-x-auto">
                            <table class="w-full text-left text-sm">
                                <thead>
                                    <tr class="bg-slate-50 border-b text-slate-500 text-xs font-bold uppercase tracking-wider">
                                        <th class="p-3.5 pl-5">ID</th>
                                        <th class="p-3.5">Employee</th>
                                        <th class="p-3.5">Type</th>
                                        <th class="p-3.5">Timestamp</th>
                                        <th class="p-3.5">Location</th>
                                        <th class="p-3.5 pr-5 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="dtrTableBody" class="divide-y divide-slate-100"></tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- TAB 2: Shift Requests Manager Approvals -->
                <div id="tabContentRequests" class="hidden space-y-6">
                    <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
                            <div>
                                <h2 class="text-base font-bold text-slate-800">Pending Shift Edit Requests</h2>
                                <p class="text-xs text-slate-500">Approve or reject employee shift adjustments and manual DTR corrections</p>
                            </div>
                            <button onclick="loadShiftRequests()" class="text-xs bg-slate-100 hover:bg-slate-200 font-semibold px-3 py-1.5 rounded-lg">Refresh Requests</button>
                        </div>

                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-xs">
                                <thead>
                                    <tr class="bg-slate-50 text-slate-500 font-bold border-b">
                                        <th class="p-3.5">ID</th>
                                        <th class="p-3.5">Employee</th>
                                        <th class="p-3.5">Type</th>
                                        <th class="p-3.5">Requested Time</th>
                                        <th class="p-3.5">Reason</th>
                                        <th class="p-3.5">Status</th>
                                        <th class="p-3.5 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="requestsTableBody" class="divide-y divide-slate-100"></tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- TAB 3: User Directory -->
                <div id="tabContentUsers" class="hidden space-y-6">
                    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                        <div>
                            <h2 class="text-base font-bold text-slate-800">User Directory & Permissions</h2>
                            <p class="text-xs text-slate-500">Manage employee accounts, titles, and system RBAC access levels</p>
                        </div>
                    </div>
                    <div id="departmentDirectoryContainer" class="space-y-4"></div>
                </div>

            </main>
        </div>

        <script>
            const API_BASE = "/api";
            let leafletMap = null;
            let mapMarkers = [];
            let adminSyncPoller = null;

            function initLeafletMap() {
                if (leafletMap) return;
                leafletMap = L.map('map').setView([14.5764, 121.0851], 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(leafletMap);
            }

            function switchTab(tabName) {
                const clockTab = document.getElementById("tabContentClocks");
                const reqTab = document.getElementById("tabContentRequests");
                const userTab = document.getElementById("tabContentUsers");

                clockTab.classList.add("hidden");
                reqTab.classList.add("hidden");
                userTab.classList.add("hidden");

                if (tabName === 'clocks') {
                    clockTab.classList.remove("hidden");
                    if (leafletMap) leafletMap.invalidateSize();
                } else if (tabName === 'requests') {
                    reqTab.classList.remove("hidden");
                    loadShiftRequests();
                } else if (tabName === 'users') {
                    userTab.classList.remove("hidden");
                }
            }

            document.getElementById("adminLoginForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const empId = document.getElementById("adminIdInput").value;
                const pass = document.getElementById("adminPassInput").value;

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
                        initLeafletMap();
                        await loadDashboard();

                        clearInterval(adminSyncPoller);
                        adminSyncPoller = setInterval(loadPunches, 3000);
                    }
                }
            });

            function logoutAdmin() {
                clearInterval(adminSyncPoller);
                document.getElementById("adminWorkspace").classList.add("hidden");
                document.getElementById("loginOverlay").classList.remove("hidden");
            }

            async function loadDashboard() {
                await loadPunches();
                await loadShiftRequests();
            }

            async function loadPunches() {
                try {
                    const res = await fetch(`${API_BASE}/admin/dtr`);
                    const data = await res.json();
                    
                    const tbody = document.getElementById("dtrTableBody");
                    const mapUserList = document.getElementById("mapUserList");
                    tbody.innerHTML = "";
                    mapUserList.innerHTML = "";

                    mapMarkers.forEach(m => leafletMap.removeLayer(m));
                    mapMarkers = [];

                    let activeClockedInCount = 0;
                    const seenUsers = new Set();

                    data.forEach(p => {
                        const isClockIn = p.punch_type === 'CLOCK_IN';
                        if (!seenUsers.has(p.employee_id)) {
                            seenUsers.add(p.employee_id);
                            if (isClockIn) activeClockedInCount++;
                        }

                        tbody.innerHTML += `
                            <tr class="hover:bg-slate-50 transition">
                                <td class="p-3.5 pl-5 font-mono text-xs text-slate-400">#${p.id}</td>
                                <td class="p-3.5 font-bold text-slate-800">${p.employee_name} (${p.employee_id})</td>
                                <td class="p-3.5">
                                    <span class="px-2.5 py-0.5 rounded-full text-xs font-bold ${isClockIn ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}">
                                        ${p.punch_type}
                                    </span>
                                </td>
                                <td class="p-3.5 text-xs font-mono font-semibold text-slate-700">${p.formatted_time}</td>
                                <td class="p-3.5 text-xs text-slate-500">${p.address}</td>
                                <td class="p-3.5 pr-5 text-right">
                                    <button onclick="deletePunch(${p.id})" class="text-xs text-rose-600 hover:underline font-semibold">Delete</button>
                                </td>
                            </tr>
                        `;

                        const lat = parseFloat(p.latitude) || 14.5764;
                        const lng = parseFloat(p.longitude) || 121.0851;

                        if (leafletMap) {
                            const marker = L.marker([lat, lng]).addTo(leafletMap);
                            mapMarkers.push(marker);
                        }
                    });

                    document.getElementById("statClockedInCount").innerText = activeClockedInCount;
                } catch(e) {}
            }

            async function loadShiftRequests() {
                try {
                    const res = await fetch(`${API_BASE}/admin/shift-requests`);
                    const requests = await res.json();
                    const tbody = document.getElementById("requestsTableBody");
                    tbody.innerHTML = "";

                    requests.forEach(r => {
                        const isPending = r.status === 'PENDING';
                        tbody.innerHTML += `
                            <tr class="hover:bg-slate-50 transition">
                                <td class="p-3.5 font-mono text-slate-400">#${r.id}</td>
                                <td class="p-3.5 font-bold text-slate-800">${r.employee_name} (${r.employee_id})</td>
                                <td class="p-3.5 font-bold">${r.requested_punch_type}</td>
                                <td class="p-3.5 font-mono">${r.requested_timestamp}</td>
                                <td class="p-3.5 text-slate-600">${r.reason}</td>
                                <td class="p-3.5">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${r.status === 'APPROVED' ? 'bg-emerald-100 text-emerald-800' : r.status === 'REJECTED' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}">${r.status}</span>
                                </td>
                                <td class="p-3.5 text-right space-x-2">
                                    ${isPending ? `
                                        <button onclick="approveRequest(${r.id})" class="px-2.5 py-1 bg-emerald-600 text-white rounded font-semibold text-xs hover:bg-emerald-700">Approve</button>
                                        <button onclick="rejectRequest(${r.id})" class="px-2.5 py-1 bg-rose-600 text-white rounded font-semibold text-xs hover:bg-rose-700">Reject</button>
                                    ` : '<span class="text-slate-400">Processed</span>'}
                                </td>
                            </tr>
                        `;
                    });
                } catch(e) {}
            }

            async function approveRequest(id) {
                if (confirm(`Approve shift edit request #${id}?`)) {
                    await fetch(`${API_BASE}/admin/shift-requests/${id}/approve`, { method: "POST" });
                    loadShiftRequests();
                    loadPunches();
                }
            }

            async function rejectRequest(id) {
                if (confirm(`Reject shift edit request #${id}?`)) {
                    await fetch(`${API_BASE}/admin/shift-requests/${id}/reject`, { method: "POST" });
                    loadShiftRequests();
                }
            }

            async function deletePunch(id) {
                if (confirm(`Delete DTR entry #${id}?`)) {
                    await fetch(`${API_BASE}/admin/dtr/${id}`, { method: "DELETE" });
                    loadPunches();
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
