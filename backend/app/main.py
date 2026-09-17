from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .database import engine, Base, SessionLocal
from .models import JobCategory, JobSubItem, Employee, PunchLog
from .limiter import limiter
from .routers import auth, punch, jobs, manager, dtr
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
def get_admin_dashboard():
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
                    <a class="nav-link" id="nav-forms-it" onclick="switchTab('forms-it')"><i class="bi bi-file-earmark-text"></i> IT Forms</a>
                    <a class="nav-link" id="nav-forms-admin" onclick="switchTab('forms-admin')"><i class="bi bi-file-earmark-richtext"></i> Admin Forms</a>
                    <a class="nav-link" id="nav-forms-hr" onclick="switchTab('forms-hr')"><i class="bi bi-file-earmark-person"></i> HR Forms</a>

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
                                        <h4 class="fw-bold text-dark m-0 d-flex align-items-center gap-2">
                                            <i class="bi bi-file-earmark-text text-primary"></i> <span id="forms-category-header-title">IT Forms</span>
                                        </h4>
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

                                        <button class="btn btn-primary-custom" onclick="openCreateCustomFormModal()"><i class="bi bi-plus-lg me-1"></i> Add new</button>
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
                    <label class="form-label fw-semibold text-secondary" style="font-size: 12px;">ASSIGN GROUP ADMINS</label>
                    <select class="form-select" id="groupAdminAssignSelect" onchange="showToast('Group admin assigned.')">
                        <option value="xinxaola" selected>Super Admin Xenon (xinxaola)</option>
                        <option value="3286">Jaypee Balonzo (System Admin - 3286)</option>
                    </select>
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
                        renderBrandSelectorOptions();
                        renderConnecteamProvisioningTable();
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

            function getStoredBrands() {
                const stored = localStorage.getItem('smart_brands_list');
                if (stored) {
                    try { return JSON.parse(stored); } catch(e) {}
                }
                localStorage.setItem('smart_brands_list', JSON.stringify(defaultBrandsInitial));
                return defaultBrandsInitial;
            }

            function setStoredBrands(brands) {
                localStorage.setItem('smart_brands_list', JSON.stringify(brands));
            }

            function getStoredGroups() {
                const stored = localStorage.getItem('smart_groups_list');
                if (stored) {
                    try { return JSON.parse(stored); } catch(e) {}
                }
                localStorage.setItem('smart_groups_list', JSON.stringify(defaultGroupsInitial));
                return defaultGroupsInitial;
            }

            function setStoredGroups(groups) {
                localStorage.setItem('smart_groups_list', JSON.stringify(groups));
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

            function populateDepartmentDropdownOptions(selectedVal) {
                const allGroups = getStoredGroups();
                let optionsHtml = '';
                allGroups.forEach(g => {
                    const isSel = (g.name === selectedVal || g.dept === selectedVal) ? 'selected' : '';
                    optionsHtml += `<option value="${g.name}" ${isSel}>${g.name}</option>`;
                });
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

            function switchTab(tab) {
                document.getElementById('tab-clock').style.display = 'none';
                document.getElementById('tab-jobs').style.display = 'none';
                document.getElementById('tab-users').style.display = 'none';
                const formsView = document.getElementById('tab-forms-view');
                if (formsView) formsView.style.display = 'none';

                document.getElementById('nav-clock').classList.remove('active');
                document.getElementById('nav-jobs').classList.remove('active');
                document.getElementById('nav-users').classList.remove('active');
                const navIt = document.getElementById('nav-forms-it');
                const navAdmin = document.getElementById('nav-forms-admin');
                const navHr = document.getElementById('nav-forms-hr');
                if (navIt) navIt.classList.remove('active');
                if (navAdmin) navAdmin.classList.remove('active');
                if (navHr) navHr.classList.remove('active');

                if (tab.startsWith('forms-')) {
                    if (formsView) formsView.style.display = 'block';
                    const navTarget = document.getElementById('nav-' + tab);
                    if (navTarget) navTarget.classList.add('active');

                    const catName = tab === 'forms-it' ? 'IT Forms' : (tab === 'forms-admin' ? 'Admin Forms' : 'HR Forms');
                    document.getElementById('page-title').innerText = catName;
                    closeFormDetailSubmissions();
                    loadCustomForms(catName);
                    return;
                }

                document.getElementById('tab-' + tab).style.display = 'block';
                document.getElementById('nav-' + tab).classList.add('active');

                if (tab === 'clock') {
                    document.getElementById('page-title').innerText = 'Time Clock';
                    setTimeout(() => { if (map) map.invalidateSize(); else initMap(); }, 200);
                    loadPunchMap();
                    loadTimeClockHistory();
                } else if (tab === 'jobs') {
                    document.getElementById('page-title').innerText = 'Smart Groups';
                    loadConnecteamDirectory().then(() => {
                        renderBrandSelectorOptions();
                        renderConnecteamProvisioningTable();
                    });
                } else if (tab === 'users') {
                    document.getElementById('page-title').innerText = 'Users Directory';
                    loadConnecteamDirectory();
                }
            }

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

            function renderBrandSelectorOptions() {
                const brands = getStoredBrands();
                let filterHtml = '<option value="ALL">All Brands</option>';
                let modalHtml = '';

                brands.forEach(b => {
                    const sel = (b === selectedBrandView) ? 'selected' : '';
                    filterHtml += `<option value="${b}" ${sel}>${b}</option>`;
                    modalHtml += `<option value="${b}">${b}</option>`;
                });

                document.getElementById('selectedBrandFilter').innerHTML = filterHtml;
                document.getElementById('modalBrandSelect').innerHTML = modalHtml;
            }

            function openAddBrandModal() {
                document.getElementById('modalNewBrandName').value = '';
                currentBsModal = new bootstrap.Modal(document.getElementById('addBrandModal'));
                currentBsModal.show();
            }

            function saveNewBrandModal() {
                const bName = document.getElementById('modalNewBrandName').value.trim();
                if (!bName) {
                    showToast('Please enter a brand name.');
                    return;
                }

                let brands = getStoredBrands();
                if (!brands.includes(bName)) {
                    brands.push(bName);
                    setStoredBrands(brands);
                }

                renderBrandSelectorOptions();
                renderConnecteamProvisioningTable();
                showToast(`New Brand "${bName}" created.`);
                if (currentBsModal) currentBsModal.hide();
            }

            function filterGroupByBrand(brandVal) {
                selectedBrandView = brandVal;
                renderConnecteamProvisioningTable();
            }

            function renderConnecteamProvisioningTable() {
                const brands = getStoredBrands();
                const allGroups = getStoredGroups();

                let visibleBrands = (selectedBrandView === 'ALL') ? brands : brands.filter(b => b === selectedBrandView);
                document.getElementById('groups-count-label').innerText = `${allGroups.length} groups total`;

                let panelsHtml = '';

                visibleBrands.forEach((brandName, bIdx) => {
                    const brandGroups = allGroups.filter(g => (g.brand || 'Head Office') === brandName);

                    let rowsHtml = '';
                    brandGroups.forEach((g) => {
                        const groupMembers = globalUsersList.filter(u => u.department === g.name || u.department === g.dept);
                        const connectedStr = `${groupMembers.length} / ${groupMembers.length}`;

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
                                        <div class="d-flex align-items-center">
                                            <span class="avatar-chip bg-primary text-white">SA</span>
                                            <span class="avatar-chip bg-secondary text-white">JB</span>
                                            <span class="avatar-chip bg-dark text-white">+10</span>
                                        </div>
                                        <button class="btn btn-sm btn-outline-custom text-danger py-0 px-2" onclick="event.stopPropagation(); deleteSubGroup('${g.name}')"><i class="bi bi-trash"></i></button>
                                    </div>
                                </td>
                            </tr>`;
                    });

                    panelsHtml += `
                        <div class="card-custom p-0 overflow-hidden mb-4">
                            <div class="p-3 bg-light border-bottom d-flex align-items-center justify-content-between">
                                <div class="d-flex align-items-center gap-2">
                                    <i class="bi bi-chevron-right text-warning fs-6" style="cursor:pointer;" id="chevron-brand-${bIdx}" onclick="toggleBrandCollapse('${bIdx}')"></i>
                                    <span class="fw-bold text-dark fs-6" style="cursor:pointer;" onclick="toggleBrandCollapse('${bIdx}')">${brandName}</span>
                                    <button class="btn btn-sm btn-outline-custom ms-2 py-0 px-2" onclick="openRenameBrandModal('${brandName}')"><i class="bi bi-pencil"></i> Edit</button>
                                    <button class="btn btn-sm btn-outline-custom text-danger py-0 px-2" onclick="deleteBrandLocation('${brandName}')"><i class="bi bi-trash"></i> Delete Brand</button>
                                </div>
                                <button class="btn btn-sm btn-outline-custom" onclick="openAddGroupModal('${brandName}')"><i class="bi bi-plus-lg me-1"></i> Add Group to ${brandName}</button>
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

            function saveRenameBrand() {
                const newBrandName = document.getElementById('modalRenameBrandName').value.trim();
                if (!newBrandName) {
                    showToast('Please enter a valid brand name.');
                    return;
                }

                let brands = getStoredBrands();
                const idx = brands.indexOf(editingBrandNameTarget);
                if (idx !== -1) brands[idx] = newBrandName;
                setStoredBrands(brands);

                let groups = getStoredGroups();
                groups.forEach(g => {
                    if (g.brand === editingBrandNameTarget) g.brand = newBrandName;
                });
                setStoredGroups(groups);

                if (selectedBrandView === editingBrandNameTarget) selectedBrandView = newBrandName;

                renderBrandSelectorOptions();
                renderConnecteamProvisioningTable();
                showToast('Brand name updated.');
                if (currentBsModal) currentBsModal.hide();
            }

            function deleteBrandLocation(brandName) {
                if (!confirm(`Are you sure you want to delete Brand "${brandName}" and all its assigned groups?`)) return;

                let brands = getStoredBrands().filter(b => b !== brandName);
                setStoredBrands(brands);

                let groups = getStoredGroups().filter(g => g.brand !== brandName);
                setStoredGroups(groups);

                if (selectedBrandView === brandName) selectedBrandView = 'ALL';

                renderBrandSelectorOptions();
                renderConnecteamProvisioningTable();
                showToast(`Brand ${brandName} deleted.`);
            }

            function deleteSubGroup(groupName) {
                if (!confirm(`Are you sure you want to remove group "${groupName}"?`)) return;

                let groups = getStoredGroups().filter(g => g.name !== groupName);
                setStoredGroups(groups);

                localStorage.removeItem('smart_group_members_' + groupName);

                renderConnecteamProvisioningTable();
                showToast(`Group "${groupName}" removed.`);
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

            function openAddGroupModal(defaultBrand = 'Head Office') {
                renderBrandSelectorOptions();
                document.getElementById('modalGroupName').value = '';
                document.getElementById('modalBrandSelect').value = defaultBrand;
                currentBsModal = new bootstrap.Modal(document.getElementById('groupModal'));
                currentBsModal.show();
            }

            function saveSmartGroup() {
                const name = document.getElementById('modalGroupName').value.trim();
                const brand = document.getElementById('modalBrandSelect').value;
                if (!name) {
                    showToast('Please enter a group name.');
                    return;
                }

                let groups = getStoredGroups();
                groups.push({
                    name: name,
                    creator: 'Super Admin',
                    selected: '10 selected',
                    brand: brand,
                    dept: name.replace('HO - ', '')
                });
                setStoredGroups(groups);

                renderConnecteamProvisioningTable();
                showToast('Smart Group created.');
                if (currentBsModal) currentBsModal.hide();
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

            // CUSTOM FORMS STATE & HANDLERS
            let currentFormCategory = 'IT Forms';
            let currentFormTabStatus = 'ACTIVE';

            const mockCustomFormsData = [
                { id: 101, category: 'IT Forms', name: 'Email Requisition Form', status: 'Published', entries: 151, views: 70, assignedGroups: ['All users group'], createdBy: 'Drenzo Pornel', createdAvatar: 'DP', administratedBy: '+5', dateCreated: '06/11/2024', isArchived: false, isNew: false },
                { id: 102, category: 'IT Forms', name: 'Asset Offsite Form', status: 'Published', entries: 1, views: 5, assignedGroups: ['All users group'], createdBy: 'Jaypee Balonzo', createdAvatar: 'JP', administratedBy: '+5', dateCreated: '06/25/2026', isArchived: false, isNew: false },
                { id: 103, category: 'IT Forms', name: 'Internet Connection Survey', status: 'Published', entries: 7, views: 54, assignedGroups: ['8 groups'], createdBy: 'Jaypee Balonzo', createdAvatar: 'JP', administratedBy: '+5', dateCreated: '03/04/2025', isArchived: false, isNew: false },
                { id: 104, category: 'IT Forms', name: 'Service Report', status: 'Published', entries: 67, views: 5, assignedGroups: ['HO - I.T.'], createdBy: 'Tonghie Sy Jr', createdAvatar: 'TS', administratedBy: '+5', dateCreated: '06/20/2024', isArchived: false, isNew: false },
                { id: 105, category: 'IT Forms', name: 'Internet Speed Survey', status: 'Published', entries: 8, views: 108, assignedGroups: ['14 groups'], createdBy: 'Drenzo Pornel', createdAvatar: 'DP', administratedBy: '+5', dateCreated: '06/05/2024', isArchived: false, isNew: true },
                { id: 201, category: 'Admin Forms', name: 'Office Supply Requisition', status: 'Published', entries: 42, views: 89, assignedGroups: ['All users group'], createdBy: 'Super Admin Xenon', createdAvatar: 'SA', administratedBy: '+3', dateCreated: '01/15/2026', isArchived: false, isNew: false },
                { id: 301, category: 'HR Forms', name: 'Leave Application Form', status: 'Published', entries: 230, views: 512, assignedGroups: ['All users group'], createdBy: 'Super Admin Xenon', createdAvatar: 'SA', administratedBy: '+4', dateCreated: '02/10/2026', isArchived: false, isNew: false }
            ];

            function loadCustomForms(category = 'IT Forms') {
                currentFormCategory = category;
                document.getElementById('forms-category-header-title').innerText = category;

                const filtered = mockCustomFormsData.filter(f => f.category === category);
                const activeCount = filtered.filter(f => !f.isArchived).length;
                const archivedCount = filtered.filter(f => f.isArchived).length;

                document.getElementById('count-active-forms').innerText = activeCount;
                document.getElementById('count-archived-forms').innerText = archivedCount;

                renderCustomFormsTable();
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

            function openCreateCustomFormModal() {
                const formTitle = prompt(`Create new ${currentFormCategory} Form Name:`);
                if (!formTitle || formTitle.trim() === '') return;

                const newFormObj = {
                    id: Date.now(),
                    category: currentFormCategory,
                    name: formTitle.trim(),
                    status: 'Published',
                    entries: 0,
                    views: 1,
                    assignedGroups: ['All users group'],
                    createdBy: 'Super Admin Xenon',
                    createdAvatar: 'SA',
                    administratedBy: '+1',
                    dateCreated: '09/18/2026',
                    isArchived: false,
                    isNew: true
                };

                mockCustomFormsData.unshift(newFormObj);
                showToast(`Form '${formTitle}' created successfully!`);
                loadCustomForms(currentFormCategory);
            }

            document.addEventListener("DOMContentLoaded", async function() {
                checkAuthentication();
                await getAdminAuthToken();
                await loadConnecteamDirectory();
                switchTab('clock');
            });
        </script>
    </body>
    </html>
    """
