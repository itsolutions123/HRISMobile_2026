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

app = FastAPI(title="HRIS Enterprise API", version="3.6.0")

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
    return {"status": "online", "service": "HRIS FastAPI Backend", "version": "3.6.0"}

# --- Dynamic Departments Endpoint ---
@app.get("/api/departments")
def get_departments(db: Session = Depends(get_db)):
    db_depts = db.query(models.User.department).distinct().all()
    dept_list = [d[0] for d in db_depts if d[0]]
    defaults = ["Admin", "IT Operations", "Executive", "Operations", "Sales"]
    for d in defaults:
        if d not in dept_list:
            dept_list.append(d)
    return sorted(dept_list)

# --- Authentication ---
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

# --- Departments Summary ---
@app.get("/api/admin/departments")
def list_departments(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    dept_map = defaultdict(lambda: {"total_users": 0, "active_clocked_in": 0})

    for u in users:
        dept_map[u.department]["total_users"] += 1

    punches = db.query(models.TimePunch).order_by(desc(models.TimePunch.timestamp)).all()
    seen_users = set()
    for p in punches:
        if p.employee_id not in seen_users:
            seen_users.add(p.employee_id)
            if p.punch_type == "CLOCK_IN":
                u = db.query(models.User).filter(models.User.employee_id == p.employee_id).first()
                if u:
                    dept_map[u.department]["active_clocked_in"] += 1

    return [{"department": k, **v} for k, v in dept_map.items()]

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
        address=req.address or "Pasig, Metro Manila",
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
            "address": p.address or "Pasig, Metro Manila",
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

# --- WEB EMPLOYEE PORTAL UI (Clock In / Clock Out Workspace) ---
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
        <style> body { font-family: 'Inter', sans-serif; } </style>
    </head>
    <body class="bg-slate-50 text-slate-900 min-h-screen antialiased flex flex-col justify-between">

        <!-- Login Card Overlay -->
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

        <!-- Clock-In / Clock-Out Workspace -->
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

                <!-- Interactive Clock Punch Button Card -->
                <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 text-center space-y-5">
                    <div>
                        <span id="statusBadge" class="inline-block px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600">OFF DUTY</span>
                        <h2 id="liveTimerText" class="text-3xl font-extrabold text-slate-800 font-mono mt-3">00:00:00</h2>
                        <p id="shiftSubText" class="text-xs text-slate-500 mt-1">Ready to start shift</p>
                    </div>

                    <button id="punchActionBtn" onclick="triggerPunch()" class="w-full py-4 rounded-xl font-bold text-base text-white bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/25 transition">
                        CLOCK IN NOW
                    </button>

                    <p id="geoStatusText" class="text-[11px] text-slate-400">GPS location verification enabled</p>
                </div>

                <!-- Daily Timesheet History -->
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
            let currentIsClockedIn = false;
            let currentLat = 14.5764;
            let currentLng = 121.0851;

            // Fetch dynamic departments on load
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

                // Load saved credentials from localStorage
                const savedEmpId = localStorage.getItem("hris_emp_id");
                if (savedEmpId) document.getElementById("loginEmpId").value = savedEmpId;

                // Watch geolocation
                if ("geolocation" in navigator) {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => {
                            currentLat = pos.coords.latitude;
                            currentLng = pos.coords.longitude;
                            document.getElementById("geoStatusText").innerText = `GPS Active: ${currentLat.toFixed(4)}, ${currentLng.toFixed(4)}`;
                        },
                        (err) => {
                            document.getElementById("geoStatusText").innerText = "GPS Location: Default Pasig Coordinates";
                        }
                    );
                }
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
                        loadActiveStatus();
                        loadTimesheet();
                    } else {
                        alert("Invalid Employee ID or Password");
                    }
                } catch (err) {
                    alert("Unable to reach HRIS server");
                }
            });

            function logoutEmployee() {
                clearInterval(activeTimerInterval);
                currentUser = null;
                document.getElementById("employeeWorkspace").classList.add("hidden");
                document.getElementById("employeeLoginCard").classList.remove("hidden");
            }

            async function loadActiveStatus() {
                if (!currentUser) return;
                const res = await fetch(`${API_BASE}/punch/active/${currentUser.employee_id}`);
                const data = await res.json();
                
                const badge = document.getElementById("statusBadge");
                const btn = document.getElementById("punchActionBtn");
                const subText = document.getElementById("shiftSubText");

                clearInterval(activeTimerInterval);

                if (data.is_clocked_in) {
                    currentIsClockedIn = true;
                    badge.innerText = "ON DUTY";
                    badge.className = "inline-block px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800";
                    btn.innerText = "CLOCK OUT NOW";
                    btn.className = "w-full py-4 rounded-xl font-bold text-base text-white bg-rose-600 hover:bg-rose-700 shadow-lg shadow-rose-500/25 transition";
                    subText.innerText = "Active shift running";

                    let elapsed = data.elapsed_seconds || 0;
                    startTimer(elapsed);
                } else {
                    currentIsClockedIn = false;
                    badge.innerText = "OFF DUTY";
                    badge.className = "inline-block px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600";
                    btn.innerText = "CLOCK IN NOW";
                    btn.className = "w-full py-4 rounded-xl font-bold text-base text-white bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/25 transition";
                    document.getElementById("liveTimerText").innerText = "00:00:00";
                    subText.innerText = "Ready to start shift";
                }
            }

            function startTimer(seconds) {
                function update() {
                    seconds++;
                    const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
                    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
                    const s = String(seconds % 60).padStart(2, '0');
                    document.getElementById("liveTimerText").innerText = `${h}:${m}:${s}`;
                }
                update();
                activeTimerInterval = setInterval(update, 1000);
            }

            async function triggerPunch() {
                if (!currentUser) return;
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
                    loadActiveStatus();
                    loadTimesheet();
                } else {
                    alert("Failed to submit punch");
                }
            }

            async function loadTimesheet() {
                if (!currentUser) return;
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
            }

            initPortal();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# --- WEB ADMIN PORTAL UI ---
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

        <!-- Admin Login Guard -->
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

        <!-- Edit Profile Modal -->
        <div id="editUserModal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
                <div class="flex justify-between items-center border-b pb-3">
                    <h3 class="font-bold text-slate-800 text-base">Edit Profile & Permissions</h3>
                    <button onclick="closeEditModal()" class="text-slate-400 hover:text-slate-600 text-lg font-bold">&times;</button>
                </div>
                <form id="editUserForm" class="space-y-3">
                    <input type="hidden" id="editOriginalEmpId">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-semibold text-slate-500 mb-1">Employee ID</label>
                            <input type="text" id="editEmpId" required class="w-full border p-2 rounded-lg text-xs font-mono">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-500 mb-1">Full Name</label>
                            <input type="text" id="editName" required class="w-full border p-2 rounded-lg text-xs">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-semibold text-slate-500 mb-1">Department</label>
                            <select id="editDept" class="deptDropdownSelect w-full border p-2 rounded-lg text-xs"></select>
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-500 mb-1">Position</label>
                            <input type="text" id="editPos" required class="w-full border p-2 rounded-lg text-xs">
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-500 mb-1">Role (RBAC Privilege)</label>
                        <select id="editRole" class="w-full border p-2 rounded-lg text-xs">
                            <option value="employee">Employee</option>
                            <option value="manager">Manager</option>
                            <option value="super_admin">Super Admin</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-500 mb-1">New Password (Optional)</label>
                        <input type="password" id="editPass" placeholder="••••••••" class="w-full border p-2 rounded-lg text-xs">
                    </div>
                    <div class="flex justify-end gap-2 pt-2 border-t">
                        <button type="button" onclick="closeEditModal()" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs transition">Cancel</button>
                        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs transition">Save Changes</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Main Workspace -->
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
                            <button id="tabBtnUsers" onclick="switchTab('users')" class="px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition">User Directory & RBAC</button>
                            <button id="tabBtnGroups" onclick="switchTab('groups')" class="px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition">Smart Groups</button>
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

                <!-- TAB 1: Time Clocks & Interactive Map View -->
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
                        <button onclick="toggleCollapse('overrideBody', 'overrideIcon')" class="w-full p-4 sm:p-5 flex items-center justify-between bg-slate-50/50 hover:bg-slate-50 text-left transition border-b border-slate-100">
                            <div>
                                <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider">Manual DTR Entry Override</h2>
                                <p class="text-xs text-slate-500">Insert custom clock-in/out records for an employee</p>
                            </div>
                            <span id="overrideIcon" class="text-slate-400 font-bold text-sm transform transition-transform">▲</span>
                        </button>
                        <div id="overrideBody" class="p-5 border-t border-slate-100 space-y-4">
                            <form id="addForm" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                                <input type="text" id="addEmpId" placeholder="Employee ID" required class="border border-slate-200 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                                <select id="addType" class="border border-slate-200 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                                    <option value="CLOCK_IN">CLOCK_IN</option>
                                    <option value="CLOCK_OUT">CLOCK_OUT</option>
                                </select>
                                <input type="datetime-local" id="addTime" required class="border border-slate-200 rounded-lg p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                                <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg text-sm transition shadow-sm">
                                    Insert Punch
                                </button>
                            </form>
                        </div>
                    </div>

                    <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                        <div class="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <button onclick="toggleCollapse('auditTableBody', 'auditIcon')" class="text-slate-400 hover:text-slate-600 text-xs font-bold">
                                    <span id="auditIcon">▲</span>
                                </button>
                                <div>
                                    <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider">DTR Audit Logs</h2>
                                    <p class="text-xs text-slate-500">Raw timestamp records from PostgreSQL</p>
                                </div>
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

                <!-- TAB 2: User Directory & RBAC Control Page -->
                <div id="tabContentUsers" class="hidden space-y-6">
                    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                        <div>
                            <h2 class="text-base font-bold text-slate-800">User Directory & Permissions</h2>
                            <p class="text-xs text-slate-500">Manage employee accounts, titles, and system RBAC access levels</p>
                        </div>
                        <button onclick="toggleCollapse('newUserFormCard', 'newUserIcon')" class="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition shadow-sm">
                            <span>+ Add New Employee</span>
                            <span id="newUserIcon" class="text-xs">▼</span>
                        </button>
                    </div>

                    <div id="newUserFormCard" class="hidden bg-white rounded-xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                        <div class="border-b border-slate-100 pb-2">
                            <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Provision New Account</h3>
                        </div>

                        <form id="createUserForm" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
                            <input type="text" id="uEmpId" placeholder="Emp ID (e.g. 3286)" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <input type="text" id="uName" placeholder="Full Name" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <select id="uDept" class="deptDropdownSelect border border-slate-200 rounded-lg p-2 text-xs"></select>
                            <input type="text" id="uPos" placeholder="Position" value="IT Specialist" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <select id="uRole" class="border border-slate-200 rounded-lg p-2 text-xs">
                                <option value="employee">Employee</option>
                                <option value="manager">Manager</option>
                                <option value="super_admin">Super Admin</option>
                            </select>
                            <input type="password" id="uPass" placeholder="Password" value="password123" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <button type="submit" class="sm:col-span-2 lg:col-span-6 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg text-xs transition shadow-sm">
                                Create Account
                            </button>
                        </form>
                    </div>

                    <div id="departmentDirectoryContainer" class="space-y-4"></div>
                </div>

                <!-- TAB 3: Smart Groups -->
                <div id="tabContentGroups" class="hidden space-y-6">
                    <div class="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                        <div>
                            <h2 class="text-base font-bold text-slate-800">Smart Groups</h2>
                            <p class="text-xs text-slate-500">Segment users by operational assignment, feature access, and automated rules</p>
                        </div>
                        <button class="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition shadow-sm">
                            + Add Segment
                        </button>
                    </div>

                    <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                        <div class="p-4 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center text-xs font-bold text-slate-500 uppercase">
                            <span>Segment Name</span>
                            <span>Connected Services</span>
                        </div>

                        <div class="border-b border-slate-100">
                            <div class="p-3.5 bg-slate-50/30 flex items-center justify-between font-bold text-xs text-slate-800">
                                <span class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-blue-600"></span> Head Office</span>
                                <span class="text-slate-500">10 Groups</span>
                            </div>
                            <div class="divide-y divide-slate-100 text-xs">
                                <div class="p-3.5 pl-8 flex justify-between items-center hover:bg-slate-50">
                                    <span class="font-semibold text-slate-800">Head Office - Management</span>
                                    <span class="bg-blue-50 text-blue-700 font-bold px-2 py-0.5 rounded-full">14 / 14 Connected</span>
                                </div>
                                <div class="p-3.5 pl-8 flex justify-between items-center hover:bg-slate-50">
                                    <span class="font-semibold text-slate-800">Head Office - Finance & HR</span>
                                    <span class="bg-blue-50 text-blue-700 font-bold px-2 py-0.5 rounded-full">8 / 8 Connected</span>
                                </div>
                            </div>
                        </div>

                        <div>
                            <div class="p-3.5 bg-slate-50/30 flex items-center justify-between font-bold text-xs text-slate-800">
                                <span class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-emerald-600"></span> Operations</span>
                                <span class="text-slate-500">5 Groups</span>
                            </div>
                            <div class="divide-y divide-slate-100 text-xs">
                                <div class="p-3.5 pl-8 flex justify-between items-center hover:bg-slate-50">
                                    <span class="font-semibold text-slate-800">Operations - TSG</span>
                                    <span class="bg-emerald-50 text-emerald-700 font-bold px-2 py-0.5 rounded-full">8 / 8 Selected</span>
                                </div>
                                <div class="p-3.5 pl-8 flex justify-between items-center hover:bg-slate-50">
                                    <span class="font-semibold text-slate-800">Operations - Technical Support</span>
                                    <span class="bg-emerald-50 text-emerald-700 font-bold px-2 py-0.5 rounded-full">10 / 10 Selected</span>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

            </main>
        </div>

        <script>
            const API_BASE = "/api";
            let globalUsersCache = [];
            let globalDeptsCache = [];
            let leafletMap = null;
            let mapMarkers = [];

            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            document.getElementById('addTime').value = now.toISOString().slice(0, 16);

            function initLeafletMap() {
                if (leafletMap) return;
                leafletMap = L.map('map').setView([14.5764, 121.0851], 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap contributors'
                }).addTo(leafletMap);
            }

            async function fetchDynamicDepartments() {
                try {
                    const res = await fetch(`${API_BASE}/departments`);
                    globalDeptsCache = await res.json();
                    
                    const dropdowns = document.querySelectorAll('.deptDropdownSelect');
                    dropdowns.forEach(sel => {
                        sel.innerHTML = "";
                        globalDeptsCache.forEach(d => {
                            sel.innerHTML += `<option value="${d}">${d}</option>`;
                        });
                    });
                } catch (e) {
                    console.log('Error fetching dynamic depts:', e);
                }
            }

            function switchTab(tabName) {
                const clockTab = document.getElementById("tabContentClocks");
                const userTab = document.getElementById("tabContentUsers");
                const groupTab = document.getElementById("tabContentGroups");

                const btnClocks = document.getElementById("tabBtnClocks");
                const btnUsers = document.getElementById("tabBtnUsers");
                const btnGroups = document.getElementById("tabBtnGroups");

                clockTab.classList.add("hidden");
                userTab.classList.add("hidden");
                groupTab.classList.add("hidden");

                btnClocks.className = "px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition";
                btnUsers.className = "px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition";
                btnGroups.className = "px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition";

                if (tabName === 'clocks') {
                    clockTab.classList.remove("hidden");
                    btnClocks.className = "px-3 py-1.5 rounded-md bg-white text-blue-600 shadow-sm transition";
                    if (leafletMap) leafletMap.invalidateSize();
                } else if (tabName === 'users') {
                    userTab.classList.remove("hidden");
                    btnUsers.className = "px-3 py-1.5 rounded-md bg-white text-blue-600 shadow-sm transition";
                } else if (tabName === 'groups') {
                    groupTab.classList.remove("hidden");
                    btnGroups.className = "px-3 py-1.5 rounded-md bg-white text-blue-600 shadow-sm transition";
                }
            }

            function toggleCollapse(bodyId, iconId) {
                const el = document.getElementById(bodyId);
                const icon = document.getElementById(iconId);
                if (el.classList.contains("hidden")) {
                    el.classList.remove("hidden");
                    if (icon) icon.innerText = "▲";
                } else {
                    el.classList.add("hidden");
                    if (icon) icon.innerText = "▼";
                }
            }

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
                            initLeafletMap();
                            loadDashboard();
                        } else {
                            alert("Access Denied: Account lacks Super Admin permissions.");
                        }
                    } else {
                        alert("Invalid Employee ID or Password");
                    }
                } catch (err) {
                    alert("Unable to reach authentication backend");
                }
            });

            function logoutAdmin() {
                document.getElementById("adminWorkspace").classList.add("hidden");
                document.getElementById("loginOverlay").classList.remove("hidden");
            }

            async function loadDashboard() {
                await fetchDynamicDepartments();
                await loadSegmentedUsers();
                await loadPunches();
            }

            async function loadSegmentedUsers() {
                const res = await fetch(`${API_BASE}/admin/users`);
                const users = await res.json();
                globalUsersCache = users;
                document.getElementById("statTotalUsersCount").innerText = users.length;

                const container = document.getElementById("departmentDirectoryContainer");
                container.innerHTML = "";

                const grouped = {};
                users.forEach(u => {
                    if (!grouped[u.department]) grouped[u.department] = [];
                    grouped[u.department].push(u);
                });

                Object.keys(grouped).forEach((dept, index) => {
                    const deptUsers = grouped[dept];
                    const cardId = `deptGroup_${index}`;
                    const iconId = `deptIcon_${index}`;

                    let rowsHtml = "";
                    deptUsers.forEach(u => {
                        rowsHtml += `
                            <tr class="hover:bg-slate-50 transition">
                                <td class="p-3.5 font-bold font-mono text-slate-800">${u.employee_id}</td>
                                <td class="p-3.5 font-semibold text-slate-800">${u.name}</td>
                                <td class="p-3.5 text-slate-600">${u.position}</td>
                                <td class="p-3.5">
                                    <span class="px-2.5 py-0.5 text-xs font-bold rounded-full ${u.role === 'super_admin' ? 'bg-purple-50 text-purple-700 border border-purple-200' : u.role === 'manager' ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-700'}">
                                        ${u.role}
                                    </span>
                                </td>
                                <td class="p-3.5 text-right space-x-3">
                                    <button onclick="openEditModal('${u.employee_id}')" class="text-xs text-blue-600 hover:underline font-semibold">Edit</button>
                                    <button onclick="deleteUser('${u.employee_id}')" class="text-xs text-rose-600 hover:underline font-semibold">Delete</button>
                                </td>
                            </tr>
                        `;
                    });

                    container.innerHTML += `
                        <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                            <button onclick="toggleCollapse('${cardId}', '${iconId}')" class="w-full p-4 flex items-center justify-between bg-slate-50/50 hover:bg-slate-50 text-left transition border-b border-slate-100">
                                <div class="flex items-center gap-2">
                                    <h3 class="text-sm font-bold text-slate-800">${dept}</h3>
                                    <span class="text-xs bg-slate-200 text-slate-700 font-bold px-2 py-0.5 rounded-full">${deptUsers.length}</span>
                                </div>
                                <span id="${iconId}" class="text-slate-400 font-bold text-xs">▲</span>
                            </button>
                            <div id="${cardId}" class="overflow-x-auto">
                                <table class="w-full text-left text-xs">
                                    <thead>
                                        <tr class="bg-slate-50/50 text-slate-500 font-bold border-b">
                                            <th class="p-3.5">Employee ID</th>
                                            <th class="p-3.5">Name</th>
                                            <th class="p-3.5">Position</th>
                                            <th class="p-3.5">Role</th>
                                            <th class="p-3.5 text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-slate-100">${rowsHtml}</tbody>
                                </table>
                            </div>
                        </div>
                    `;
                });
            }

            function focusMapLocation(lat, lng, name) {
                if (leafletMap) {
                    leafletMap.setView([lat, lng], 15);
                    mapMarkers.forEach(m => {
                        if (m.getLatLng().lat === lat && m.getLatLng().lng === lng) {
                            m.openPopup();
                        }
                    });
                }
            }

            async function loadPunches() {
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
                                <span class="px-2.5 py-0.5 rounded-full text-xs font-bold ${isClockIn ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}">
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

                    mapUserList.innerHTML += `
                        <div onclick="focusMapLocation(${lat}, ${lng}, '${p.employee_name}')" class="bg-white p-2.5 rounded-lg border border-slate-200 cursor-pointer hover:border-blue-500 transition shadow-sm space-y-1">
                            <div class="flex justify-between items-center">
                                <span class="font-bold text-xs text-slate-800">${p.employee_name}</span>
                                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded ${isClockIn ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">${p.punch_type}</span>
                            </div>
                            <p class="text-[11px] text-slate-500 truncate">${p.address}</p>
                            <p class="text-[10px] font-mono text-slate-400">${p.formatted_time}</p>
                        </div>
                    `;

                    if (leafletMap) {
                        const marker = L.marker([lat, lng]).addTo(leafletMap);
                        marker.bindPopup(`
                            <div class="p-1 space-y-1 font-sans">
                                <h4 class="font-bold text-sm text-slate-800">${p.employee_name}</h4>
                                <p class="text-xs text-slate-600"><b>ID:</b> ${p.employee_id} | <b>Dept:</b> ${p.department}</p>
                                <p class="text-xs text-slate-600"><b>Action:</b> <span class="font-bold ${isClockIn ? 'text-emerald-600' : 'text-rose-600'}">${p.punch_type}</span></p>
                                <p class="text-xs text-slate-500">${p.address}</p>
                                <p class="text-[10px] text-slate-400">${p.formatted_time}</p>
                            </div>
                        `);
                        mapMarkers.push(marker);
                    }
                });

                document.getElementById("statClockedInCount").innerText = activeClockedInCount;
            }

            function openEditModal(empId) {
                const user = globalUsersCache.find(u => u.employee_id === empId);
                if (!user) return;

                document.getElementById("editOriginalEmpId").value = user.employee_id;
                document.getElementById("editEmpId").value = user.employee_id;
                document.getElementById("editName").value = user.name;
                document.getElementById("editDept").value = user.department;
                document.getElementById("editPos").value = user.position;
                document.getElementById("editRole").value = user.role;
                document.getElementById("editPass").value = "";

                document.getElementById("editUserModal").classList.remove("hidden");
            }

            function closeEditModal() {
                document.getElementById("editUserModal").classList.add("hidden");
            }

            document.getElementById("editUserForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const origId = document.getElementById("editOriginalEmpId").value;
                const newId = document.getElementById("editEmpId").value;
                const name = document.getElementById("editName").value;
                const dept = document.getElementById("editDept").value;
                const pos = document.getElementById("editPos").value;
                const role = document.getElementById("editRole").value;
                const pass = document.getElementById("editPass").value;

                const payload = {
                    new_employee_id: newId,
                    name: name,
                    department: dept,
                    position: pos,
                    role: role,
                };
                if (pass) payload.password = pass;

                const res = await fetch(`${API_BASE}/admin/users/${origId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    closeEditModal();
                    loadSegmentedUsers();
                } else {
                    alert("Failed to update user profile");
                }
            });

            document.getElementById("createUserForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                await fetch(`${API_BASE}/admin/users`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        employee_id: document.getElementById("uEmpId").value,
                        name: document.getElementById("uName").value,
                        department: document.getElementById("uDept").value,
                        position: document.getElementById("uPos").value,
                        role: document.getElementById("uRole").value,
                        password: document.getElementById("uPass").value
                    })
                });
                toggleCollapse('newUserFormCard', 'newUserIcon');
                loadSegmentedUsers();
            });

            document.getElementById("addForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                await fetch(`${API_BASE}/admin/dtr`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        employee_id: document.getElementById("addEmpId").value,
                        punch_type: document.getElementById("addType").value,
                        timestamp: document.getElementById("addTime").value + ":00",
                        latitude: 14.5764,
                        longitude: 121.0851,
                        address: "Pasig, Metro Manila"
                    })
                });
                loadPunches();
            });

            async function deleteUser(empId) {
                if (confirm(`Remove user ${empId}?`)) {
                    await fetch(`${API_BASE}/admin/users/${empId}`, { method: "DELETE" });
                    loadSegmentedUsers();
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
