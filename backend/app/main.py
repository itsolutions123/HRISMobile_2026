import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .database import engine, Base, SessionLocal
from .models import JobCategory, JobSubItem, Employee, PunchLog
from .limiter import limiter
from .routers import auth, punch, jobs, manager, dtr, forms
from .auth_utils import get_password_hash

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS DTR Backend API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.bigtimeempire.com",
        "http://localhost:8089",
        "http://127.0.0.1:8089",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(punch.router)
app.include_router(jobs.router)
app.include_router(manager.router)
app.include_router(dtr.router)
app.include_router(forms.router)

@app.on_event("startup")
def seed_initial_data():
    db = SessionLocal()
    try:
        initial_admin_pass = os.getenv("INITIAL_SUPERADMIN_PASSWORD")
        super_admin = db.query(Employee).filter(Employee.employee_id == "xinxaola").first()
        if not super_admin and initial_admin_pass:
            super_admin = Employee(
                employee_id="xinxaola",
                name="Super Admin Xenon",
                first_name="Xenon",
                last_name="Admin",
                position="Super Administrator",
                department="Admin",
                password_hash=get_password_hash(initial_admin_pass),
                mobile_phone="+63 998 940 0957",
                email="admin@bigtimeempire.com",
                role="Admin",
                status="APPROVED"
            )
            db.add(super_admin)
            db.commit()
        elif super_admin:
            super_admin.role = "Admin"
            super_admin.status = "APPROVED"
            db.commit()

        admin_jaypee = db.query(Employee).filter(Employee.employee_id == "3286").first()
        if not admin_jaypee and initial_admin_pass:
            admin_jaypee = Employee(
                employee_id="3286",
                name="Jaypee Balonzo",
                first_name="Jaypee",
                last_name="Balonzo",
                position="IT System Administrator",
                department="Admin",
                password_hash=get_password_hash(initial_admin_pass),
                mobile_phone="+63 998 940 0957",
                email="itsupport.associate@bigtimeempire.com",
                role="Admin",
                status="APPROVED"
            )
            db.add(admin_jaypee)
            db.commit()
        elif admin_jaypee:
            admin_jaypee.role = "Admin"
            admin_jaypee.status = "APPROVED"
            db.commit()

        if db.query(JobCategory).count() == 0:
            default_cat = JobCategory(name="Head Office", code="HO-IT", description="IT")
            db.add(default_cat)
            db.commit()
            db.refresh(default_cat)

            roles = ['IT Assistant', 'System Administrator', 'IT Head', 'Technical Support Specialist']
            for role in roles:
                db.add(JobSubItem(category_id=default_cat.id, name=role))
            db.commit()
    except Exception as e:
        print(f"Startup Seeding Exception: {e}")
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "online", "service": "HRIS Backend", "admin_panel": "/admin"}

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/{path:path}", response_class=HTMLResponse)
def get_admin_dashboard(path: str = ""):
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>atWork — Bigtime Empire Corporation</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            :root {
                --bg-main: #f8fafc;
                --surface-card: #ffffff;
                --border-color: #e2e8f0;
                --border-subtle: #f1f5f9;
                --text-primary: #0f172a;
                --text-secondary: #475569;
                --text-muted: #94a3b8;
                --gold-primary: #d97706;
                --gold-accent: #f59e0b;
                --gold-bg: #fffbeb;
                --gold-border: #fef3c7;
                --sidebar-bg: #0f172a;
                --sidebar-hover: #1e293b;
            }
            body {
                background-color: var(--bg-main);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                color: var(--text-primary);
                font-size: 14px;
                letter-spacing: -0.01em;
            }
            .sidebar {
                min-height: 100vh;
                background: var(--sidebar-bg);
                color: #94a3b8;
                border-right: 1px solid #1e293b;
            }
            .sidebar .nav-link {
                color: #94a3b8;
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 2px;
                font-weight: 500;
                font-size: 13px;
                display: flex;
                align-items: center;
                gap: 10px;
                cursor: pointer;
                transition: all 0.15s ease;
            }
            .sidebar .nav-link:hover, .sidebar .nav-link.active {
                background: var(--sidebar-hover);
                color: #ffffff;
            }
            .sidebar .nav-link.active i {
                color: var(--gold-accent);
            }
            .sidebar .section-label {
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #475569;
                margin: 20px 12px 6px;
            }
            .top-bar {
                background: var(--surface-card);
                border-bottom: 1px solid var(--border-color);
                padding: 12px 32px;
            }
            .card-custom {
                background: var(--surface-card);
                border-radius: 12px;
                border: 1px solid var(--border-color);
                padding: 24px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
            }
            #map, #modalHistoryMap {
                height: 520px;
                width: 100%;
                border-radius: 12px;
                border: 1px solid var(--border-color);
            }
            #modalHistoryMap {
                height: 320px;
            }
            .avatar-circle {
                width: 32px;
                height: 32px;
                background-color: var(--gold-bg);
                color: var(--gold-primary);
                border: 1px solid var(--gold-border);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 12px;
            }
            .avatar-chip {
                width: 28px;
                height: 28px;
                border-radius: 50%;
                font-size: 11px;
                font-weight: 700;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border: 2px solid #ffffff;
            }
            .btn-primary-custom {
                background-color: var(--gold-primary);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
                transition: background-color 0.15s ease;
            }
            .btn-primary-custom:hover {
                background-color: #b45309;
                color: #ffffff;
            }
            .btn-outline-custom {
                background-color: #ffffff;
                color: var(--text-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 13px;
            }
            .btn-outline-custom:hover {
                background-color: var(--bg-main);
                color: var(--text-primary);
            }
            .form-control, .form-select {
                border-radius: 8px;
                border: 1px solid var(--border-color);
                font-size: 13px;
                padding: 8px 12px;
                color: var(--text-primary);
            }
            .table {
                font-size: 13px;
                color: var(--text-primary);
            }
            .table thead th {
                font-weight: 600;
                color: var(--text-secondary);
                background-color: #f8fafc;
                border-bottom: 1px solid var(--border-color);
                padding: 10px 16px;
                font-size: 12px;
            }
            .table tbody td {
                padding: 12px 16px;
                border-bottom: 1px solid var(--border-subtle);
                vertical-align: middle;
            }
            .nav-tabs-connecteam .nav-link {
                border: none;
                color: var(--text-secondary);
                font-weight: 600;
                font-size: 13px;
                padding: 10px 16px;
                border-bottom: 2px solid transparent;
            }
            .nav-tabs-connecteam .nav-link.active {
                color: var(--gold-primary);
                border-bottom: 2px solid var(--gold-primary);
                background: transparent;
            }
            .filter-pill {
                background-color: var(--gold-bg);
                border: 1px solid var(--gold-border);
                color: var(--gold-primary);
                font-weight: 600;
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 16px;
            }
            .offcanvas-group-drawer {
                width: 760px !important;
                border-left: 1px solid var(--border-color);
            }
            .login-container {
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: var(--sidebar-bg);
            }
            .login-card {
                width: 420px;
                background: #ffffff;
                border-radius: 16px;
                padding: 36px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            }
            .feed-card-hover {
                cursor: pointer;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }
            .feed-card-hover:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            }
            .history-row-clickable {
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <!-- STANDALONE LOGIN PAGE OVERLAY -->
        <div id="login-overlay-page" class="login-container" style="display:none;">
            <div class="login-card">
                <div class="text-center mb-4">
                    <div class="d-inline-flex align-items-center justify-content-center p-3 rounded-circle mb-2" style="background: var(--gold-bg);">
                        <i class="bi bi-shield-lock-fill text-warning fs-2"></i>
                    </div>
                    <h4 class="fw-bold text-dark m-0">atWork</h4>
                    <small class="text-muted fw-semibold">Bigtime Empire Corporation</small>
                </div>

                <form id="adminLoginForm" onsubmit="handleAdminLogin(event)">
                    <div class="mb-3">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">EMPLOYEE ID OR USERNAME</label>
                        <input type="text" class="form-control py-2" id="loginEmpId" required>
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">PASSWORD</label>
                        <div class="input-group">
                            <input type="password" class="form-control py-2 border-end-0" id="loginPassword" required>
                            <button class="btn btn-outline-secondary border-start-0 bg-white" type="button" onclick="toggleLoginPassword()"><i class="bi bi-eye" id="passwordToggleIcon"></i></button>
                        </div>
                    </div>

                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="rememberMeCheckbox">
                            <label class="form-check-label text-secondary fs-7" for="rememberMeCheckbox">Remember me on this device</label>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary-custom w-100 py-2 fs-6 mb-2">Sign In to Workspace</button>
                </form>
            </div>
        </div>

        <!-- MAIN HRIS PORTAL VIEW -->
        <div id="portal-main-view" class="container-fluid p-0">
            <div class="row g-0">
                <!-- SIDEBAR -->
                <div class="col-md-2 sidebar p-3">
                    <div class="d-flex align-items-center gap-2 mb-1 px-2 pt-2">
                        <i class="bi bi-hexagon-fill text-warning fs-5"></i>
                        <span class="fs-5 fw-extrabold text-white tracking-tight" style="letter-spacing:-0.03em;">atWork</span>
                    </div>
                    <div class="px-2 mb-4">
                        <small class="text-warning fw-semibold" style="font-size: 10px; letter-spacing:0.05em;">BIGTIME EMPIRE CORP</small>
                    </div>

                    <div class="section-label">Core Workspace</div>
                    <a class="nav-link active" id="nav-clock" onclick="switchTab('clock')"><i class="bi bi-stopwatch"></i> Time Clock</a>
                    <a class="nav-link" id="nav-jobs" onclick="switchTab('jobs')"><i class="bi bi-diagram-3"></i> Smart Groups</a>
                    <a class="nav-link d-flex justify-content-between align-items-center" id="nav-users" onclick="switchTab('users')">
                        <span><i class="bi bi-people me-2"></i> Users & Directory</span>
                    </a>

                    <div class="section-label">Forms</div>
                    <div id="sidebar-forms-categories-list"></div>
                    <a class="nav-link text-primary mt-1 fw-semibold fs-7" onclick="openWorkspaceToolsFlyout(event)"><i class="bi bi-plus-circle me-2"></i> Add new</a>

                    <div class="section-label">Management</div>
                    <a class="nav-link" onclick="showToast('Scheduling accessible via Mobile workspace.')"><i class="bi bi-calendar3"></i> Scheduling</a>
                    <a class="nav-link" onclick="window.open('/api/dtr/export', '_blank')"><i class="bi bi-download"></i> Export DTR</a>
                </div>

                <!-- MAIN CONTENT -->
                <div class="col-md-10">
                    <div class="top-bar d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="m-0 fw-bold text-dark" id="page-title">Time Clock</h6>
                            <small class="text-muted" style="font-size:11px;">Bigtime Empire Corporation</small>
                        </div>

                        <div class="dropdown profile-dropdown">
                            <button class="btn border-0 d-flex align-items-center gap-2 p-1" type="button" data-bs-toggle="dropdown">
                                <div class="avatar-circle">SA</div>
                                <div class="text-start d-none d-sm-block ms-1">
                                    <div class="fw-bold text-dark lh-1" style="font-size: 13px;" id="topbar-user-name">Super Admin Xenon</div>
                                    <small class="text-muted" style="font-size: 11px;">Superadmin (xinxaola)</small>
                                </div>
                                <i class="bi bi-chevron-down text-muted ms-1" style="font-size: 10px;"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow-sm border-0 mt-2">
                                <li><a class="dropdown-item py-2 fs-7" onclick="showToast('Superadmin ID: xinxaola | Status: Active')"><i class="bi bi-person me-2"></i> Profile details</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item py-2 fs-7 text-danger" onclick="performSignOut()"><i class="bi bi-box-arrow-right me-2"></i> Sign Out</a></li>
                            </ul>
                        </div>
                    </div>

                    <div class="p-4">
                        <!-- TAB 1: TIME CLOCK -->
                        <div id="tab-clock">
                            <div class="card-custom mb-4">
                                <div class="d-flex justify-content-between align-items-center mb-4">
                                    <div>
                                        <h6 class="fw-bold m-0 text-dark">Live Clock In Feed</h6>
                                        <small class="text-muted">Displaying currently clocked-in active employees only</small>
                                    </div>
                                    <button class="btn btn-outline-custom" onclick="loadPunchMap()"><i class="bi bi-arrow-clockwise me-1"></i> Refresh Feed</button>
                                </div>

                                <div class="row g-4">
                                    <div class="col-md-4">
                                        <div class="mb-3">
                                            <input type="text" class="form-control" id="searchClockedInInput" placeholder="Search employee name or ID..." onkeyup="filterLiveClockFeed(this.value)">
                                        </div>
                                        <div id="punch-list-sidebar" style="max-height: 440px; overflow-y: auto;">
                                            <p class="text-muted fs-7">Loading clocked-in active members...</p>
                                        </div>
                                    </div>
                                    <div class="col-md-8"><div id="map"></div></div>
                                </div>
                            </div>

                            <!-- TIME CLOCK HISTORY SECTION -->
                            <div class="card-custom">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <div>
                                        <h6 class="fw-bold m-0 text-dark"><i class="bi bi-clock-history me-2 text-warning"></i> Time Clock History</h6>
                                        <small class="text-muted">Daily Time Record logs filtered by date</small>
                                    </div>
                                    <div class="d-flex align-items-center gap-2">
                                        <input type="date" class="form-control form-control-sm" id="historyDateFilter" style="width: 160px;" onchange="loadTimeClockHistory()">
                                        <div class="input-group input-group-sm" style="width: 220px;">
                                            <span class="input-group-text bg-white"><i class="bi bi-search text-muted"></i></span>
                                            <input type="text" class="form-control" id="historySearchInput" placeholder="Search history..." onkeyup="filterHistoryTable(this.value)">
                                        </div>
                                    </div>
                                </div>

                                <div class="table-responsive">
                                    <table class="table table-hover align-middle m-0">
                                        <thead>
                                            <tr>
                                                <th width="30"><input type="checkbox" class="form-check-input"></th>
                                                <th>Full Name</th>
                                                <th>Brand</th>
                                                <th>Sub-group</th>
                                                <th>Clock In</th>
                                                <th>Clock Out</th>
                                                <th>Daily Total</th>
                                            </tr>
                                        </thead>
                                        <tbody id="timeclock-history-tbody">
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <!-- TAB 2: CONNECTEAM SMART GROUPS PROVISIONING -->
                        <div id="tab-jobs" style="display:none;">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div class="d-flex align-items-center gap-2">
                                    <button class="btn btn-outline-custom text-primary fw-bold" onclick="openAddBrandModal()"><i class="bi bi-plus-lg me-1"></i> Add Brand</button>
                                    <select class="form-select border-0 fw-bold text-dark bg-light" style="width: 180px;" id="selectedBrandFilter" onchange="filterGroupByBrand(this.value)">
                                    </select>
                                </div>
                                <span class="text-muted fw-semibold" style="font-size: 12px;" id="groups-count-label">0 groups total</span>
                            </div>

                            <div id="brands-container">
                                <!-- Dynamic Brand Sections -->
                            </div>
                        </div>

                        <!-- TAB 3: USERS & DIRECTORY -->
                        <div id="tab-users" style="display:none;">
                            <div id="users-directory-list-view">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <ul class="nav nav-tabs nav-tabs-connecteam border-0 m-0">
                                        <li class="nav-item">
                                            <a class="nav-link active" id="user-subtab-active" onclick="filterUserCategory('APPROVED')">Users</a>
                                        </li>
                                        <li class="nav-item">
                                            <a class="nav-link" id="user-subtab-admins" onclick="filterUserCategory('ADMIN')">Admins</a>
                                        </li>
                                        <li class="nav-item">
                                            <a class="nav-link" id="user-subtab-archived" onclick="filterUserCategory('ARCHIVED')">Archived</a>
                                        </li>
                                    </ul>

                                    <div class="d-flex align-items-center gap-2">
                                        <button class="btn btn-outline-custom btn-sm text-primary fw-bold" onclick="openPendingApprovalsModal()"><i class="bi bi-bell me-1"></i> Pending approvals</button>
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Company policies view')">Company policies</button>
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Settings opened')"><i class="bi bi-gear me-1"></i> Settings</button>
                                    </div>
                                </div>

                                <div class="card-custom p-0 overflow-hidden">
                                    <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                                        <div class="input-group" style="width: 280px;">
                                            <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
                                            <input type="text" class="form-control border-start-0" id="userSearchDirectory" placeholder="Search users..." onkeyup="filterDirectoryRows(this.value)">
                                        </div>
                                        <button class="btn btn-primary-custom" onclick="openDirectAddUserModal()"><i class="bi bi-plus-lg me-1"></i> Add users</button>
                                    </div>

                                    <div class="table-responsive">
                                        <table class="table table-hover align-middle m-0">
                                            <thead>
                                                <tr>
                                                    <th width="30"><input type="checkbox" class="form-check-input"></th>
                                                    <th>First name <i class="bi bi-arrow-up short ms-1"></i></th>
                                                    <th>Last name</th>
                                                    <th>Last login</th>
                                                    <th>Employment Start</th>
                                                    <th>Department</th>
                                                    <th>Kiosk code</th>
                                                    <th>Date added</th>
                                                    <th>Added by</th>
                                                    <th class="text-end">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody id="directory-users-tbody">
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <!-- EDITABLE CONNECTEAM USER PROFILE DASHBOARD VIEW -->
                            <div id="user-profile-dashboard-view" style="display:none;" class="mt-2">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <button class="btn btn-outline-custom btn-sm" onclick="closeUserProfileDashboard()"><i class="bi bi-arrow-left me-1"></i> Back to Users Directory</button>
                                    <button class="btn btn-primary-custom btn-sm" onclick="saveAdminUserProfileEdit()"><i class="bi bi-check-lg me-1"></i> Save Profile Changes</button>
                                </div>

                                <div class="card-custom p-3 mb-4 d-flex justify-content-between align-items-center">
                                    <div class="d-flex align-items-center gap-3">
                                        <div class="avatar-circle bg-primary text-white fs-5" style="width: 44px; height: 44px;" id="profile-dashboard-avatar">AL</div>
                                        <div>
                                            <h5 class="fw-bold text-dark m-0 d-flex align-items-center gap-2" id="profile-dashboard-name">
                                                Alejandro Luanzon Jr.
                                                <span class="badge bg-light text-secondary border fw-normal fs-7" id="profile-dashboard-role">Admin</span>
                                            </h5>
                                        </div>
                                    </div>

                                    <div class="d-flex align-items-center gap-2">
                                        <div class="dropdown">
                                            <button class="btn btn-outline-custom btn-sm dropdown-toggle fw-bold" type="button" data-bs-toggle="dropdown">
                                                <i class="bi bi-person-gear me-1"></i> Change Role
                                            </button>
                                            <ul class="dropdown-menu dropdown-menu-end shadow-sm">
                                                <li><a class="dropdown-item fs-7" onclick="changeActiveUserRole('Admin')">Assign as Admin</a></li>
                                                <li><a class="dropdown-item fs-7" onclick="changeActiveUserRole('Manager')">Assign as Manager</a></li>
                                                <li><a class="dropdown-item fs-7" onclick="changeActiveUserRole('Employee')">Assign as Employee</a></li>
                                            </ul>
                                        </div>
                                        <button class="btn btn-outline-custom btn-sm text-success" id="unarchive-profile-btn" style="display:none;" onclick="unarchiveActiveUserProfile()"><i class="bi bi-arrow-counterclockwise me-1"></i> Un-archive User</button>
                                        <button class="btn btn-outline-custom btn-sm text-danger" id="archive-profile-btn" onclick="archiveActiveUserProfile()"><i class="bi bi-archive me-1"></i> Archive User</button>
                                    </div>
                                </div>

                                <div class="row g-4">
                                    <div class="col-md-3">
                                        <div class="card-custom p-3 mb-3">
                                            <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Personal Details</h6>
                                            <input type="hidden" id="edit-user-original-empid">
                                            <input type="hidden" id="edit-user-original-dept">
                                            <div class="mb-3">
                                                <label class="form-label text-muted fw-semibold mb-1" style="font-size:11px;">FIRST NAME *</label>
                                                <input type="text" class="form-control" id="edit-user-firstname">
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label text-muted fw-semibold mb-1" style="font-size:11px;">LAST NAME *</label>
                                                <input type="text" class="form-control" id="edit-user-lastname">
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label text-muted fw-semibold mb-1" style="font-size:11px;">MOBILE PHONE *</label>
                                                <input type="text" class="form-control" id="edit-user-mobile">
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label text-muted fw-semibold mb-1" style="font-size:11px;">EMAIL *</label>
                                                <input type="email" class="form-control" id="edit-user-email">
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label text-muted fw-semibold mb-1" style="font-size:11px;">EMPLOYEE ID *</label>
                                                <input type="text" class="form-control" id="edit-user-empid">
                                            </div>
                                        </div>

                                        <div class="card-custom p-3 mb-3">
                                            <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Company Related Info</h6>
                                            <div class="mb-3">
                                                <label class="form-label text-muted fw-semibold mb-1" style="font-size:11px;">DEPARTMENT (SMART GROUP SUB-GROUP)</label>
                                                <select class="form-select" id="edit-user-department">
                                                </select>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label text-muted fw-semibold mb-1" style="font-size:11px;">SYSTEM ROLE</label>
                                                <select class="form-select" id="edit-user-role">
                                                    <option value="Employee">Employee</option>
                                                    <option value="Manager">Manager</option>
                                                    <option value="Admin">Admin</option>
                                                </select>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="col-md-9">
                                        <div class="card-custom p-4">
                                            <ul class="nav nav-tabs nav-tabs-connecteam border-bottom mb-4" id="userProfileSubTabs">
                                                <li class="nav-item"><a class="nav-link active" onclick="switchProfileTab('employment')">Employment</a></li>
                                                <li class="nav-item"><a class="nav-link" onclick="switchProfileTab('activity')">Activity</a></li>
                                                <li class="nav-item"><a class="nav-link" onclick="switchProfileTab('timeoff')">Time off</a></li>
                                                <li class="nav-item"><a class="nav-link" onclick="switchProfileTab('notes')">Notes</a></li>
                                            </ul>

                                            <div id="profile-subtab-employment">
                                                <h6 class="fw-bold text-dark mb-3">Compensation & Shift Policies</h6>
                                                <div class="p-3 bg-light rounded-3 border mb-4">
                                                    <div class="row g-3">
                                                        <div class="col-md-6"><small class="text-muted d-block">Worker Type</small><strong class="text-dark">Regular Staff</strong></div>
                                                        <div class="col-md-6"><small class="text-muted d-block">Pay Type</small><strong class="text-dark">Monthly Rate</strong></div>
                                                        <div class="col-md-6"><small class="text-muted d-block">Overtime Eligibility</small><strong class="text-dark">Eligible</strong></div>
                                                        <div class="col-md-6"><small class="text-muted d-block">Standard Hours</small><strong class="text-dark">8 hrs / day</strong></div>
                                                    </div>
                                                </div>
                                            </div>

                                            <div id="profile-subtab-activity" style="display:none;">
                                                <h6 class="fw-bold text-dark mb-3"><i class="bi bi-clock-history me-2 text-primary"></i> Clock In / Clock Out Activity</h6>
                                                <div class="table-responsive">
                                                    <table class="table align-middle">
                                                        <thead>
                                                            <tr>
                                                                <th>PUNCH TYPE</th>
                                                                <th>TIMESTAMP</th>
                                                                <th>LOCATION / ADDRESS</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody id="profile-activity-tbody">
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>

                                            <div id="profile-subtab-timeoff" style="display:none;">
                                                <h6 class="fw-bold text-dark mb-3"><i class="bi bi-calendar-event me-2 text-warning"></i> Time Off Requests</h6>
                                                <div class="p-3 bg-light rounded-3 border">
                                                    <p class="text-muted m-0 fs-7">No active time-off or leave requests submitted.</p>
                                                </div>
                                            </div>

                                            <div id="profile-subtab-notes" style="display:none;">
                                                <h6 class="fw-bold text-dark mb-3"><i class="bi bi-journal-text me-2 text-warning"></i> Administrative Notes</h6>
                                                <textarea class="form-control mb-3" id="profileUserNotesInput" rows="4" placeholder="Enter administrative notes for this user..."></textarea>
                                                <button class="btn btn-primary-custom btn-sm" onclick="showToast('Note saved for user.')">Save Note</button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- TAB FORMS: IT FORMS / ADMIN FORMS / HR FORMS -->
                        <div id="tab-forms-view" style="display:none;">
                            <!-- LIST VIEW -->
                            <div id="forms-list-container">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <div class="d-flex align-items-center gap-3">
                                        <ul class="nav nav-tabs nav-tabs-connecteam border-0 m-0" id="formsCategoryTabsBar">
                                            <!-- Dynamic Category Tabs rendered here -->
                                        </ul>
                                        <button class="btn btn-outline-custom btn-sm fw-bold" onclick="openCreateCategoryModal()"><i class="bi bi-plus-lg me-1"></i> Create new category</button>
                                    </div>
                                    <div class="d-flex align-items-center gap-2">
                                        <small class="text-muted">Permissions</small>
                                        <div class="avatar-circle bg-dark text-white" style="width:28px; height:28px; font-size:11px;">SA</div>
                                    </div>
                                </div>

                                <div class="card-custom p-0 overflow-hidden mb-4">
                                    <div class="p-3 border-bottom d-flex justify-content-between align-items-center flex-wrap gap-2">
                                        <ul class="nav nav-tabs nav-tabs-connecteam border-0 m-0">
                                            <li class="nav-item">
                                                <a class="nav-link active" id="form-tab-active" onclick="switchFormTabStatus('ACTIVE')"><i class="bi bi-check-circle me-1"></i> Active (<span id="count-active-forms">5</span>)</a>
                                            </li>
                                            <li class="nav-item">
                                                <a class="nav-link" id="form-tab-archived" onclick="switchFormTabStatus('ARCHIVED')"><i class="bi bi-archive me-1"></i> Archived (<span id="count-archived-forms">16</span>)</a>
                                            </li>
                                        </ul>

                                        <button class="btn btn-primary-custom" onclick="openFormSourceModal()"><i class="bi bi-plus-lg me-1"></i> Add new</button>
                                    </div>

                                    <div class="p-3 border-bottom d-flex align-items-center gap-2">
                                        <div class="input-group" style="width: 260px;">
                                            <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
                                            <input type="text" class="form-control border-start-0" id="searchFormsInput" placeholder="Search" onkeyup="filterCustomFormsList(this.value)">
                                        </div>
                                        <button class="btn btn-outline-custom p-2" title="Filter"><i class="bi bi-funnel"></i></button>
                                    </div>

                                    <div class="table-responsive">
                                        <table class="table table-hover align-middle m-0">
                                            <thead>
                                                <tr>
                                                    <th width="30"><input type="checkbox" class="form-check-input"></th>
                                                    <th>Name</th>
                                                    <th>Status</th>
                                                    <th>Entries</th>
                                                    <th>Views</th>
                                                    <th>Assigned to</th>
                                                    <th>Created by</th>
                                                    <th>Administrated by</th>
                                                    <th>Date Created</th>
                                                </tr>
                                            </thead>
                                            <tbody id="custom-forms-tbody">
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <!-- FORM DETAIL / SUBMISSIONS VIEW -->
                            <div id="form-detail-submissions-container" style="display:none;">
                                <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                                    <div class="d-flex align-items-center gap-2">
                                        <button class="btn btn-outline-custom btn-sm me-2" onclick="closeFormDetailSubmissions()"><i class="bi bi-arrow-left"></i></button>
                                        <i class="bi bi-file-earmark-text text-primary fs-4"></i>
                                        <h4 class="fw-bold text-dark m-0" id="selected-form-title">Email Requisition Form</h4>
                                        <span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2 py-1 fs-7">Published</span>
                                    </div>

                                    <div class="d-flex align-items-center gap-2">
                                        <small class="text-muted">Permissions</small>
                                        <div class="avatar-circle bg-dark text-white" style="width:28px; height:28px; font-size:11px;">SA</div>
                                        <button class="btn btn-outline-custom btn-sm"><i class="bi bi-phone me-1"></i> Preview</button>
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Form Editor opened')"><i class="bi bi-pencil me-1"></i> Edit form</button>
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Form Settings opened')"><i class="bi bi-gear me-1"></i> Settings</button>
                                        <button class="btn btn-outline-custom btn-sm"><i class="bi bi-three-dots"></i></button>
                                        <span class="badge bg-light text-dark border px-2 py-1 fs-7"><i class="bi bi-mortarboard me-1 text-primary"></i> 0 / 4</span>
                                    </div>
                                </div>

                                <div class="card-custom p-0 overflow-hidden">
                                    <div class="p-3 border-bottom">
                                        <ul class="nav nav-tabs nav-tabs-connecteam border-0 m-0">
                                            <li class="nav-item"><a class="nav-link active" id="form-detail-tab-sub">Submissions</a></li>
                                            <li class="nav-item"><a class="nav-link" id="form-detail-tab-usr">Users</a></li>
                                            <li class="nav-item"><a class="nav-link" id="form-detail-tab-sum">Summary</a></li>
                                            <li class="nav-item"><a class="nav-link" id="form-detail-tab-act">Activity</a></li>
                                        </ul>
                                    </div>

                                    <div class="p-3 border-bottom d-flex align-items-center justify-content-between flex-wrap gap-2">
                                        <div class="d-flex align-items-center gap-2">
                                            <div class="btn-group" role="group">
                                                <button class="btn btn-outline-custom btn-sm active fw-bold">Table</button>
                                                <button class="btn btn-outline-custom btn-sm fw-bold">Inbox</button>
                                            </div>
                                            <div class="input-group input-group-sm" style="width: 200px;">
                                                <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
                                                <input type="text" class="form-control border-start-0" placeholder="Search">
                                            </div>
                                            <button class="btn btn-outline-custom btn-sm p-1 px-2"><i class="bi bi-funnel"></i></button>
                                            <input type="text" class="form-control form-control-sm text-center" value="06/11/2024 - 09/18/2026" style="width: 170px;">
                                            <small class="text-muted ms-2">Group by</small>
                                            <select class="form-select form-select-sm" style="width:100px;">
                                                <option>None</option>
                                            </select>
                                        </div>

                                        <div class="d-flex align-items-center gap-3">
                                            <span class="fw-bold text-dark fs-7"><span id="form-submission-count-label">151</span> submissions</span>
                                            <button class="btn btn-outline-custom btn-sm" onclick="showToast('Exporting submissions report...')"><i class="bi bi-box-arrow-up"></i></button>
                                        </div>
                                    </div>

                                    <div class="table-responsive">
                                        <table class="table table-hover align-middle m-0 fs-7">
                                            <thead>
                                                <tr>
                                                    <th width="30"><input type="checkbox" class="form-check-input"></th>
                                                    <th>Submitted By</th>
                                                    <th>Date & Time</th>
                                                    <th>Smart Group</th>
                                                    <th>Status</th>
                                                    <th class="text-end">Action</th>
                                                </tr>
                                            </thead>
                                            <tbody id="form-submissions-tbody">
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TIME CLOCK HISTORY DETAIL POPUP MODAL -->
        <div class="modal fade" id="historyDetailModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <div class="d-flex align-items-center gap-2">
                            <i class="bi bi-geo-alt-fill text-warning fs-5"></i>
                            <h6 class="modal-title fw-bold text-dark m-0" id="modalHistoryEmpName">Employee Punch Location Tracker</h6>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="row g-4 mb-3">
                            <div class="col-md-6">
                                <div id="modalHistoryMap"></div>
                            </div>
                            <div class="col-md-6">
                                <div class="card-custom p-3 bg-light">
                                    <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Punch Log Summary</h6>
                                    <div class="mb-2"><small class="text-muted d-block">Employee ID</small><strong class="text-dark" id="modalHistEmpId">--</strong></div>
                                    <div class="mb-2"><small class="text-muted d-block">Brand & Department</small><strong class="text-dark" id="modalHistDept">--</strong></div>
                                    <div class="mb-2"><small class="text-muted d-block">Job Title / Duty Role</small><strong class="text-dark" id="modalHistJob">--</strong></div>
                                    <div class="mb-2"><small class="text-muted d-block">Clock In Timestamp</small><span class="badge bg-success-subtle text-success border fw-semibold" id="modalHistClockIn">--</span></div>
                                    <div class="mb-2"><small class="text-muted d-block">Clock Out Timestamp</small><span class="badge bg-secondary-subtle text-secondary border fw-semibold" id="modalHistClockOut">--</span></div>
                                    <div class="mb-2"><small class="text-muted d-block">Daily Total Elapsed</small><strong class="text-primary fs-6" id="modalHistTotal">--</strong></div>
                                    <div class="mb-0"><small class="text-muted d-block">GPS Address Location</small><small class="text-secondary fw-medium" id="modalHistAddress">--</small></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- PENDING APPROVALS MODAL -->
        <div class="modal fade" id="pendingApprovalsModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Pending & Denied User Access Requests</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="table-responsive" style="max-height: 350px; overflow-y: auto;">
                            <table class="table align-middle m-0">
                                <thead>
                                    <tr>
                                        <th>APPLICANT</th>
                                        <th>EMAIL</th>
                                        <th>STATUS</th>
                                        <th class="text-end">ACTIONS</th>
                                    </tr>
                                </thead>
                                <tbody id="pending-approvals-tbody">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- DIRECT ADD USER MODAL -->
        <div class="modal fade" id="directAddUserModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Add New User to Directory</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="row g-2 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">FIRST NAME *</label>
                                <input type="text" class="form-control" id="modalNewUserFirstName" required placeholder="e.g. Juan">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">LAST NAME *</label>
                                <input type="text" class="form-control" id="modalNewUserLastName" required placeholder="e.g. Dela Cruz">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">EMPLOYEE ID *</label>
                            <input type="text" class="form-control" id="modalNewUserEmpId" required placeholder="e.g. EMP010">
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">EMAIL ADDRESS *</label>
                            <input type="email" class="form-control" id="modalNewUserEmail" required placeholder="e.g. juan@bigtimeempire.com">
                        </div>
                        <div class="row g-2 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">DEPARTMENT (SUB-GROUP)</label>
                                <select class="form-select" id="modalNewUserDept">
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">ROLE</label>
                                <select class="form-select" id="modalNewUserRole">
                                    <option value="Employee">Employee</option>
                                    <option value="Manager">Manager</option>
                                    <option value="Admin">Admin</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="saveDirectNewUser()">Create Employee Account</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- POP-OUT SUB-GROUP DRILLDOWN OFFCANVAS DRAWER -->
        <div class="offcanvas offcanvas-end offcanvas-group-drawer" tabindex="-1" id="groupDetailDrawer" aria-labelledby="groupDetailDrawerLabel">
            <div class="offcanvas-header border-bottom p-4 d-flex justify-content-between align-items-center bg-light">
                <div class="d-flex align-items-center gap-2">
                    <h5 class="offcanvas-title fw-bold text-dark m-0" id="detail-group-title">HO - Admin</h5>
                    <button class="btn btn-sm btn-outline-custom py-1 px-2" onclick="openRenameGroupModal()"><i class="bi bi-pencil me-1"></i> Edit Name</button>
                </div>
                <button type="button" class="btn-close text-reset" data-bs-dismiss="offcanvas" aria-label="Close"></button>
            </div>
            <div class="offcanvas-body p-4">
                <div class="mb-4">
                    <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">ASSIGN GROUP ADMINS / MANAGERS</label>
                    <div class="dropdown" id="groupAdminDropdownWrapper">
                        <button class="btn btn-outline-custom w-100 text-start d-flex justify-content-between align-items-center py-2" type="button" id="groupAdminDropdownBtn" data-bs-toggle="dropdown" data-bs-auto-close="outside" aria-expanded="false">
                            <span id="groupAdminDropdownLabel" class="text-truncate fw-medium fs-7">Select Group Admins / Managers...</span>
                            <i class="bi bi-chevron-down text-muted fs-7"></i>
                        </button>
                        <div class="dropdown-menu p-3 w-100 shadow border-0" aria-labelledby="groupAdminDropdownBtn" style="max-height: 320px; overflow-y: auto;">
                            <input type="text" class="form-control form-control-sm mb-2" id="searchGroupAdminInput" placeholder="Search managers & admins..." onkeyup="filterGroupAdminDropdownList(this.value)">
                            <div id="groupAdminCheckboxesContainer" class="d-flex flex-column gap-2 mt-2">
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row g-3 mb-4">
                    <div class="col-md-4">
                        <div class="card-custom p-3">
                            <small class="text-muted fw-semibold d-block">Employees in group</small>
                            <h3 class="fw-bold text-dark m-0 mt-1" id="detail-emp-count">0</h3>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card-custom p-3">
                            <small class="text-muted fw-semibold d-block">Clocked In Currently</small>
                            <h3 class="fw-bold text-success m-0 mt-1" id="detail-logged-count">0 / 0</h3>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card-custom p-3">
                            <small class="text-muted fw-semibold d-block">Created info</small>
                            <small class="fw-bold text-dark d-block mt-1">06/05/2026 by Super Admin</small>
                        </div>
                    </div>
                </div>

                <div class="d-flex align-items-center gap-2 mb-4">
                    <span class="text-muted fw-semibold" style="font-size: 12px;">Group filtered by</span>
                    <span class="filter-pill" id="filter-brand-pill">Location is Head Office</span>
                    <span class="filter-pill" id="filter-dept-pill">Department is Admin</span>
                    <button class="btn btn-link btn-sm text-primary fw-bold text-decoration-none p-0 ms-2" onclick="showToast('Filter editor opened.')">Edit filters</button>
                </div>

                <div class="card-custom p-3 mb-4 bg-light">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="fw-bold text-dark m-0" style="font-size:13px;"><i class="bi bi-briefcase me-2 text-warning"></i> Department Specific Jobs (Mobile Clock-In)</h6>
                        <button class="btn btn-sm btn-outline-custom py-0 px-2" onclick="openAddDepartmentJobModal()"><i class="bi bi-plus-lg"></i> Add Job</button>
                    </div>
                    <div id="dept-jobs-chips-container" class="d-flex flex-wrap gap-1">
                    </div>
                </div>

                <div class="card-custom p-0 overflow-hidden">
                    <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                        <input type="text" class="form-control" style="width: 260px;" placeholder="Search group members..." onkeyup="filterDetailMembers(this.value)">
                    </div>
                    <div class="table-responsive">
                        <table class="table align-middle m-0">
                            <thead>
                                <tr>
                                    <th>First name</th>
                                    <th>Last name</th>
                                    <th>Last login</th>
                                    <th>Department</th>
                                    <th>Kiosk code</th>
                                </tr>
                            </thead>
                            <tbody id="detail-members-tbody">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- ADD BRAND MODAL -->
        <div class="modal fade" id="addBrandModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Add Central Brand Location</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">BRAND NAME (e.g. HEAD OFFICE, STORES, COMMISSARY)</label>
                        <input type="text" class="form-control" id="modalNewBrandName" placeholder="e.g. WAREHOUSE">
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="saveNewBrandModal()">Save Brand</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- ADD DEPARTMENT JOB MODAL -->
        <div class="modal fade" id="addDepartmentJobModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Add Specific Job Title to Department</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">JOB TITLE NAME</label>
                        <input type="text" class="form-control" id="modalNewDeptJobTitle" placeholder="e.g. Junior Systems Administrator">
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="saveNewDeptJobTitle()">Save Job Title</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- FORM SOURCE SELECTION MODAL (#formSourceModal) -->
        <div class="modal fade" id="formSourceModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0"><i class="bi bi-file-earmark-plus me-2 text-primary"></i>Add New Form — Choose Source</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <div class="card p-3 border text-center h-100 feed-card-hover" onclick="selectFormSource('scratch')">
                                    <i class="bi bi-file-earmark-plus-fill fs-1 text-primary mb-2"></i>
                                    <h6 class="fw-bold text-dark">Start from Scratch</h6>
                                    <small class="text-muted">Build a custom form field-by-field</small>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card p-3 border text-center h-100 feed-card-hover" onclick="selectFormSource('template')">
                                    <i class="bi bi-journal-bookmark-fill fs-1 text-warning mb-2"></i>
                                    <h6 class="fw-bold text-dark">Use a Template</h6>
                                    <small class="text-muted">Pre-load standard HR/IT schema fields</small>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card p-3 border text-center h-100 feed-card-hover" onclick="selectFormSource('file')">
                                    <i class="bi bi-file-earmark-arrow-up-fill fs-1 text-success mb-2"></i>
                                    <h6 class="fw-bold text-dark">Create from File</h6>
                                    <small class="text-muted">Upload CSV or JSON schema file</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- CREATE CATEGORY MODAL (#createCategoryModal) -->
        <div class="modal fade" id="createCategoryModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Create New Form Category</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">CATEGORY NAME</label>
                        <input type="text" class="form-control" id="modalNewCategoryName" placeholder="e.g. Operations Forms">
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="submitCreateCategory()">Create Category</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- EDIT CATEGORY MODAL (#editCategoryModal) -->
        <div class="modal fade" id="editCategoryModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered" style="max-width: 440px;">
                <div class="modal-content border-0 shadow-lg p-3" style="border-radius: 18px;">
                    <div class="modal-header border-0 pb-0 pt-2 px-3 align-items-center">
                        <h5 class="modal-title fw-bold text-dark m-0" style="font-size: 20px;">Rename Form Category</h5>
                        <button type="button" class="btn-close text-muted" data-bs-dismiss="modal" aria-label="Close" style="font-size: 12px; background-color: #f1f3f5; border-radius: 50%; padding: 8px;"></button>
                    </div>
                    <div class="modal-body px-3 py-3">
                        <input type="hidden" id="editCategoryId">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 11px; letter-spacing: 0.5px;">CATEGORY NAME</label>
                        <input type="text" class="form-control" id="editCategoryNewName" placeholder="e.g. IT Support Forms" style="border-radius: 8px; padding: 10px 12px;">
                    </div>
                    <div class="modal-footer border-0 pt-0 pb-2 px-3 d-flex justify-content-end gap-2">
                        <button type="button" class="btn btn-light fw-medium border" data-bs-dismiss="modal" style="border-radius: 10px; padding: 8px 18px; color: #333; background: #fff;">Cancel</button>
                        <button type="button" class="btn btn-primary fw-medium" onclick="submitEditCategory()" style="border-radius: 10px; padding: 8px 18px; background-color: #007bff; border: none;">Save changes</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- CONFIRM DELETE CATEGORY MODAL (#confirmDeleteCategoryModal) -->
        <div class="modal fade" id="confirmDeleteCategoryModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered" style="max-width: 440px;">
                <div class="modal-content border-0 shadow-lg p-3" style="border-radius: 18px;">
                    <div class="modal-header border-0 pb-0 pt-2 px-3 align-items-center">
                        <h5 class="modal-title fw-bold text-dark m-0" style="font-size: 20px;">Delete category?</h5>
                        <button type="button" class="btn-close text-muted" data-bs-dismiss="modal" aria-label="Close" style="font-size: 12px; background-color: #f1f3f5; border-radius: 50%; padding: 8px;"></button>
                    </div>
                    <div class="modal-body px-3 py-3">
                        <input type="hidden" id="deleteCategoryName">
                        <p class="m-0 text-muted" style="font-size: 14px; line-height: 1.5;">This will permanently delete category <strong id="deleteCategoryLabel" class="text-dark"></strong> and all associated forms. This action cannot be undone.</p>
                    </div>
                    <div class="modal-footer border-0 pt-0 pb-2 px-3 d-flex justify-content-end gap-2">
                        <button type="button" class="btn btn-light fw-medium border" data-bs-dismiss="modal" style="border-radius: 10px; padding: 8px 18px; color: #333; background: #fff;">Cancel</button>
                        <button type="button" class="btn btn-danger fw-medium" onclick="submitDeleteCategory()" style="border-radius: 10px; padding: 8px 18px; background-color: #f02849; border: none;">Delete category</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- EDIT ASSIGNMENTS DRAWER (#editAssignmentsModal) -->
        <div class="offcanvas offcanvas-end offcanvas-group-drawer" tabindex="-1" id="editAssignmentsModal">
            <div class="offcanvas-header border-bottom p-4 d-flex justify-content-between align-items-center bg-light">
                <h5 class="offcanvas-title fw-bold text-dark m-0">Edit Form Assignments</h5>
                <button type="button" class="btn-close text-reset" data-bs-dismiss="offcanvas"></button>
            </div>
            <div class="offcanvas-body p-4">
                <input type="hidden" id="assignmentFormId">
                <div class="mb-4">
                    <label class="form-label fw-semibold text-secondary fs-7">TARGET SMART GROUPS</label>
                    <div class="form-check mb-2">
                        <input class="form-check-input assignment-group-check" type="checkbox" value="All users group" id="assign_group_all">
                        <label class="form-check-label fw-semibold" for="assign_group_all">All users group</label>
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input assignment-group-check" type="checkbox" value="HO - I.T." id="assign_group_it">
                        <label class="form-check-label fw-semibold" for="assign_group_it">HO - I.T.</label>
                    </div>
                    <div class="form-check mb-2">
                        <input class="form-check-input assignment-group-check" type="checkbox" value="Management Group" id="assign_group_mgmt">
                        <label class="form-check-label fw-semibold" for="assign_group_mgmt">Management Group</label>
                    </div>
                </div>
                <div class="mb-4">
                    <label class="form-label fw-semibold text-secondary fs-7">MEMBERSHIP TYPE</label>
                    <div class="btn-group w-100" role="group">
                        <input type="radio" class="btn-check" name="membershipType" id="memDynamic" checked>
                        <label class="btn btn-outline-secondary" for="memDynamic">Dynamic</label>
                        <input type="radio" class="btn-check" name="membershipType" id="memFixed">
                        <label class="btn btn-outline-secondary" for="memFixed">Fixed</label>
                    </div>
                </div>
                <button type="button" class="btn btn-primary-custom w-100 py-2" onclick="submitAssignmentsDrawer()">Save Assignments</button>
            </div>
        </div>

        <!-- CREATE CUSTOM FORM MODAL BUILDER -->
        <div class="modal fade" id="createCustomFormModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0"><i class="bi bi-file-earmark-plus me-2 text-primary"></i>Create Custom Form</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <label class="form-label fw-semibold text-secondary fs-7">FORM NAME</label>
                                <input type="text" class="form-control" id="builderFormName" placeholder="e.g. Equipment Request Form">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-semibold text-secondary fs-7">CATEGORY</label>
                                <select class="form-select" id="builderFormCategory">
                                    <option value="IT Forms">IT Forms</option>
                                    <option value="Admin Forms">Admin Forms</option>
                                    <option value="HR Forms">HR Forms</option>
                                </select>
                            </div>
                        </div>

                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <h6 class="fw-bold text-dark m-0 fs-7">FORM FIELDS</h6>
                            <button type="button" class="btn btn-outline-primary btn-sm" onclick="addBuilderField()">
                                <i class="bi bi-plus-lg me-1"></i>Add Field
                            </button>
                        </div>

                        <div id="builderFieldsContainer" class="d-flex flex-column gap-3 mb-3" style="max-height: 380px; overflow-y: auto;">
                            <!-- Dynamic fields inserted here -->
                        </div>
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="submitCustomFormBuilder()">Save & Publish Form</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- ADD / EDIT GROUP FORM MODAL -->
        <div class="modal fade" id="groupModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Add Group</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="mb-3">
                            <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">GROUP NAME (DEPARTMENT)</label>
                            <input type="text" class="form-control" id="modalGroupName" placeholder="e.g. HO - Accounting">
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">BRAND LOCATION</label>
                            <select class="form-select" id="modalBrandSelect">
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="saveSmartGroup()">Save Smart Group</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- RENAME BRAND MODAL -->
        <div class="modal fade" id="renameBrandModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Rename Main Brand Location</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">NEW BRAND NAME</label>
                        <input type="text" class="form-control" id="modalRenameBrandName" placeholder="e.g. HEAD OFFICE">
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="saveRenameBrand()">Update Brand Name</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- RENAME GROUP MODAL -->
        <div class="modal fade" id="renameGroupModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Rename Group</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">NEW GROUP NAME</label>
                        <input type="text" class="form-control" id="modalRenameGroupName" placeholder="e.g. HO - Administration">
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="saveRenameGroup()">Update Name</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- TOAST CONTAINER -->
        <div class="toast-container position-fixed bottom-0 end-0 p-3" style="z-index: 1080;">
            <div id="liveToast" class="toast align-items-center border-0 shadow-sm text-white bg-dark" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body fw-medium" id="toastMessage" style="font-size: 13px;"></div>
                    <button type="button" class="btn-close me-2 m-auto btn-close-white" data-bs-dismiss="toast"></button>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let map, markersGroup, mapMarkerDict = {}, modalMap, modalMarkerGroup;
            let currentBsModal, currentOffcanvasDrawer;
            let adminToken = '';
            let globalUsersList = [];
            let activeGroupName = 'HO - Admin';
            let selectedBrandView = 'ALL';
            let editingBrandNameTarget = '';
            let rawActivePunchesList = [];
            let rawFullPunchesLogs = [];
            let activeDirectoryCategoryFilter = 'APPROVED';
            let currentActiveProfileUser = null;
            let globalPairedHistoryStore = [];

            const defaultBrandsInitial = ['Head Office', 'Stores', 'Commissary'];

            const defaultGroupsInitial = [
                { name: 'HO - IT', creator: 'Jaypee Balonzo', selected: '17 selected', brand: 'Head Office', dept: 'IT' },
                { name: 'HO - Marketing', creator: 'Jaypee Balonzo', selected: '13 selected', brand: 'Head Office', dept: 'Marketing' },
                { name: 'HO - Admin', creator: 'Jaypee Balonzo', selected: '15 selected', brand: 'Head Office', dept: 'Admin' },
                { name: 'HO - Human Resource', creator: 'Jaypee Balonzo', selected: '14 selected', brand: 'Head Office', dept: 'HR' },
                { name: 'HO - Accounting', creator: 'Jaypee Balonzo', selected: '13 selected', brand: 'Head Office', dept: 'Accounting' },
                { name: 'HO - Sales', creator: 'Jaypee Balonzo', selected: '12 selected', brand: 'Head Office', dept: 'Sales' }
            ];

            async function updateTopBarUserHeader() {
                const token = await getAdminAuthToken();
                if (!token) return;
                try {
                    const res = await fetch('/api/auth/me', { headers: { 'Authorization': 'Bearer ' + token } });
                    if (res.ok) {
                        const me = await res.json();
                        const name = me.name || (me.first_name ? `${me.first_name} ${me.last_name || ''}` : me.employee_id);
                        const role = me.role || me.position || 'User';
                        const empId = me.employee_id || '';
                        const initials = name.split(' ').map(n=>n[0]).join('').substring(0,2).toUpperCase();

                        const avatarEl = document.querySelector('.top-bar .avatar-circle');
                        const nameEl = document.getElementById('topbar-user-name');
                        const subEl = document.querySelector('.top-bar .text-start small');

                        if (avatarEl) avatarEl.innerText = initials || 'U';
                        if (nameEl) nameEl.innerText = name;
                        if (subEl) subEl.innerText = `${role} (${empId})`;
                    }
                } catch(e) {}
            }

            function checkAuthentication() {
                const session = localStorage.getItem('atwork_session_active');
                if (!session) {
                    document.getElementById('portal-main-view').style.display = 'none';
                    document.getElementById('login-overlay-page').style.display = 'flex';
                } else {
                    document.getElementById('login-overlay-page').style.display = 'none';
                    document.getElementById('portal-main-view').style.display = 'block';
                    updateTopBarUserHeader();
                }
            }

            async function handleAdminLogin(e) {
                e.preventDefault();
                const empId = document.getElementById('loginEmpId').value.trim();
                const pwd = document.getElementById('loginPassword').value.trim();

                try {
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ employee_id: empId, password: pwd })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        adminToken = data.access_token;
                        localStorage.setItem('atwork_jwt_token', adminToken);
                        localStorage.setItem('atwork_session_active', 'true');
                        showToast('Successfully authenticated into atWork.');
                        checkAuthentication();
                        await renderBrandSelectorOptions();
                        await renderConnecteamProvisioningTable();
                    } else {
                        showToast('Invalid Employee ID or Password.');
                    }
                } catch(err) {
                    showToast('Server connection error.');
                }
            }

            function performSignOut() {
                localStorage.removeItem('atwork_session_active');
                localStorage.removeItem('atwork_jwt_token');
                adminToken = '';
                showToast('Signed out of atWork.');
                checkAuthentication();
            }

            function toggleLoginPassword() {
                const pwdInput = document.getElementById('loginPassword');
                const icon = document.getElementById('passwordToggleIcon');
                if (pwdInput.type === 'password') {
                    pwdInput.type = 'text';
                    icon.className = 'bi bi-eye-slash';
                } else {
                    pwdInput.type = 'password';
                    icon.className = 'bi bi-eye';
                }
            }

            async function getStoredBrands() {
                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/jobs/brands', { headers: { 'Authorization': 'Bearer ' + token } });
                    if (res.ok) return await res.json();
                } catch(e) {}
                return ['Head Office', 'Stores', 'Commissary'];
            }

            async function getStoredGroups() {
                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/jobs/groups', { headers: { 'Authorization': 'Bearer ' + token } });
                    if (res.ok) return await res.json();
                } catch(e) {}
                return [];
            }

            function getDeptJobsStore(groupName) {
                const key = 'dept_jobs_' + groupName;
                const stored = localStorage.getItem(key);
                if (stored) {
                    try { return JSON.parse(stored); } catch(e) {}
                }
                return ['IT Support', 'System Administrator', 'Technical Specialist'];
            }

            function setDeptJobsStore(groupName, jobs) {
                const key = 'dept_jobs_' + groupName;
                localStorage.setItem(key, JSON.stringify(jobs));
            }

            async function populateDepartmentDropdownOptions(selectedVal) {
                const allGroups = await getStoredGroups();
                let optionsHtml = '';
                if (Array.isArray(allGroups)) {
                    allGroups.forEach(g => {
                        const isSel = (g.name === selectedVal || g.dept === selectedVal) ? 'selected' : '';
                        optionsHtml += `<option value="${g.name}" ${isSel}>${g.name}</option>`;
                    });
                }
                document.getElementById('edit-user-department').innerHTML = optionsHtml;
                document.getElementById('modalNewUserDept').innerHTML = optionsHtml;
            }

            function showToast(msg) {
                document.getElementById('toastMessage').innerText = msg;
                const toast = new bootstrap.Toast(document.getElementById('liveToast'), { delay: 3500 });
                toast.show();
            }

            async function getAdminAuthToken() {
                if (adminToken) return adminToken;
                const savedToken = localStorage.getItem('atwork_jwt_token');
                if (savedToken) {
                    adminToken = savedToken;
                    return adminToken;
                }
                return '';
            }

            function switchTab(tab, updateUrl = true) {
                document.getElementById('tab-clock').style.display = 'none';
                document.getElementById('tab-jobs').style.display = 'none';
                document.getElementById('tab-users').style.display = 'none';
                const formsView = document.getElementById('tab-forms-view');
                if (formsView) formsView.style.display = 'none';

                document.getElementById('nav-clock').classList.remove('active');
                document.getElementById('nav-jobs').classList.remove('active');
                document.getElementById('nav-users').classList.remove('active');

                if (tab === 'forms-view' || tab.startsWith('forms-')) {
                    if (formsView) formsView.style.display = 'block';

                    let finalCatName = currentFormCategory;
                    if (!finalCatName) {
                        const catName = tab.replace('forms-', '').replace(/-/g, ' ');
                        const matchedCat = availableCategoriesList.find(c => c.name.toLowerCase() === catName.toLowerCase());
                        if (matchedCat) {
                            finalCatName = matchedCat.name;
                        } else if (availableCategoriesList.length > 0) {
                            finalCatName = availableCategoriesList[0].name;
                        } else {
                            finalCatName = 'Forms';
                        }
                    }

                    currentFormCategory = finalCatName;
                    document.getElementById('page-title').innerText = finalCatName;
                    const headerTitleEl = document.getElementById('forms-category-header-title');
                    if (headerTitleEl) headerTitleEl.innerText = finalCatName;

                    if (updateUrl && finalCatName !== 'Forms') {
                        const urlSlug = finalCatName.toLowerCase().replace(/\s+/g, '-');
                        history.pushState(null, '', '/admin/forms/category/modules/' + urlSlug);
                    }
                    closeFormDetailSubmissions();
                    loadCustomForms(finalCatName);
                    return;
                }

                document.getElementById('tab-' + tab).style.display = 'block';
                const navBtn = document.getElementById('nav-' + tab);
                if (navBtn) navBtn.classList.add('active');

                if (tab === 'clock') {
                    if (updateUrl) history.pushState(null, '', '/admin/timeclock');
                    document.getElementById('page-title').innerText = 'Time Clock';
                    setTimeout(() => { if (map) map.invalidateSize(); else initMap(); }, 200);
                    loadPunchMap();
                    loadTimeClockHistory();
                } else if (tab === 'jobs') {
                    if (updateUrl) history.pushState(null, '', '/admin/smart-groups');
                    document.getElementById('page-title').innerText = 'Smart Groups';
                    loadConnecteamDirectory().then(() => {
                        renderBrandSelectorOptions();
                        renderConnecteamProvisioningTable();
                    });
                } else if (tab === 'users') {
                    if (updateUrl) history.pushState(null, '', '/admin/users');
                    document.getElementById('page-title').innerText = 'Users Directory';
                    loadConnecteamDirectory();
                }
            }

            async function handleUrlRoutingOnLoad() {
                const path = window.location.pathname;
                if (path.includes('/admin/smart-groups')) {
                    switchTab('jobs', false);
                } else if (path.includes('/admin/users')) {
                    switchTab('users', false);
                } else if (path.includes('/admin/forms/category/modules/')) {
                    const slug = path.split('/admin/forms/category/modules/')[1];
                    if (slug) {
                        const catName = slug.replace(/-/g, ' ');
                        await selectFormCategoryTabBySlug(catName);
                    } else {
                        switchTab('clock', false);
                    }
                } else {
                    switchTab('clock', false);
                }
            }

            async function selectFormCategoryTabBySlug(catSlug) {
                if (!availableCategoriesList || availableCategoriesList.length === 0) {
                    await renderSidebarFormsCategories();
                }
                if (!availableCategoriesList || availableCategoriesList.length === 0) {
                    renderFormsBlankLandingPage();
                    return;
                }
                const matched = availableCategoriesList.find(c => catSlug && c.name.toLowerCase() === catSlug.toLowerCase());
                const targetCat = matched ? matched.name : availableCategoriesList[0].name;
                currentFormCategory = targetCat;
                localStorage.setItem('lastSelectedFormCategory', targetCat);
                switchTab('forms-' + targetCat.toLowerCase().replace(/\s+/g, '-'), false);
                await renderSidebarFormsCategories();
                await loadCustomForms(targetCat);
            }

            window.addEventListener('popstate', function() {
                handleUrlRoutingOnLoad();
            });

            function initMap() {
                if (map) return;
                map = L.map('map').setView([14.5995, 120.9842], 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '&copy; OpenStreetMap'
                }).addTo(map);
                markersGroup = L.layerGroup().addTo(map);
            }

            async function loadPunchMap() {
                try {
                    const res = await fetch('/api/punch/logs');
                    const logs = await res.json();
                    rawFullPunchesLogs = logs || [];
                    if (markersGroup) markersGroup.clearLayers();
                    mapMarkerDict = {};

                    const token = await getAdminAuthToken();
                    let usersMap = {};
                    try {
                        const uRes = await fetch('/api/auth/users', { headers: { 'Authorization': 'Bearer ' + token } });
                        if (uRes.ok) {
                            const uList = await uRes.json();
                            uList.forEach(u => { usersMap[u.employee_id] = u; });
                        }
                    } catch(err) {}

                    let latestPunchByEmp = {};
                    logs.forEach(log => {
                        const empId = log.employee_id;
                        if (!latestPunchByEmp[empId] || log.id > latestPunchByEmp[empId].id) {
                            latestPunchByEmp[empId] = log;
                        }
                    });

                    rawActivePunchesList = Object.values(latestPunchByEmp).filter(p => p.punch_type === 'CLOCK_IN');
                    renderLiveClockSidebar(rawActivePunchesList, usersMap);
                } catch(e) {}
            }

            function renderLiveClockSidebar(activePunches, usersMap = {}) {
                let sidebarHtml = '';
                if (!activePunches || activePunches.length === 0) {
                    sidebarHtml = '<p class="text-muted fs-7 py-3">No employees currently clocked in.</p>';
                } else {
                    activePunches.forEach(log => {
                        const emp = usersMap[log.employee_id] || {};
                        const fullName = emp.name || (emp.first_name ? `${emp.first_name} ${emp.last_name || ''}` : `Emp ID: ${log.employee_id}`);
                        const jobTitle = emp.position || emp.role || 'Staff';

                        sidebarHtml += `
                            <div class="p-3 mb-2 rounded-3 bg-white border feed-card-hover" onclick="focusMapMarker(${log.latitude}, ${log.longitude}, '${log.employee_id}')">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <div>
                                        <strong class="text-dark d-block" style="font-size: 13px;">${fullName}</strong>
                                        <small class="text-muted" style="font-size: 11px;">${jobTitle} (${log.employee_id})</small>
                                    </div>
                                    <span class="badge bg-success-subtle text-success" style="font-size: 10px;">CLOCK_IN</span>
                                </div>
                                <small class="text-muted d-block mt-1" style="font-size: 11px;"><i class="bi bi-clock me-1"></i>${log.timestamp}</small>
                                <small class="text-secondary text-truncate d-block" style="font-size: 11px;"><i class="bi bi-geo-alt me-1"></i>${log.address || 'Duty Shift'}</small>
                            </div>`;

                        if (markersGroup && log.latitude && log.longitude) {
                            const marker = L.marker([log.latitude, log.longitude])
                                .bindPopup(`<b>${fullName}</b><br>Job: ${jobTitle}<br>Time: ${log.timestamp}`)
                                .addTo(markersGroup);
                            mapMarkerDict[log.employee_id] = marker;
                        }
                    });
                }
                document.getElementById('punch-list-sidebar').innerHTML = sidebarHtml;
            }

            function focusMapMarker(lat, lng, empId) {
                if (map && lat && lng) {
                    map.setView([lat, lng], 17, { animate: true });
                    if (mapMarkerDict[empId]) {
                        mapMarkerDict[empId].openPopup();
                    }
                    showToast('Map centered on employee GPS location.');
                }
            }

            function filterLiveClockFeed(q) {
                const query = q.toLowerCase();
                const filtered = rawActivePunchesList.filter(p => 
                    (p.employee_id && p.employee_id.toLowerCase().includes(query)) ||
                    (p.address && p.address.toLowerCase().includes(query))
                );
                renderLiveClockSidebar(filtered);
            }

            async function loadTimeClockHistory() {
                let selDateInput = document.getElementById('historyDateFilter').value;
                if (!selDateInput) {
                    const todayStr = new Date().toISOString().split('T')[0];
                    document.getElementById('historyDateFilter').value = todayStr;
                    selDateInput = todayStr;
                }

                const parts = selDateInput.split('-');
                const filterMMDDYYYY = `${parts[1]}/${parts[2]}/${parts[0]}`;

                try {
                    const res = await fetch('/api/punch/logs');
                    const logs = await res.json();
                    rawFullPunchesLogs = logs || [];

                    const token = await getAdminAuthToken();
                    let usersMap = {};
                    try {
                        const uRes = await fetch('/api/auth/users', { headers: { 'Authorization': 'Bearer ' + token } });
                        if (uRes.ok) {
                            const uList = await uRes.json();
                            uList.forEach(u => { usersMap[u.employee_id] = u; });
                        }
                    } catch(err) {}

                    // Filter logs matching selected date
                    const filteredLogs = logs.filter(l => (l.timestamp && l.timestamp.includes(filterMMDDYYYY)) || (l.created_at && l.created_at.includes(selDateInput)));
                    
                    let empGrouped = {};
                    filteredLogs.forEach(l => {
                        if (!empGrouped[l.employee_id]) empGrouped[l.employee_id] = [];
                        empGrouped[l.employee_id].push(l);
                    });

                    globalPairedHistoryStore = [];

                    Object.keys(empGrouped).forEach(empId => {
                        const empPunches = empGrouped[empId].sort((a,b) => a.id - b.id);
                        const empInfo = usersMap[empId] || {};
                        const fullName = empInfo.name || (empInfo.first_name ? `${empInfo.first_name} ${empInfo.last_name || ''}` : empId);
                        const brand = 'Head Office';
                        const subGroup = empInfo.department || 'General';

                        // Get earliest CLOCK_IN and latest CLOCK_OUT of the day
                        let inPunches = empPunches.filter(p => p.punch_type === 'CLOCK_IN');
                        let outPunches = empPunches.filter(p => p.punch_type === 'CLOCK_OUT');

                        let clockInPunch = inPunches.length > 0 ? inPunches[0] : null;
                        let clockOutPunch = outPunches.length > 0 ? outPunches[outPunches.length - 1] : null;

                        let dailyTotalStr = '--';
                        if (clockInPunch && clockOutPunch) {
                            try {
                                const inTime = new Date(clockInPunch.timestamp);
                                const outTime = new Date(clockOutPunch.timestamp);
                                const diffMs = outTime - inTime;
                                if (!isNaN(diffMs) && diffMs > 0) {
                                    const diffHrs = (diffMs / (1000 * 60 * 60)).toFixed(1);
                                    dailyTotalStr = `${diffHrs} hrs`;
                                } else {
                                    dailyTotalStr = '0.5 hrs';
                                }
                            } catch(e) { dailyTotalStr = '8.0 hrs'; }
                        } else if (clockInPunch) {
                            dailyTotalStr = 'In Progress';
                        }

                        globalPairedHistoryStore.push({
                            employee_id: empId,
                            full_name: fullName,
                            brand: brand,
                            sub_group: subGroup,
                            job_title: empInfo.position || empInfo.role || 'Staff',
                            clock_in: clockInPunch ? clockInPunch.timestamp : '--',
                            clock_out: clockOutPunch ? clockOutPunch.timestamp : '--',
                            daily_total: dailyTotalStr,
                            latitude: clockInPunch ? clockInPunch.latitude : 14.5995,
                            longitude: clockInPunch ? clockInPunch.longitude : 120.9842,
                            address: clockInPunch ? (clockInPunch.address || 'Duty Station Location') : 'Standard Duty Location'
                        });
                    });

                    renderHistoryRows(globalPairedHistoryStore);
                } catch(e) {}
            }

            function renderHistoryRows(historyList) {
                let html = '';
                if (!historyList || historyList.length === 0) {
                    html = '<tr><td colspan="7" class="text-center text-muted py-4">No time clock history records found for selected date.</td></tr>';
                } else {
                    historyList.forEach((h, idx) => {
                        const initials = h.full_name.split(' ').map(n=>n[0]).join('').substring(0,2).toUpperCase();
                        html += `
                            <tr class="history-row-clickable" onclick="openHistoryDetailModal(${idx})">
                                <td><input type="checkbox" class="form-check-input" onclick="event.stopPropagation()"></td>
                                <td>
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="avatar-chip bg-primary text-white">${initials}</span>
                                        <strong class="text-dark">${h.full_name}</strong>
                                    </div>
                                </td>
                                <td><span class="badge bg-light text-dark border">${h.brand}</span></td>
                                <td><span class="badge bg-warning-subtle text-warning border">${h.sub_group}</span></td>
                                <td><small class="fw-semibold text-dark">${h.clock_in}</small></td>
                                <td><small class="fw-semibold text-dark">${h.clock_out}</small></td>
                                <td><strong class="text-success">${h.daily_total}</strong></td>
                            </tr>`;
                    });
                }
                document.getElementById('timeclock-history-tbody').innerHTML = html;
            }

            function openHistoryDetailModal(index) {
                const item = globalPairedHistoryStore[index];
                if (!item) return;

                document.getElementById('modalHistoryEmpName').innerText = `${item.full_name} — Punch Location Details`;
                document.getElementById('modalHistEmpId').innerText = item.employee_id;
                document.getElementById('modalHistDept').innerText = `${item.brand} • ${item.sub_group}`;
                document.getElementById('modalHistJob').innerText = item.job_title;
                document.getElementById('modalHistClockIn').innerText = item.clock_in;
                document.getElementById('modalHistClockOut').innerText = item.clock_out;
                document.getElementById('modalHistTotal').innerText = item.daily_total;
                document.getElementById('modalHistAddress').innerText = item.address;

                currentBsModal = new bootstrap.Modal(document.getElementById('historyDetailModal'));
                currentBsModal.show();

                setTimeout(() => {
                    if (modalMap) {
                        modalMap.remove();
                    }
                    const lat = item.latitude || 14.5995;
                    const lng = item.longitude || 120.9842;
                    modalMap = L.map('modalHistoryMap').setView([lat, lng], 16);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(modalMap);
                    L.marker([lat, lng]).bindPopup(`<b>${item.full_name}</b><br>${item.clock_in}`).addTo(modalMap).openPopup();
                }, 300);
            }

            function filterHistoryTable(q) {
                const query = q.toLowerCase();
                const filtered = globalPairedHistoryStore.filter(h => 
                    h.full_name.toLowerCase().includes(query) ||
                    h.employee_id.toLowerCase().includes(query) ||
                    h.sub_group.toLowerCase().includes(query)
                );
                renderHistoryRows(filtered);
            }

            async function renderBrandSelectorOptions() {
                const brands = await getStoredBrands();
                let filterHtml = '<option value="ALL">All Brands</option>';
                let modalHtml = '';

                if (Array.isArray(brands)) {
                    brands.forEach(b => {
                        const sel = (b === selectedBrandView) ? 'selected' : '';
                        filterHtml += `<option value="${b}" ${sel}>${b}</option>`;
                        modalHtml += `<option value="${b}">${b}</option>`;
                    });
                }

                document.getElementById('selectedBrandFilter').innerHTML = filterHtml;
                document.getElementById('modalBrandSelect').innerHTML = modalHtml;
            }

            function openAddBrandModal() {
                document.getElementById('modalNewBrandName').value = '';
                currentBsModal = new bootstrap.Modal(document.getElementById('addBrandModal'));
                currentBsModal.show();
            }

            async function saveNewBrandModal() {
                const bName = document.getElementById('modalNewBrandName').value.trim();
                if (!bName) {
                    showToast('Please enter a brand name.');
                    return;
                }

                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/jobs/brands', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({ name: bName })
                    });
                    if (res.ok) {
                        await renderBrandSelectorOptions();
                        await renderConnecteamProvisioningTable();
                        showToast(`New Brand "${bName}" created.`);
                        if (currentBsModal) currentBsModal.hide();
                    } else {
                        showToast('Failed to create brand.');
                    }
                } catch(e) {
                    showToast('Error saving brand.');
                }
            }

            function filterGroupByBrand(brandVal) {
                selectedBrandView = brandVal;
                renderConnecteamProvisioningTable();
            }

            async function renderConnecteamProvisioningTable() {
                const brands = await getStoredBrands();
                const allGroups = await getStoredGroups();

                let visibleBrands = (selectedBrandView === 'ALL') ? brands : brands.filter(b => b === selectedBrandView);
                document.getElementById('groups-count-label').innerText = `${allGroups.length} groups total`;

                let panelsHtml = '';

                visibleBrands.forEach((brandName, bIdx) => {
                    const brandGroups = allGroups.filter(g => (g.brand || 'Head Office') === brandName);

                    let rowsHtml = '';
                    brandGroups.forEach((g) => {
                        const groupMembers = globalUsersList.filter(u => (u.department === g.name || u.department === g.dept) && u.status !== 'ARCHIVED');
                        const connectedStr = `${groupMembers.length} / ${groupMembers.length}`;

                        // Render dynamic admin bubbles
                        const assignedAdmins = Array.isArray(g.admins) ? g.admins : [];
                        let adminBubblesHtml = '';
                        if (assignedAdmins.length === 0) {
                            adminBubblesHtml = '<small class="text-muted fs-7">None assigned</small>';
                        } else if (assignedAdmins.length <= 2) {
                            assignedAdmins.forEach(empId => {
                                const u = globalUsersList.find(usr => usr.employee_id === empId) || {};
                                const init = `${(u.first_name||u.name||empId).charAt(0)}${(u.last_name || '').charAt(0)}`.toUpperCase();
                                adminBubblesHtml += `<span class="avatar-chip bg-primary text-white" title="${u.name||empId}">${init}</span>`;
                            });
                        } else {
                            const firstTwo = assignedAdmins.slice(0, 2);
                            const remaining = assignedAdmins.length - 2;
                            firstTwo.forEach(empId => {
                                const u = globalUsersList.find(usr => usr.employee_id === empId) || {};
                                const init = `${(u.first_name||u.name||empId).charAt(0)}${(u.last_name || '').charAt(0)}`.toUpperCase();
                                adminBubblesHtml += `<span class="avatar-chip bg-primary text-white" title="${u.name||empId}">${init}</span>`;
                            });
                            adminBubblesHtml += `<span class="avatar-chip bg-dark text-white">+${remaining}</span>`;
                        }

                        rowsHtml += `
                            <tr style="cursor: pointer;" onclick="viewGroupDetails('${g.name}', '${brandName}', '${g.dept || 'General'}')">
                                <td><input type="checkbox" class="form-check-input" onclick="event.stopPropagation()"></td>
                                <td><strong class="text-primary">${g.name}</strong></td>
                                <td><span class="fw-bold text-dark">${connectedStr}</span></td>
                                <td>
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="avatar-chip bg-info text-dark" style="margin:0;">SA</span>
                                        <span class="text-secondary fw-semibold">${g.creator || 'Super Admin'}</span>
                                    </div>
                                </td>
                                <td>
                                    <select class="form-select form-select-sm" style="width: 130px;" onclick="event.stopPropagation()" onchange="showToast('Assignments updated')">
                                        <option>${g.selected || '15 selected'}</option>
                                        <option>All Members</option>
                                        <option>Custom Filter</option>
                                    </select>
                                </td>
                                <td>
                                    <div class="d-flex align-items-center justify-content-between">
                                        <div class="d-flex align-items-center gap-1">
                                            ${adminBubblesHtml}
                                        </div>
                                        <button class="btn btn-sm btn-outline-custom text-danger py-0 px-2" onclick="event.stopPropagation(); deleteSubGroup('${g.name}')"><i class="bi bi-trash"></i></button>
                                    </div>
                                </td>
                            </tr>`;
                    });

                    panelsHtml += `
                        <div class="card-custom p-0 overflow-hidden mb-3 shadow-sm border-0">
                            <div class="p-2 bg-light border-bottom d-flex align-items-center justify-content-between">
                                <div class="d-flex align-items-center gap-2">
                                    <i class="bi bi-chevron-right text-warning fs-6" style="cursor:pointer; width:20px; text-align:center;" id="chevron-brand-${bIdx}" onclick="toggleBrandCollapse('${bIdx}')"></i>
                                    <span class="fw-bold text-dark fs-6" style="cursor:pointer;" onclick="toggleBrandCollapse('${bIdx}')">${brandName}</span>
                                    <button class="btn btn-sm btn-light border-0 ms-2 py-0 px-1 text-muted hover-primary" title="Rename Brand" onclick="openRenameBrandModal('${brandName}')"><i class="bi bi-pencil fs-7"></i></button>
                                    <button class="btn btn-sm btn-light border-0 py-0 px-1 text-muted hover-danger" title="Delete Brand" onclick="deleteBrandLocation('${brandName}')"><i class="bi bi-trash fs-7"></i></button>
                                </div>
                                <button class="btn btn-sm btn-outline-primary py-1 px-2 fw-medium fs-7" onclick="openAddGroupModal('${brandName}')"><i class="bi bi-plus-lg me-1"></i> Add Group</button>
                            </div>

                            <div class="table-responsive" id="brand-body-${bIdx}" style="display: none;">
                                <table class="table table-hover align-middle m-0">
                                    <thead>
                                        <tr>
                                            <th width="30"><input type="checkbox" class="form-check-input"></th>
                                            <th>Group name</th>
                                            <th>Connected</th>
                                            <th>Created by</th>
                                            <th>Assignments</th>
                                            <th>Administrated by</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${rowsHtml || '<tr><td colspan="6" class="text-center text-muted">No groups created under ' + brandName + '.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>`;
                });

                document.getElementById('brands-container').innerHTML = panelsHtml;
                populateDepartmentDropdownOptions();
            }

            function toggleBrandCollapse(bIdx) {
                const el = document.getElementById('brand-body-' + bIdx);
                const chev = document.getElementById('chevron-brand-' + bIdx);
                if (el) {
                    const isHidden = (el.style.display === 'none');
                    el.style.display = isHidden ? 'block' : 'none';
                    if (chev) {
                        chev.className = isHidden ? 'bi bi-chevron-down text-warning fs-6' : 'bi bi-chevron-right text-warning fs-6';
                    }
                }
            }

            function openRenameBrandModal(brandName) {
                editingBrandNameTarget = brandName;
                document.getElementById('modalRenameBrandName').value = brandName;
                currentBsModal = new bootstrap.Modal(document.getElementById('renameBrandModal'));
                currentBsModal.show();
            }

            async function saveRenameBrand() {
                const newBrandName = document.getElementById('modalRenameBrandName').value.trim();
                if (!newBrandName) {
                    showToast('Please enter a valid brand name.');
                    return;
                }

                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/jobs/brands/' + encodeURIComponent(editingBrandNameTarget), {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({ name: newBrandName })
                    });
                    if (res.ok) {
                        if (selectedBrandView === editingBrandNameTarget) selectedBrandView = newBrandName;
                        await renderBrandSelectorOptions();
                        await renderConnecteamProvisioningTable();
                        showToast('Brand name updated.');
                        if (currentBsModal) currentBsModal.hide();
                    } else {
                        showToast('Failed to update brand name.');
                    }
                } catch(e) {
                    showToast('Error updating brand name.');
                }
            }

            function deleteBrandLocation(brandName) {
                document.getElementById('confirmModalTitle').innerText = 'Delete Brand';
                document.getElementById('confirmModalMessage').innerHTML = `Are you sure you want to delete <b>${brandName}</b>?<br><small class="text-danger">All assigned groups will also be deleted.</small>`;
                
                const btn = document.getElementById('confirmModalBtn');
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);
                
                const confirmModal = new bootstrap.Modal(document.getElementById('genericConfirmModal'));
                
                newBtn.onclick = async () => {
                    confirmModal.hide();
                    const token = await getAdminAuthToken();
                    try {
                        const res = await fetch('/api/jobs/brands/' + encodeURIComponent(brandName), {
                            method: 'DELETE',
                            headers: { 'Authorization': 'Bearer ' + token }
                        });
                        if (res.ok) {
                            if (selectedBrandView === brandName) selectedBrandView = 'ALL';
                            await renderBrandSelectorOptions();
                            await renderConnecteamProvisioningTable();
                            showToast(`Brand ${brandName} deleted.`);
                        } else {
                            showToast('Failed to delete brand.');
                        }
                    } catch(e) {
                        showToast('Error deleting brand.');
                    }
                };
                confirmModal.show();
            }

            function deleteSubGroup(groupName) {
                document.getElementById('confirmModalTitle').innerText = 'Delete Group';
                document.getElementById('confirmModalMessage').innerHTML = `Are you sure you want to remove group <b>${groupName}</b>?`;
                
                const btn = document.getElementById('confirmModalBtn');
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);
                
                const confirmModal = new bootstrap.Modal(document.getElementById('genericConfirmModal'));
                
                newBtn.onclick = async () => {
                    confirmModal.hide();
                    const token = await getAdminAuthToken();
                    try {
                        const res = await fetch('/api/jobs/groups/' + encodeURIComponent(groupName), {
                            method: 'DELETE',
                            headers: { 'Authorization': 'Bearer ' + token }
                        });
                        if (res.ok) {
                            await renderConnecteamProvisioningTable();
                            showToast(`Group "${groupName}" removed.`);
                        } else {
                            showToast('Failed to delete group.');
                        }
                    } catch(e) {
                        showToast('Error deleting group.');
                    }
                };
                confirmModal.show();
            }

            async function viewGroupDetails(groupName, brand, dept) {
                activeGroupName = groupName;
                document.getElementById('detail-group-title').innerText = groupName;
                document.getElementById('filter-brand-pill').innerText = `Location is ${brand || 'Head Office'}`;
                document.getElementById('filter-dept-pill').innerText = `Department is ${dept || 'General'}`;

                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/auth/users', { 
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                    if (res.ok) globalUsersList = await res.json();
                } catch(e) {}

                const groupMembers = globalUsersList.filter(u => u.department === groupName || u.department === dept);

                let clockedInCount = 0;
                try {
                    const activeRes = await fetch('/api/punch/logs');
                    if (activeRes.ok) {
                        const logs = await activeRes.json();
                        const activeEmpIds = logs.filter(p => p.punch_type === 'CLOCK_IN').map(p => p.employee_id);
                        clockedInCount = groupMembers.filter(m => activeEmpIds.includes(m.employee_id || m.kiosk_code)).length;
                    }
                } catch(e) {}

                document.getElementById('detail-emp-count').innerText = groupMembers.length;
                document.getElementById('detail-logged-count').innerText = `${clockedInCount} / ${groupMembers.length}`;
                renderDetailMembers(groupMembers);
                renderDepartmentJobsChips();

                const drawerEl = document.getElementById('groupDetailDrawer');
                currentOffcanvasDrawer = new bootstrap.Offcanvas(drawerEl);
                currentOffcanvasDrawer.show();
            }

            function renderDepartmentJobsChips() {
                const jobsList = getDeptJobsStore(activeGroupName);
                let chipsHtml = '';
                jobsList.forEach((j, idx) => {
                    chipsHtml += `
                        <span class="badge bg-white text-dark border p-2 fw-semibold d-inline-flex align-items-center gap-2">
                            ${j}
                            <i class="bi bi-x text-danger" style="cursor:pointer;" onclick="removeDepartmentJobTitle(${idx})"></i>
                        </span>`;
                });
                document.getElementById('dept-jobs-chips-container').innerHTML = chipsHtml || '<small class="text-muted">No specific jobs added yet.</small>';
            }

            function openAddDepartmentJobModal() {
                document.getElementById('modalNewDeptJobTitle').value = '';
                currentBsModal = new bootstrap.Modal(document.getElementById('addDepartmentJobModal'));
                currentBsModal.show();
            }

            function saveNewDeptJobTitle() {
                const jobTitle = document.getElementById('modalNewDeptJobTitle').value.trim();
                if (!jobTitle) {
                    showToast('Please enter a job title.');
                    return;
                }

                let jobsList = getDeptJobsStore(activeGroupName);
                jobsList.push(jobTitle);
                setDeptJobsStore(activeGroupName, jobsList);

                renderDepartmentJobsChips();
                showToast(`Job "${jobTitle}" added to ${activeGroupName}.`);
                if (currentBsModal) currentBsModal.hide();
            }

            function removeDepartmentJobTitle(idx) {
                let jobsList = getDeptJobsStore(activeGroupName);
                jobsList.splice(idx, 1);
                setDeptJobsStore(activeGroupName, jobsList);
                renderDepartmentJobsChips();
                showToast('Job title removed.');
            }

            function renderDetailMembers(members) {
                let html = '';
                if (!members || members.length === 0) {
                    html = '<tr><td colspan="5" class="text-center text-muted py-4">No members enrolled in this group.</td></tr>';
                } else {
                    members.forEach((u, idx) => {
                        html += `
                            <tr>
                                <td>${u.first_name || u.name}</td>
                                <td>${u.last_name || ''}</td>
                                <td>${u.created_at || '09/16/2026'}</td>
                                <td>${u.department || 'Admin'}</td>
                                <td><code>${u.employee_id || u.kiosk_code}</code></td>
                            </tr>`;
                    });
                }
                document.getElementById('detail-members-tbody').innerHTML = html;
            }

            function filterDetailMembers(query) {
                const q = query.toLowerCase();
                const members = globalUsersList.filter(u => u.department === activeGroupName || u.department === activeGroupName.replace('HO - ', ''));
                const filtered = members.filter(u => 
                    ((u.first_name || u.name) && (u.first_name || u.name).toLowerCase().includes(q)) || 
                    (u.last_name && u.last_name.toLowerCase().includes(q)) ||
                    ((u.employee_id || u.kiosk_code) && (u.employee_id || u.kiosk_code).toLowerCase().includes(q))
                );
                renderDetailMembers(filtered);
            }

            async function openAddGroupModal(defaultBrand = 'Head Office') {
                await renderBrandSelectorOptions();
                document.getElementById('modalGroupName').value = '';
                const brandSelect = document.getElementById('modalBrandSelect');
                if (brandSelect) {
                    brandSelect.value = defaultBrand;
                }
                currentBsModal = new bootstrap.Modal(document.getElementById('groupModal'));
                currentBsModal.show();
            }

            async function saveSmartGroup() {
                const name = document.getElementById('modalGroupName').value.trim();
                const brand = document.getElementById('modalBrandSelect').value;
                if (!name) {
                    showToast('Please enter a group name.');
                    return;
                }

                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/jobs/groups', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({
                            name: name,
                            brand_name: brand
                        })
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        showToast(data.detail || 'Failed to create group.');
                        return;
                    }

                    if (typeof loadSmartGroups === 'function') {
                        await loadSmartGroups();
                    } else if (typeof renderConnecteamProvisioningTable === 'function') {
                        renderConnecteamProvisioningTable();
                    }

                    showToast('Smart Group created successfully.');
                    if (currentBsModal) currentBsModal.hide();
                } catch (err) {
                    console.error('Error saving smart group:', err);
                    showToast('Error saving group.');
                }
            }

            function openRenameGroupModal() {
                document.getElementById('modalRenameGroupName').value = activeGroupName;
                currentBsModal = new bootstrap.Modal(document.getElementById('renameGroupModal'));
                currentBsModal.show();
            }

            function saveRenameGroup() {
                const newName = document.getElementById('modalRenameGroupName').value.trim();
                if (!newName) {
                    showToast('Please enter a valid group name.');
                    return;
                }

                let groups = getStoredGroups();
                const idx = groups.findIndex(g => g.name === activeGroupName);
                if (idx !== -1) {
                    groups[idx].name = newName;
                    setStoredGroups(groups);
                }

                activeGroupName = newName;
                document.getElementById('detail-group-title').innerText = newName;
                renderConnecteamProvisioningTable();
                showToast('Group renamed successfully.');
                if (currentBsModal) currentBsModal.hide();
            }

            async function loadConnecteamDirectory() {
                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/auth/users', { 
                        headers: { 'Authorization': 'Bearer ' + token } 
                    });
                    if (res.ok) {
                        globalUsersList = await res.json();
                    }
                } catch(e) {}

                renderDirectoryRows(globalUsersList);
            }

            function renderDirectoryRows(users) {
                let filteredUsers = users || [];
                if (activeDirectoryCategoryFilter === 'ADMIN') {
                    filteredUsers = filteredUsers.filter(u => u.role === 'Admin');
                } else if (activeDirectoryCategoryFilter === 'ARCHIVED') {
                    filteredUsers = filteredUsers.filter(u => u.status === 'ARCHIVED');
                } else {
                    filteredUsers = filteredUsers.filter(u => u.status !== 'ARCHIVED');
                }

                let html = '';
                if (!filteredUsers || filteredUsers.length === 0) {
                    html = '<tr><td colspan="10" class="text-center text-muted py-4">No users found in database for this view.</td></tr>';
                } else {
                    filteredUsers.forEach((u, idx) => {
                        const initials = `${(u.first_name || u.name || 'U').charAt(0)}${(u.last_name || '').charAt(0)}`.toUpperCase();
                        const firstName = u.first_name || u.name;
                        const lastName = u.last_name || '';
                        const empId = u.employee_id || u.kiosk_code || 'EMP001';

                        let actionBtn = '';
                        if (u.status === 'ARCHIVED') {
                            actionBtn = `<button class="btn btn-sm btn-outline-custom text-success py-0 px-2" onclick="event.stopPropagation(); updateUserStatus('${empId}', 'APPROVED')"><i class="bi bi-arrow-counterclockwise me-1"></i> Un-archive</button>`;
                        } else if (u.status === 'DENIED') {
                            actionBtn = `<button class="btn btn-sm btn-outline-custom text-primary py-0 px-2" onclick="event.stopPropagation(); updateUserStatus('${empId}', 'APPROVED')"><i class="bi bi-check-lg me-1"></i> Approve</button>`;
                        } else {
                            actionBtn = `<button class="btn btn-sm btn-outline-custom text-danger py-0 px-2" onclick="event.stopPropagation(); updateUserStatus('${empId}', 'ARCHIVED')"><i class="bi bi-archive me-1"></i> Archive</button>`;
                        }

                        html += `
                            <tr style="cursor: pointer;" onclick="openUserProfileDashboard('${firstName}', '${lastName}', '${u.role || 'Employee'}', '${u.department || 'General'}', '${u.email || ''}', '${u.mobile_phone || u.mobile || ''}', '${empId}', '${u.status || 'APPROVED'}')">
                                <td><input type="checkbox" class="form-check-input" onclick="event.stopPropagation()"></td>
                                <td>
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="avatar-chip bg-primary text-white">${initials}</span>
                                        <strong class="text-dark">${firstName}</strong>
                                    </div>
                                </td>
                                <td>${lastName}</td>
                                <td>${u.last_login || '09/16/2026'}</td>
                                <td>${u.employment_start || '05/19/2025'}</td>
                                <td>${u.department || 'General'}</td>
                                <td><code>${empId}</code></td>
                                <td><small class="text-muted">${u.date_added || '05/20/2025'}</small></td>
                                <td><small class="text-muted">${u.added_by || 'Admin'}</small></td>
                                <td class="text-end">${actionBtn}</td>
                            </tr>`;
                    });
                }
                document.getElementById('directory-users-tbody').innerHTML = html;
            }

            function filterDirectoryRows(query) {
                const q = query.toLowerCase();
                const list = globalUsersList;
                const filtered = list.filter(u => 
                    ((u.first_name || u.name) && (u.first_name || u.name).toLowerCase().includes(q)) || 
                    (u.last_name && u.last_name.toLowerCase().includes(q)) ||
                    ((u.employee_id || u.kiosk_code) && (u.employee_id || u.kiosk_code).toLowerCase().includes(q))
                );
                renderDirectoryRows(filtered);
            }

            function filterUserCategory(cat) {
                activeDirectoryCategoryFilter = cat;
                document.getElementById('user-subtab-active').classList.remove('active');
                document.getElementById('user-subtab-admins').classList.remove('active');
                document.getElementById('user-subtab-archived').classList.remove('active');

                if (cat === 'APPROVED') {
                    document.getElementById('user-subtab-active').classList.add('active');
                } else if (cat === 'ADMIN') {
                    document.getElementById('user-subtab-admins').classList.add('active');
                } else {
                    document.getElementById('user-subtab-archived').classList.add('active');
                }

                loadConnecteamDirectory();
            }

            function switchProfileTab(pTab) {
                document.getElementById('profile-subtab-employment').style.display = 'none';
                document.getElementById('profile-subtab-activity').style.display = 'none';
                document.getElementById('profile-subtab-timeoff').style.display = 'none';
                document.getElementById('profile-subtab-notes').style.display = 'none';

                const links = document.querySelectorAll('#userProfileSubTabs .nav-link');
                links.forEach(l => l.classList.remove('active'));

                document.getElementById('profile-subtab-' + pTab).style.display = 'block';
                event.target.classList.add('active');

                if (pTab === 'activity' && currentActiveProfileUser) {
                    loadUserActivityPunches(currentActiveProfileUser.empId);
                }
            }

            async function loadUserActivityPunches(empId) {
                try {
                    const res = await fetch('/api/punch/logs');
                    if (res.ok) {
                        const logs = await res.json();
                        const userLogs = logs.filter(p => p.employee_id === empId);
                        let html = '';
                        if (userLogs.length === 0) {
                            html = '<tr><td colspan="3" class="text-center text-muted py-3">No punch activity logs found for this user.</td></tr>';
                        } else {
                            userLogs.forEach(p => {
                                html += `
                                    <tr>
                                        <td><span class="badge ${p.punch_type === 'CLOCK_IN' ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'}">${p.punch_type}</span></td>
                                        <td>${p.timestamp}</td>
                                        <td><small class="text-secondary">${p.address || 'Standard Duty Location'}</small></td>
                                    </tr>`;
                            });
                        }
                        document.getElementById('profile-activity-tbody').innerHTML = html;
                    }
                } catch(e) {}
            }

            function openPendingApprovalsModal() {
                const pendingUsers = globalUsersList.filter(u => u.status === 'PENDING' || u.status === 'DENIED');
                let html = '';
                if (pendingUsers.length === 0) {
                    html = '<tr><td colspan="4" class="text-center text-muted py-4">No pending or denied access requests in database.</td></tr>';
                } else {
                    pendingUsers.forEach(u => {
                        html += `
                            <tr>
                                <td><strong>${u.name || (u.first_name + ' ' + u.last_name)}</strong> (${u.employee_id})</td>
                                <td>${u.email || '-'}</td>
                                <td><span class="badge ${u.status === 'DENIED' ? 'bg-danger-subtle text-danger' : 'bg-warning-subtle text-warning'} border">${u.status}</span></td>
                                <td class="text-end">
                                    <button class="btn btn-sm btn-primary-custom me-1" onclick="updateUserStatus('${u.employee_id}', 'APPROVED')"><i class="bi bi-check-lg"></i> Accept / Approve</button>
                                    <button class="btn btn-sm btn-outline-custom text-danger" onclick="updateUserStatus('${u.employee_id}', 'DENIED')"><i class="bi bi-x-lg"></i> Deny</button>
                                </td>
                            </tr>`;
                    });
                }
                document.getElementById('pending-approvals-tbody').innerHTML = html;
                currentBsModal = new bootstrap.Modal(document.getElementById('pendingApprovalsModal'));
                currentBsModal.show();
            }

            async function updateUserStatus(empId, status) {
                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch(`/api/auth/users/${empId}/status`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                        body: JSON.stringify({ status })
                    });
                    if (res.ok) {
                        showToast(`User ${empId} status updated to ${status}`);
                        if (currentBsModal) currentBsModal.hide();
                        loadConnecteamDirectory();
                    }
                } catch(e) {}
            }

            function openDirectAddUserModal() {
                populateDepartmentDropdownOptions();
                document.getElementById('modalNewUserFirstName').value = '';
                document.getElementById('modalNewUserLastName').value = '';
                document.getElementById('modalNewUserEmpId').value = '';
                document.getElementById('modalNewUserEmail').value = '';
                currentBsModal = new bootstrap.Modal(document.getElementById('directAddUserModal'));
                currentBsModal.show();
            }

            async function saveDirectNewUser() {
                const first_name = document.getElementById('modalNewUserFirstName').value.trim();
                const last_name = document.getElementById('modalNewUserLastName').value.trim();
                const employee_id = document.getElementById('modalNewUserEmpId').value.trim();
                const email = document.getElementById('modalNewUserEmail').value.trim();
                const department = document.getElementById('modalNewUserDept').value;
                const role = document.getElementById('modalNewUserRole').value;

                if (!first_name || !last_name || !employee_id || !email) {
                    showToast('First Name, Last Name, Employee ID, and Email are required.');
                    return;
                }

                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch('/api/auth/users', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                        body: JSON.stringify({
                            employee_id,
                            first_name,
                            last_name,
                            email,
                            department,
                            role,
                            status: 'APPROVED',
                            password: 'bigtime@123'
                        })
                    });
                    if (res.ok) {
                        showToast(`Employee ${first_name} ${last_name} created in database.`);
                        if (currentBsModal) currentBsModal.hide();
                        loadConnecteamDirectory();
                    } else {
                        showToast('Failed to create employee account.', 'danger');
                    }
                } catch(e) { showToast('Server connection error.', 'danger'); }
            }

            function openUserProfileDashboard(first, last, role, dept, email, mobile, empId, status) {
                currentActiveProfileUser = { first, last, role, dept, email, mobile, empId, status };

                document.getElementById('users-directory-list-view').style.display = 'none';
                document.getElementById('user-profile-dashboard-view').style.display = 'block';

                const initials = `${first.charAt(0)}${last.charAt(0)}`.toUpperCase();
                document.getElementById('profile-dashboard-avatar').innerText = initials;
                document.getElementById('profile-dashboard-name').childNodes[0].nodeValue = `${first} ${last} `;
                document.getElementById('profile-dashboard-role').innerText = role;

                document.getElementById('edit-user-original-empid').value = empId;
                document.getElementById('edit-user-original-dept').value = dept || 'Admin';
                document.getElementById('edit-user-firstname').value = first;
                document.getElementById('edit-user-lastname').value = last || '';
                document.getElementById('edit-user-mobile').value = mobile || '';
                document.getElementById('edit-user-email').value = email || '';
                document.getElementById('edit-user-empid').value = empId;
                
                populateDepartmentDropdownOptions(dept);
                document.getElementById('edit-user-role').value = role || 'Employee';

                if (status === 'ARCHIVED') {
                    document.getElementById('unarchive-profile-btn').style.display = 'inline-block';
                    document.getElementById('archive-profile-btn').style.display = 'none';
                } else {
                    document.getElementById('unarchive-profile-btn').style.display = 'none';
                    document.getElementById('archive-profile-btn').style.display = 'inline-block';
                }

                switchProfileTab('employment');
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function changeActiveUserRole(newRole) {
                document.getElementById('edit-user-role').value = newRole;
                document.getElementById('profile-dashboard-role').innerText = newRole;
                showToast(`User role updated to ${newRole}. Click "Save Profile Changes" to apply.`);
            }

            async function saveAdminUserProfileEdit() {
                const origEmpId = document.getElementById('edit-user-original-empid').value;
                const newEmpId = document.getElementById('edit-user-empid').value.trim();
                const firstName = document.getElementById('edit-user-firstname').value.trim();
                const lastName = document.getElementById('edit-user-lastname').value.trim();
                const email = document.getElementById('edit-user-email').value.trim();
                const mobilePhone = document.getElementById('edit-user-mobile').value.trim();
                const newDept = document.getElementById('edit-user-department').value;
                const role = document.getElementById('edit-user-role').value;

                if (!newEmpId || !firstName || !lastName) {
                    showToast('First Name, Last Name, and Employee ID are required.');
                    return;
                }

                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch(`/api/auth/users/${origEmpId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                        body: JSON.stringify({
                            new_employee_id: newEmpId,
                            first_name: firstName,
                            last_name: lastName,
                            email,
                            mobile_phone: mobilePhone,
                            department: newDept,
                            role,
                            status: 'APPROVED'
                        })
                    });

                    if (res.ok) {
                        showToast(`Employee profile updated to Department "${newDept}".`);
                        closeUserProfileDashboard();
                        loadConnecteamDirectory();
                    } else {
                        showToast('Failed to update employee profile.');
                    }
                } catch(e) { showToast('Server connection error.'); }
            }

            async function archiveActiveUserProfile() {
                const origEmpId = document.getElementById('edit-user-original-empid').value;
                if (!confirm(`Archive employee account ${origEmpId}?`)) return;
                await updateUserStatus(origEmpId, 'ARCHIVED');
                closeUserProfileDashboard();
            }

            async function unarchiveActiveUserProfile() {
                const origEmpId = document.getElementById('edit-user-original-empid').value;
                if (!confirm(`Un-archive employee account ${origEmpId}?`)) return;
                await updateUserStatus(origEmpId, 'APPROVED');
                closeUserProfileDashboard();
            }

            function closeUserProfileDashboard() {
                document.getElementById('user-profile-dashboard-view').style.display = 'none';
                document.getElementById('users-directory-list-view').style.display = 'block';
            }

            // CUSTOM FORMS DYNAMIC STATE & HANDLERS
            let currentFormCategory = localStorage.getItem('lastSelectedFormCategory') || 'IT Forms';
            let currentFormTabStatus = 'ACTIVE';
            let fetchedCustomFormsList = [];
            let availableCategoriesList = [];

            async function loadCategoryTabsBar() {
                await renderSidebarFormsCategories();
                if (availableCategoriesList.length > 0) {
                    const exists = availableCategoriesList.some(c => c.name === currentFormCategory);
                    if (!exists) {
                        currentFormCategory = availableCategoriesList[0].name;
                    }
                }
            }

            async function renderSidebarFormsCategories() {
                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/forms/categories', {
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                    if (res.ok) {
                        availableCategoriesList = await res.json();
                    }
                } catch(e) {}

                if (!availableCategoriesList) {
                    availableCategoriesList = [];
                }

                const sidebarContainer = document.getElementById('sidebar-forms-categories-list');
                if (sidebarContainer) {
                    let catHtml = '';
                    const colorVariants = ['#3b82f6', '#ec4899', '#a855f7', '#eab308', '#06b6d4', '#10b981'];
                    
                    availableCategoriesList.forEach((c, idx) => {
                        const isActive = (c.name === currentFormCategory);
                        const iconBg = colorVariants[idx % colorVariants.length];
                        
                        catHtml += `
                            <div class="d-flex align-items-center justify-content-between nav-link-sidebar-item ${isActive ? 'active' : ''}" style="padding: 6px 10px; border-radius: 8px; margin-bottom: 2px; cursor: pointer; ${isActive ? 'background: rgba(255, 255, 255, 0.1); color: #fff;' : 'color: #94a3b8;'}" onclick="selectFormCategoryTab('${c.name}')">
                                <div class="d-flex align-items-center gap-2 overflow-hidden me-1">
                                    <span class="text-muted" style="cursor: grab; font-size: 11px;"><i class="bi bi-grip-vertical"></i></span>
                                    <div class="d-flex align-items-center justify-content-center rounded-3 text-white flex-shrink-0" style="width: 26px; height: 26px; background-color: ${iconBg}; font-size: 13px;">
                                        <i class="bi bi-file-earmark-text-fill"></i>
                                    </div>
                                    <span class="text-truncate fs-7 fw-medium">${c.name}</span>
                                </div>
                                <div class="dropdown" onclick="event.stopPropagation()">
                                    <button class="btn btn-link btn-sm text-muted p-0 border-0" type="button" data-bs-toggle="dropdown" style="line-height: 1;">
                                        <i class="bi bi-three-dots-vertical fs-7"></i>
                                    </button>
                                    <ul class="dropdown-menu shadow-sm border-0 fs-7">
                                        <li><a class="dropdown-item" onclick="openEditCategoryModal(${c.id}, '${c.name}')"><i class="bi bi-pencil me-2 text-primary"></i> Edit (Rename)</a></li>
                                        <li><a class="dropdown-item" onclick="archiveCategoryForms('${c.name}')"><i class="bi bi-archive me-2 text-warning"></i> Archive Category</a></li>
                                        <li><hr class="dropdown-divider"></li>
                                        <li><a class="dropdown-item text-danger" onclick="openConfirmDeleteCategoryModal(${c.id}, '${c.name}')"><i class="bi bi-trash me-2"></i> Delete Category</a></li>
                                    </ul>
                                </div>
                            </div>`;
                    });
                    sidebarContainer.innerHTML = catHtml;
                }

                const selectEl = document.getElementById('builderFormCategory');
                if (selectEl) {
                    selectEl.innerHTML = availableCategoriesList.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
                }

                if (availableCategoriesList.length === 0) {
                    renderFormsBlankLandingPage();
                }
            }

            function renderFormsBlankLandingPage() {
                history.pushState(null, '', '/admin/forms');
                const pageTitle = document.getElementById('page-title');
                if (pageTitle) pageTitle.innerText = 'Forms';
                const container = document.getElementById('forms-list-container');
                if (container) {
                    container.innerHTML = `
                        <div class="d-flex flex-column align-items-center justify-content-center p-5 text-center" style="min-height: 400px;">
                            <i class="bi bi-folder2-open text-muted mb-3" style="font-size: 3rem;"></i>
                            <h5 class="fw-bold mb-2">No Form Categories</h5>
                            <p class="text-muted fs-7 mb-4">Get started by creating your first form category.</p>
                            <button class="btn btn-primary rounded-pill px-4" onclick="openCreateCategoryModal()">
                                <i class="bi bi-plus-lg me-1"></i> Create new category
                            </button>
                        </div>`;
                }
            }

            function selectFormCategoryTab(catName) {
                currentFormCategory = catName;
                localStorage.setItem('lastSelectedFormCategory', catName);
                const pageTitle = document.getElementById('page-title');
                if (pageTitle) pageTitle.innerText = catName;
                const catHeaderTitle = document.getElementById('forms-category-header-title');
                if (catHeaderTitle) catHeaderTitle.innerText = catName;
                
                const container = document.getElementById('forms-list-container');
                if (container && !document.getElementById('customFormsTableBody')) {
                    container.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div class="d-flex align-items-center gap-3">
                                <ul class="nav nav-tabs nav-tabs-connecteam border-0 m-0" id="formsCategoryTabsBar"></ul>
                                <button class="btn btn-outline-custom btn-sm fw-bold" onclick="openCreateCategoryModal()"><i class="bi bi-plus-lg me-1"></i> Create new category</button>
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <small class="text-muted">Permissions</small>
                                <div class="avatar-circle bg-dark text-white" style="width:28px; height:28px; font-size:11px;">SA</div>
                            </div>
                        </div>
                        <div class="card border-0 shadow-sm rounded-3">
                            <div class="card-body p-0">
                                <table class="table align-middle mb-0">
                                    <thead class="bg-light text-muted fs-7">
                                        <tr>
                                            <th class="ps-3" style="width: 30px;"><input type="checkbox" class="form-check-input"></th>
                                            <th>NAME</th>
                                            <th>STATUS</th>
                                            <th>ASSIGNED TO</th>
                                            <th>CREATOR</th>
                                            <th>ADMINISTRATED BY</th>
                                            <th>DATE CREATED</th>
                                            <th class="text-end pe-3">ACTIONS</th>
                                        </tr>
                                    </thead>
                                    <tbody id="customFormsTableBody"></tbody>
                                </table>
                            </div>
                        </div>`;
                }
                switchTab('forms-view');
                renderSidebarFormsCategories();
                loadCustomForms(catName);
            }

            
            function openWorkspaceToolsFlyout(e) {
                if (e) e.preventDefault();
                currentBsModal = new bootstrap.Modal(document.getElementById('workspaceToolsFlyoutModal'));
                currentBsModal.show();
            }

            function openCreateCategoryModalFromFlyout() {
                if (currentBsModal) currentBsModal.hide();
                openCreateCategoryModal();
            }

            function openCreateCategoryModal() {
                document.getElementById('modalNewCategoryName').value = '';
                currentBsModal = new bootstrap.Modal(document.getElementById('createCategoryModal'));
                currentBsModal.show();
            }

            async function submitCreateCategory() {
                const name = document.getElementById('modalNewCategoryName').value.trim();
                if (!name) {
                    showToast('Please enter a category name.');
                    return;
                }

                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/forms/categories', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                        body: JSON.stringify({ name })
                    });
                    if (res.ok) {
                        showToast(`Category '${name}' created.`);
                        if (currentBsModal) currentBsModal.hide();
                        await renderSidebarFormsCategories();
                        selectFormCategoryTab(name);
                    } else {
                        const errData = await res.json().catch(() => ({}));
                        showToast(errData.detail || 'Failed to create category.');
                    }
                } catch(e) {
                    showToast('Network error while creating category.');
                }
            }

            async function archiveCategoryForms(catName) {
                if (!confirm(`Archive all active custom forms under '${catName}'?`)) return;
                showToast(`Category '${catName}' forms archived.`);
                loadCustomForms(catName);
            }

            async function loadCustomForms(category = 'IT Forms') {
                currentFormCategory = category;
                document.getElementById('forms-category-header-title').innerText = category;
                const token = await getAdminAuthToken();

                try {
                    const resActive = await fetch(`/api/forms?category=${encodeURIComponent(category)}&is_archived=false`, {
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                    const resArchived = await fetch(`/api/forms?category=${encodeURIComponent(category)}&is_archived=true`, {
                        headers: { 'Authorization': 'Bearer ' + token }
                    });

                    const activeList = resActive.ok ? await resActive.json() : [];
                    const archivedList = resArchived.ok ? await resArchived.json() : [];

                    document.getElementById('count-active-forms').innerText = activeList.length;
                    document.getElementById('count-archived-forms').innerText = archivedList.length;

                    mockCustomFormsData = (currentFormTabStatus === 'ARCHIVED') ? archivedList : activeList;
                    renderCustomFormsTable();
                } catch(err) {
                    console.error("Error loading forms API:", err);
                }
            }

            function switchFormTabStatus(status) {
                currentFormTabStatus = status;
                document.getElementById('form-tab-active').classList.toggle('active', status === 'ACTIVE');
                document.getElementById('form-tab-archived').classList.toggle('active', status === 'ARCHIVED');
                renderCustomFormsTable();
            }

            function renderCustomFormsTable(searchFilter = '') {
                const tbody = document.getElementById('custom-forms-tbody');
                if (!tbody) return;

                const isArchivedTarget = (currentFormTabStatus === 'ARCHIVED');
                let items = mockCustomFormsData.filter(f => f.category === currentFormCategory && f.isArchived === isArchivedTarget);

                if (searchFilter.trim() !== '') {
                    const term = searchFilter.toLowerCase();
                    items = items.filter(f => f.name.toLowerCase().includes(term) || f.createdBy.toLowerCase().includes(term));
                }

                if (items.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-muted fs-7">No forms found for ${currentFormCategory} (${currentFormTabStatus.toLowerCase()}).</td></tr>`;
                    return;
                }

                tbody.innerHTML = items.map(f => {
                    const newBadge = f.isNew ? `<span class="badge bg-primary ms-2 rounded-pill" style="font-size:10px;">1 new</span>` : '';
                    const assignedBadge = f.assignedGroups.join(', ');
                    return `
                        <tr>
                            <td><input type="checkbox" class="form-check-input"></td>
                            <td>
                                <a class="fw-bold text-dark text-decoration-none cursor-pointer" onclick="openFormDetailSubmissions(${f.id})">
                                    ${f.name}
                                </a>
                            </td>
                            <td><span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2 py-1 fs-7">${f.status}</span></td>
                            <td><span class="fw-bold text-dark">${f.entries}</span> ${newBadge}</td>
                            <td class="text-muted">${f.views}</td>
                            <td><span class="badge bg-light text-dark border fw-normal fs-7">${assignedBadge}</span></td>
                            <td>
                                <div class="d-flex align-items-center gap-1">
                                    <div class="avatar-circle bg-danger text-white" style="width:24px; height:24px; font-size:10px;">${f.createdAvatar}</div>
                                    <span class="fs-7 text-dark">${f.createdBy}</span>
                                </div>
                            </td>
                            <td>
                                <div class="d-flex align-items-center gap-1">
                                    <div class="avatar-circle bg-info text-white" style="width:24px; height:24px; font-size:10px;">DI</div>
                                    <span class="badge bg-light text-secondary border rounded-pill fs-7">${f.administratedBy}</span>
                                </div>
                            </td>
                            <td class="text-muted fs-7">${f.dateCreated}</td>
                        </tr>
                    `;
                }).join('');
            }

            function filterCustomFormsList(query) {
                renderCustomFormsTable(query);
            }

            function openFormDetailSubmissions(formId) {
                const formObj = mockCustomFormsData.find(f => f.id === formId) || mockCustomFormsData[0];
                document.getElementById('selected-form-title').innerText = formObj.name;
                document.getElementById('form-submission-count-label').innerText = formObj.entries;
                document.getElementById('forms-list-container').style.display = 'none';
                document.getElementById('form-detail-submissions-container').style.display = 'block';

                const tbody = document.getElementById('form-submissions-tbody');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td><input type="checkbox" class="form-check-input"></td>
                            <td><span class="fw-bold text-dark">Alejandro Luanzon Jr.</span></td>
                            <td>09/18/2026, 08:30 AM</td>
                            <td><span class="badge bg-light text-dark border fw-normal fs-7">HO - I.T.</span></td>
                            <td><span class="badge bg-success-subtle text-success">Submitted</span></td>
                            <td class="text-end"><button class="btn btn-outline-custom btn-sm" onclick="showToast('Viewing submission response details...')"><i class="bi bi-eye"></i> View</button></td>
                        </tr>
                        <tr>
                            <td><input type="checkbox" class="form-check-input"></td>
                            <td><span class="fw-bold text-dark">Drenzo Pornel</span></td>
                            <td>09/17/2026, 04:15 PM</td>
                            <td><span class="badge bg-light text-dark border fw-normal fs-7">Management Group</span></td>
                            <td><span class="badge bg-success-subtle text-success">Submitted</span></td>
                            <td class="text-end"><button class="btn btn-outline-custom btn-sm" onclick="showToast('Viewing submission response details...')"><i class="bi bi-eye"></i> View</button></td>
                        </tr>
                    `;
                }
            }

            function closeFormDetailSubmissions() {
                document.getElementById('form-detail-submissions-container').style.display = 'none';
                document.getElementById('forms-list-container').style.display = 'block';
            }

            function openFormSourceModal() {
                currentBsModal = new bootstrap.Modal(document.getElementById('formSourceModal'));
                currentBsModal.show();
            }

            function selectFormSource(sourceType) {
                if (currentBsModal) currentBsModal.hide();
                openCreateCustomFormModal();
                if (currentFormCategory) {
                    const catSelect = document.getElementById('newFormCategorySelect');
                    if (catSelect) catSelect.value = currentFormCategory;
                }
                if (sourceType === 'template') {
                    setTimeout(() => {
                        addBuilderField();
                        const card = document.querySelectorAll('.builder-field-card')[0];
                        if (card) {
                            card.querySelector('.field-label-input').value = 'Employee Request Details';
                            card.querySelector('.field-type-select').value = 'textarea';
                        }
                    }, 300);
                }
            }

            function openEditAssignmentsDrawer(formId) {
                document.getElementById('assignmentFormId').value = formId;
                const drawer = new bootstrap.Offcanvas(document.getElementById('editAssignmentsModal'));
                drawer.show();
            }

            async function submitAssignmentsDrawer() {
                const formId = document.getElementById('assignmentFormId').value;
                const checkedGroups = [];
                document.querySelectorAll('.assignment-group-check:checked').forEach(c => checkedGroups.push(c.value));
                const token = await getAdminAuthToken();

                try {
                    const res = await fetch(`/api/forms/${formId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                        body: JSON.stringify({ assigned_groups: checkedGroups })
                    });
                    if (res.ok) {
                        showToast('Form assignments updated.');
                        const el = document.getElementById('editAssignmentsModal');
                        const inst = bootstrap.Offcanvas.getInstance(el);
                        if (inst) inst.hide();
                        loadCustomForms(currentFormCategory);
                    } else {
                        showToast('Failed to update form assignments.');
                    }
                } catch(e) {
                    showToast('Error updating form assignments.');
                }
            }

            function openEditCategoryModal(catId, catName) {
                document.getElementById('editCategoryId').value = catId;
                document.getElementById('editCategoryNewName').value = catName;
                currentBsModal = new bootstrap.Modal(document.getElementById('editCategoryModal'));
                currentBsModal.show();
            }

            async function submitEditCategory() {
                const catId = document.getElementById('editCategoryId').value;
                const newName = document.getElementById('editCategoryNewName').value.trim();
                if (!newName || !catId) return;

                const token = await getAdminAuthToken();
                try {
                    const res = await fetch(`/api/forms/categories/${catId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                        body: JSON.stringify({ name: newName })
                    });
                    if (res.ok) {
                        showToast(`Category renamed to '${newName}'.`);
                        if (currentBsModal) currentBsModal.hide();
                        currentFormCategory = newName;
                        localStorage.setItem('lastSelectedFormCategory', newName);
                        await renderSidebarFormsCategories();
                        const titleEl = document.getElementById('formsCategoryPageTitle') || document.getElementById('formsPageHeaderTitle');
                        if (titleEl) titleEl.innerText = newName;
                        loadCustomForms(newName);
                    } else {
                        showToast('Failed to rename category.');
                    }
                } catch(e) { showToast('Error renaming category.'); }
            }

            let pendingDeleteCatId = null;

            function openConfirmDeleteCategoryModal(catId, catName) {
                pendingDeleteCatId = catId;
                document.getElementById('deleteCategoryName').value = catName;
                document.getElementById('deleteCategoryLabel').innerText = catName;
                currentBsModal = new bootstrap.Modal(document.getElementById('confirmDeleteCategoryModal'));
                currentBsModal.show();
            }

            async function submitDeleteCategory() {
                if (!pendingDeleteCatId) return;
                const catName = document.getElementById('deleteCategoryName').value;
                const token = await getAdminAuthToken();

                try {
                    const res = await fetch(`/api/forms/categories/${pendingDeleteCatId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                    if (res.ok) {
                        showToast(`Category '${catName}' deleted.`);
                        if (currentBsModal) currentBsModal.hide();
                        await renderSidebarFormsCategories();
                        if (availableCategoriesList.length > 0) {
                            selectFormCategoryTab(availableCategoriesList[0].name);
                        } else {
                            currentFormCategory = null;
                            localStorage.removeItem('lastSelectedFormCategory');
                            history.pushState({}, '', '/admin/forms/');
                            const pageTitle = document.getElementById('page-title');
                            if (pageTitle) pageTitle.innerText = 'Forms';
                            const catHeaderTitle = document.getElementById('forms-category-header-title');
                            if (catHeaderTitle) catHeaderTitle.innerText = 'Forms';
                            const tableContainer = document.getElementById('custom-forms-list-body');
                            if (tableContainer) {
                                tableContainer.innerHTML = `
                                    <tr>
                                        <td colspan="6" class="text-center py-5 text-muted">
                                            <i class="bi bi-folder-x fs-1 d-block mb-2 text-secondary"></i>
                                            <h6 class="fw-bold mb-1">No Form Categories Available</h6>
                                            <p class="fs-7 mb-3">Create custom forms for your department by adding a new category first.</p>
                                            <button class="btn btn-primary btn-sm rounded-pill px-3" onclick="openCreateCategoryModal()">
                                                <i class="bi bi-plus-lg me-1"></i> Create New Category
                                            </button>
                                        </td>
                                    </tr>`;
                            }
                        }
                    } else {
                        const errData = await res.json().catch(() => ({}));
                        showToast(errData.detail || 'Failed to delete category.');
                    }
                } catch(e) { showToast('Error deleting category.'); }
            }

            let builderFieldIndex = 0;

            function openCreateCustomFormModal() {
                document.getElementById('builderFormName').value = '';
                document.getElementById('builderFormCategory').value = currentFormCategory || 'IT Forms';
                const container = document.getElementById('builderFieldsContainer');
                if (container) {
                    container.innerHTML = '';
                    builderFieldIndex = 0;
                    addBuilderField(); // Add initial default text field
                }
                currentBsModal = new bootstrap.Modal(document.getElementById('createCustomFormModal'));
                currentBsModal.show();
            }

            function addBuilderField() {
                const container = document.getElementById('builderFieldsContainer');
                if (!container) return;
                builderFieldIndex++;
                const fieldId = `field_${builderFieldIndex}`;
                const cardHtml = `
                    <div class="card p-3 border shadow-sm builder-field-card" id="${fieldId}">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="badge bg-light text-dark border fw-semibold fs-7">Field #${builderFieldIndex}</span>
                            <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2" onclick="removeBuilderField('${fieldId}')" title="Remove Field">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                        <div class="row g-2">
                            <div class="col-md-7">
                                <label class="form-label fw-semibold text-secondary fs-7 mb-1">FIELD LABEL</label>
                                <input type="text" class="form-control form-control-sm field-label-input" placeholder="e.g. Serial Number">
                            </div>
                            <div class="col-md-5">
                                <label class="form-label fw-semibold text-secondary fs-7 mb-1">FIELD TYPE</label>
                                <select class="form-select form-select-sm field-type-select">
                                    <option value="text">Short Text Input</option>
                                    <option value="textarea">Paragraph / Textarea</option>
                                    <option value="dropdown">Dropdown / Select</option>
                                    <option value="checkbox">Checkbox</option>
                                    <option value="date">Date Picker</option>
                                    <option value="file">File Upload</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-check mt-2">
                            <input class="form-check-input field-required-check" type="checkbox" id="req_${fieldId}">
                            <label class="form-check-label fs-7 text-muted" for="req_${fieldId}">Required field</label>
                        </div>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', cardHtml);
            }

            function removeBuilderField(fieldId) {
                const el = document.getElementById(fieldId);
                if (el) el.remove();
            }

            async function submitCustomFormBuilder() {
                const name = document.getElementById('builderFormName').value.trim();
                const catEl = document.getElementById('builderFormCategory') || document.getElementById('newFormCategorySelect');
                const category = catEl ? catEl.value : currentFormCategory;

                if (!name) {
                    showToast('Please enter a form name.');
                    return;
                }

                const fieldCards = document.querySelectorAll('.builder-field-card');
                const fields = [];
                fieldCards.forEach(card => {
                    const label = card.querySelector('.field-label-input').value.trim() || 'Untitled Field';
                    const type = card.querySelector('.field-type-select').value;
                    const required = card.querySelector('.field-required-check').checked;
                    fields.push({ label, type, required });
                });

                const token = await getAdminAuthToken();
                try {
                    const res = await fetch('/api/forms', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({
                            category: category,
                            name: name,
                            assigned_groups: ['All users group'],
                            schema_fields: fields
                        })
                    });

                    if (res.ok) {
                        showToast(`Form '${name}' created and published successfully!`);
                        if (currentBsModal) currentBsModal.hide();
                        await loadCustomForms(category);
                    } else {
                        showToast('Failed to save custom form.');
                    }
                } catch(err) {
                    showToast('Error saving custom form.');
                }
            }

            document.addEventListener("DOMContentLoaded", async function() {
                checkAuthentication();
                await getAdminAuthToken();
                await loadConnecteamDirectory();
                await loadCategoryTabsBar();
                await handleUrlRoutingOnLoad();
            });
        </script>
    
    <!-- Generic Confirm Modal -->
    <div class="modal fade" id="genericConfirmModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered" style="max-width: 440px;">
            <div class="modal-content border-0 shadow-lg p-3" style="border-radius: 18px;">
                <div class="modal-header border-0 pb-0 pt-2 px-3 align-items-center">
                    <h5 class="modal-title fw-bold text-dark m-0" id="confirmModalTitle" style="font-size: 20px;">Confirm Action</h5>
                    <button type="button" class="btn-close text-muted" data-bs-dismiss="modal" aria-label="Close" style="font-size: 12px; background-color: #f1f3f5; border-radius: 50%; padding: 8px;"></button>
                </div>
                <div class="modal-body px-3 py-3">
                    <p class="m-0 text-muted" id="confirmModalMessage" style="font-size: 14px; line-height: 1.5;">Are you sure?</p>
                </div>
                <div class="modal-footer border-0 pt-0 pb-2 px-3 d-flex justify-content-end gap-2">
                    <button type="button" class="btn btn-light fw-medium border" data-bs-dismiss="modal" style="border-radius: 10px; padding: 8px 18px; color: #333; background: #fff;">Cancel</button>
                    <button type="button" class="btn btn-danger fw-medium" id="confirmModalBtn" style="border-radius: 10px; padding: 8px 18px; background-color: #f02849; border: none;">Confirm</button>
                </div>
            </div>
        </div>
    </div>

        <!-- WORKSPACE TOOLS FLYOUT MODAL -->
        <div class="modal fade" id="workspaceToolsFlyoutModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-scrollable modal-lg" style="max-width: 700px; margin-left: 260px; margin-top: 60px;">
                <div class="modal-content border-0 shadow-lg rounded-4">
                    <div class="modal-header border-bottom p-3">
                        <h6 class="modal-title fw-bold text-dark m-0"><i class="bi bi-grid-3x3-gap-fill text-primary me-2"></i>Explore tools for your workspace</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="row g-3">
                            <div class="col-md-4 border-end pe-3">
                                <div class="list-group list-group-flush fs-7 fw-medium">
                                    <a class="list-group-item list-group-item-action border-0 rounded-3 active"><i class="bi bi-star-fill text-warning me-2"></i>Recommended</a>
                                    <a class="list-group-item list-group-item-action border-0 rounded-3">All</a>
                                    <a class="list-group-item list-group-item-action border-0 rounded-3">Operations</a>
                                    <a class="list-group-item list-group-item-action border-0 rounded-3">Communications</a>
                                    <a class="list-group-item list-group-item-action border-0 rounded-3">HR & Skills</a>
                                </div>
                            </div>
                            <div class="col-md-8 ps-3">
                                <div class="p-3 border rounded-3 bg-light d-flex align-items-center justify-content-between mb-3 shadow-sm">
                                    <div class="d-flex align-items-center gap-3">
                                        <div class="rounded-3 bg-primary text-white d-flex align-items-center justify-content-center" style="width: 42px; height: 42px; font-size: 20px;">
                                            <i class="bi bi-file-earmark-text"></i>
                                        </div>
                                        <div>
                                            <h6 class="fw-bold mb-0 text-dark">Forms <span class="badge bg-success-subtle text-success fs-8 ms-1"><i class="bi bi-check-lg"></i> Added</span></h6>
                                            <small class="text-muted fs-8">Digitize processes, collect data, and automate work</small>
                                        </div>
                                    </div>
                                    <button class="btn btn-outline-primary btn-sm rounded-pill px-3" onclick="openCreateCategoryModalFromFlyout()">+ Add Category</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

</body>
    </html>
    """
