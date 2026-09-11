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

app = FastAPI(title="HRIS Enterprise API", version="3.1.0")

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

class UserCreateRequest(BaseModel):
    employee_id: str
    name: str
    department: str
    position: str
    role: str
    password: str

class UserUpdateRequest(BaseModel):
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
    latitude: float = 0.0
    longitude: float = 0.0
    address: Optional[str] = "Manual Admin Entry"

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

# --- User Management API (RBAC) ---
@app.get("/api/admin/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

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

# --- DTR Audit & Export ---
@app.get("/api/admin/dtr")
def list_all_dtr(employee_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.TimePunch)
    if employee_id:
        query = query.filter(models.TimePunch.employee_id == employee_id)
    punches = query.order_by(desc(models.TimePunch.timestamp)).all()
    
    result = []
    for p in punches:
        result.append({
            "id": p.id,
            "employee_id": p.employee_id,
            "punch_type": p.punch_type,
            "formatted_time": p.timestamp.strftime("%Y-%m-%d %I:%M:%S %p"),
            "address": p.address or "Pasig, Metro Manila",
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

# --- Modern Segmented Web Admin UI ---
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
        <style> body { font-family: 'Inter', sans-serif; } </style>
    </head>
    <body class="bg-slate-50 text-slate-900 min-h-screen antialiased">

        <!-- Login Overlay Guard -->
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

        <!-- Main Workspace -->
        <div id="adminWorkspace" class="hidden min-h-screen flex flex-col">
            <!-- Navigation Header -->
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

                        <!-- Navigation Tab Switcher -->
                        <nav class="hidden md:flex gap-1 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                            <button id="tabBtnClocks" onclick="switchTab('clocks')" class="px-3 py-1.5 rounded-md bg-white text-blue-600 shadow-sm transition">Time Clocks & DTR</button>
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

                <!-- TAB 1: Time Clocks & DTR Management -->
                <div id="tabContentClocks" class="space-y-6">
                    <!-- Department Time Clocks Grid -->
                    <div>
                        <h2 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Department Time Clocks</h2>
                        <div id="deptGrid" class="grid grid-cols-1 md:grid-cols-3 gap-4"></div>
                    </div>

                    <!-- Collapsible Manual Override Card -->
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

                    <!-- Collapsible DTR Audit Table -->
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
                    <!-- Create User Form Card -->
                    <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                            <div>
                                <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider">Add New User Account</h2>
                                <p class="text-xs text-slate-500">Provision credentials and assign access levels</p>
                            </div>
                        </div>

                        <form id="createUserForm" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
                            <input type="text" id="uEmpId" placeholder="Emp ID (e.g. 3286)" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <input type="text" id="uName" placeholder="Full Name" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <input type="text" id="uDept" placeholder="Department" value="IT Operations" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <input type="text" id="uPos" placeholder="Position" value="IT Specialist" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <select id="uRole" class="border border-slate-200 rounded-lg p-2 text-xs">
                                <option value="employee">Employee</option>
                                <option value="manager">Manager</option>
                                <option value="super_admin">Super Admin</option>
                            </select>
                            <input type="password" id="uPass" placeholder="Password" value="password123" required class="border border-slate-200 rounded-lg p-2 text-xs">
                            <button type="submit" class="sm:col-span-2 lg:col-span-6 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg text-xs transition shadow-sm">
                                Create Account
                            </button>
                        </form>
                    </div>

                    <!-- Department-Segmented Directory Accordions -->
                    <div class="space-y-4">
                        <h2 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Directory Grouped By Department</h2>
                        <div id="departmentDirectoryContainer" class="space-y-3"></div>
                    </div>
                </div>

            </main>
        </div>

        <script>
            const API_BASE = "/api";

            // Default datetime field setup
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            document.getElementById('addTime').value = now.toISOString().slice(0, 16);

            function switchTab(tabName) {
                const clockTab = document.getElementById("tabContentClocks");
                const userTab = document.getElementById("tabContentUsers");
                const btnClocks = document.getElementById("tabBtnClocks");
                const btnUsers = document.getElementById("tabBtnUsers");

                if (tabName === 'clocks') {
                    clockTab.classList.remove("hidden");
                    userTab.classList.add("hidden");
                    btnClocks.className = "px-3 py-1.5 rounded-md bg-white text-blue-600 shadow-sm transition";
                    btnUsers.className = "px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition";
                } else {
                    clockTab.classList.add("hidden");
                    userTab.classList.remove("hidden");
                    btnUsers.className = "px-3 py-1.5 rounded-md bg-white text-blue-600 shadow-sm transition";
                    btnClocks.className = "px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition";
                }
            }

            function toggleCollapse(bodyId, iconId) {
                const el = document.getElementById(bodyId);
                const icon = document.getElementById(iconId);
                if (el.classList.contains("hidden")) {
                    el.classList.remove("hidden");
                    icon.innerText = "▲";
                } else {
                    el.classList.add("hidden");
                    icon.innerText = "▼";
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
                loadDepartments();
                loadSegmentedUsers();
                loadPunches();
            }

            async function loadDepartments() {
                const res = await fetch(`${API_BASE}/admin/departments`);
                const data = await res.json();
                const grid = document.getElementById("deptGrid");
                grid.innerHTML = "";

                data.forEach(d => {
                    grid.innerHTML += `
                        <div class="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm space-y-2">
                            <div class="flex justify-between items-center">
                                <h3 class="font-bold text-slate-800 text-sm">${d.department}</h3>
                                <span class="text-xs bg-blue-50 text-blue-700 font-bold px-2 py-0.5 rounded-full">${d.active_clocked_in} On Duty</span>
                            </div>
                            <p class="text-xs text-slate-500">${d.total_users} Total Users Assigned</p>
                        </div>
                    `;
                });
            }

            async function loadSegmentedUsers() {
                const res = await fetch(`${API_BASE}/admin/users`);
                const users = await res.json();
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
                                <td class="p-3 font-bold text-slate-800">${u.employee_id}</td>
                                <td class="p-3 font-semibold text-slate-700">${u.name}</td>
                                <td class="p-3 text-slate-500">${u.position}</td>
                                <td class="p-3">
                                    <span class="px-2 py-0.5 text-xs font-bold rounded ${u.role === 'super_admin' ? 'bg-purple-50 text-purple-700 border border-purple-200' : u.role === 'manager' ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-700'}">
                                        ${u.role}
                                    </span>
                                </td>
                                <td class="p-3 text-right">
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
                                            <th class="p-3">ID</th>
                                            <th class="p-3">Name</th>
                                            <th class="p-3">Position</th>
                                            <th class="p-3">Role</th>
                                            <th class="p-3 text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-slate-100">${rowsHtml}</tbody>
                                </table>
                            </div>
                        </div>
                    `;
                });
            }

            async function loadPunches() {
                const res = await fetch(`${API_BASE}/admin/dtr`);
                const data = await res.json();
                const tbody = document.getElementById("dtrTableBody");
                tbody.innerHTML = "";

                data.forEach(p => {
                    const isClockIn = p.punch_type === 'CLOCK_IN';
                    tbody.innerHTML += `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="p-3.5 pl-5 font-mono text-xs text-slate-400">#${p.id}</td>
                            <td class="p-3.5 font-bold text-slate-800">${p.employee_id}</td>
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
                });
            }

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
                        address: "Manual Admin Entry"
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
