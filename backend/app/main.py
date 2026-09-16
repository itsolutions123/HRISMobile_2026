from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .database import engine, Base, SessionLocal
from .models import JobCategory, JobSubItem, Employee, PunchLog
from .routers import auth, punch, jobs, manager, dtr

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS DTR Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        existing_user = db.query(Employee).filter(Employee.employee_id == "3286").first()
        if not existing_user:
            test_user = Employee(
                employee_id="3286",
                name="Jaypee Balonzo",
                first_name="Jaypee",
                last_name="Balonzo",
                position="IT System Administrator",
                department="Admin",
                password_hash="bigtime@123",
                mobile_phone="+63 998 940 0957",
                email="itsupport.associate@bigtimeempire.com",
                role="Admin",
                status="APPROVED"
            )
            db.add(test_user)
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
        <title>HRIS Portal</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
                --accent-primary: #0284c7;
                --accent-hover: #0369a1;
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
                color: #38bdf8;
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
            #map {
                height: 520px;
                width: 100%;
                border-radius: 12px;
                border: 1px solid var(--border-color);
            }
            .avatar-circle {
                width: 32px;
                height: 32px;
                background-color: #e0f2fe;
                color: #0369a1;
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
                background-color: var(--accent-primary);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
                transition: background-color 0.15s ease;
            }
            .btn-primary-custom:hover {
                background-color: var(--accent-hover);
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
                color: var(--accent-primary);
                border-bottom: 2px solid var(--accent-primary);
                background: transparent;
            }
            .readonly-box {
                background-color: #f8fafc;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: var(--text-primary);
                font-weight: 500;
            }
            .filter-pill {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                color: #0284c7;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 16px;
            }
            .offcanvas-group-drawer {
                width: 720px !important;
                border-left: 1px solid var(--border-color);
            }
        </style>
    </head>
    <body>
        <div class="container-fluid p-0">
            <div class="row g-0">
                <!-- SIDEBAR -->
                <div class="col-md-2 sidebar p-3">
                    <div class="d-flex align-items-center gap-2 mb-4 px-2 pt-2">
                        <i class="bi bi-shield-check text-info fs-5"></i>
                        <span class="fs-6 fw-bold text-white tracking-tight">HRIS Portal</span>
                    </div>

                    <div class="section-label">Core Workspace</div>
                    <a class="nav-link" id="nav-clock" onclick="switchTab('clock')"><i class="bi bi-stopwatch"></i> Time Clock</a>
                    <a class="nav-link active" id="nav-jobs" onclick="switchTab('jobs')"><i class="bi bi-diagram-3"></i> Smart Groups</a>
                    <a class="nav-link d-flex justify-content-between align-items-center" id="nav-users" onclick="switchTab('users')">
                        <span><i class="bi bi-people me-2"></i> Users & Directory</span>
                    </a>

                    <div class="section-label">Management</div>
                    <a class="nav-link" onclick="showToast('Scheduling accessible via Mobile workspace.')"><i class="bi bi-calendar3"></i> Scheduling</a>
                    <a class="nav-link" onclick="window.open('/api/dtr/export', '_blank')"><i class="bi bi-download"></i> Export DTR</a>
                </div>

                <!-- MAIN CONTENT -->
                <div class="col-md-10">
                    <div class="top-bar d-flex justify-content-between align-items-center">
                        <h6 class="m-0 fw-bold text-dark" id="page-title">Smart Groups</h6>

                        <div class="dropdown profile-dropdown">
                            <button class="btn border-0 d-flex align-items-center gap-2 p-1" type="button" data-bs-toggle="dropdown">
                                <div class="avatar-circle">JB</div>
                                <div class="text-start d-none d-sm-block ms-1">
                                    <div class="fw-bold text-dark lh-1" style="font-size: 13px;">Jaypee Balonzo</div>
                                    <small class="text-muted" style="font-size: 11px;">System Admin (3286)</small>
                                </div>
                                <i class="bi bi-chevron-down text-muted ms-1" style="font-size: 10px;"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow-sm border-0 mt-2">
                                <li><a class="dropdown-item py-2 fs-7" onclick="showToast('Admin ID: 3286 | Status: Active')"><i class="bi bi-person me-2"></i> Profile details</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item py-2 fs-7 text-danger" onclick="location.reload()"><i class="bi bi-box-arrow-right me-2"></i> Sign out</a></li>
                            </ul>
                        </div>
                    </div>

                    <div class="p-4">
                        <!-- TAB 1: TIME CLOCK -->
                        <div id="tab-clock" style="display:none;">
                            <div class="card-custom">
                                <div class="d-flex justify-content-between align-items-center mb-4">
                                    <h6 class="fw-bold m-0 text-dark">Live Clock Feed</h6>
                                    <button class="btn btn-outline-custom" onclick="loadPunchMap()"><i class="bi bi-arrow-clockwise me-1"></i> Refresh</button>
                                </div>
                                <div class="row g-4">
                                    <div class="col-md-4">
                                        <div id="punch-list-sidebar" style="max-height: 400px; overflow-y: auto;">
                                            <p class="text-muted fs-7">Loading recent logs...</p>
                                        </div>
                                    </div>
                                    <div class="col-md-8"><div id="map"></div></div>
                                </div>
                            </div>
                        </div>

                        <!-- TAB 2: CONNECTEAM SMART GROUPS PROVISIONING -->
                        <div id="tab-jobs">
                            <!-- TOP OVERVIEW ACTIONS -->
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div class="d-flex align-items-center gap-2">
                                    <button class="btn btn-outline-custom text-primary fw-bold" onclick="openAddBrandModal()"><i class="bi bi-plus-lg me-1"></i> Add Brand</button>
                                    <select class="form-select border-0 fw-bold text-dark bg-light" style="width: 180px;" id="selectedBrandFilter" onchange="filterGroupByBrand(this.value)">
                                    </select>
                                </div>
                                <span class="text-muted fw-semibold" style="font-size: 12px;" id="groups-count-label">0 groups total</span>
                            </div>

                            <!-- DYNAMIC COLLAPSIBLE BRAND PANELS CONTAINER -->
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
                                            <a class="nav-link active" id="user-subtab-active" onclick="filterUserCategory('APPROVED')">Users (88/87)</a>
                                        </li>
                                        <li class="nav-item">
                                            <a class="nav-link" id="user-subtab-admins" onclick="filterUserCategory('ADMIN')">Admins (34)</a>
                                        </li>
                                        <li class="nav-item">
                                            <a class="nav-link" id="user-subtab-archived" onclick="filterUserCategory('ARCHIVED')">Archived (124)</a>
                                        </li>
                                    </ul>

                                    <div class="d-flex align-items-center gap-2">
                                        <small class="text-muted fw-semibold">Permissions</small>
                                        <div class="d-flex align-items-center me-2">
                                            <span class="avatar-chip bg-primary text-white">JB</span>
                                            <span class="avatar-chip bg-dark text-white">+8</span>
                                        </div>
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Pending approvals view')">Pending approvals</button>
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
                                        <button class="btn btn-primary-custom" onclick="showToast('Export / Add users')"><i class="bi bi-plus-lg me-1"></i> Add users</button>
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
                                                </tr>
                                            </thead>
                                            <tbody id="directory-users-tbody">
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <div id="user-profile-dashboard-view" style="display:none;" class="mt-2">
                                <button class="btn btn-outline-custom btn-sm mb-3" onclick="closeUserProfileDashboard()"><i class="bi bi-arrow-left me-1"></i> Back to Users Directory</button>

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
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Reward feature')"><i class="bi bi-gift me-1"></i> Send reward</button>
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Options menu')">Options <i class="bi bi-chevron-down ms-1"></i></button>
                                        <button class="btn btn-outline-custom btn-sm" onclick="showToast('Text message initiated')"><i class="bi bi-chat-text me-1"></i> Text Message</button>
                                    </div>
                                </div>

                                <div class="row g-4">
                                    <div class="col-md-3">
                                        <div class="card-custom p-3 mb-3">
                                            <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Personal Details</h6>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">First name *</small><div class="readonly-box" id="profile-detail-firstname">Alejandro</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Last name *</small><div class="readonly-box" id="profile-detail-lastname">Luanzon Jr.</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Mobile phone *</small><div class="readonly-box" id="profile-detail-mobile">+63 912 794 6060</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Email *</small><div class="readonly-box text-truncate" id="profile-detail-email">amluanzon1979@gmail.com</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Employee ID *</small><div class="readonly-box" id="profile-detail-empid">3490</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Birthday</small><div class="readonly-box">02/02/1979</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Gender</small><div class="readonly-box">Male</div></div>
                                        </div>

                                        <div class="card-custom p-3 mb-3">
                                            <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Company Related Info</h6>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Employment Start Date</small><div class="readonly-box">05/19/2025</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Direct manager</small><div class="readonly-box">Jaypee Balonzo</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Location</small><div class="readonly-box">Pares In-Store</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Sub Location / Branch</small><div class="readonly-box">Head Office - Accounting</div></div>
                                            <div class="mb-3"><small class="text-muted fw-semibold d-block mb-1">Department</small><div class="readonly-box" id="profile-detail-dept">Operations</div></div>
                                        </div>

                                        <div class="card-custom p-3 mb-3">
                                            <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Government Details</h6>
                                            <div class="mb-2"><small class="text-muted d-block">SSS Number</small><div class="readonly-box">-</div></div>
                                            <div class="mb-2"><small class="text-muted d-block">PHILHEALTH Number</small><div class="readonly-box">-</div></div>
                                            <div class="mb-2"><small class="text-muted d-block">PAG-IBIG Number</small><div class="readonly-box">-</div></div>
                                        </div>

                                        <div class="card-custom p-3 mb-3">
                                            <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Groups (3)</h6>
                                            <div class="d-flex flex-wrap gap-1">
                                                <span class="badge bg-light text-dark border">All users group</span>
                                                <span class="badge bg-light text-dark border">Operations - Employee (Form)</span>
                                                <span class="badge bg-light text-dark border">Operations - Pares</span>
                                            </div>
                                        </div>

                                        <div class="card-custom p-3">
                                            <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">Usage info</h6>
                                            <div class="d-flex justify-content-between mb-2"><small class="text-muted">Total sessions</small><strong class="text-dark">1439</strong></div>
                                            <div class="d-flex justify-content-between mb-2"><small class="text-muted">Days in system</small><strong class="text-dark">484</strong></div>
                                            <div class="d-flex justify-content-between"><small class="text-muted">Last logged-in</small><strong class="text-dark">Tue, Sep 15 at 17:05</strong></div>
                                        </div>
                                    </div>

                                    <div class="col-md-9">
                                        <div class="card-custom p-4">
                                            <ul class="nav nav-tabs nav-tabs-connecteam border-bottom mb-4">
                                                <li class="nav-item"><a class="nav-link active">Employment</a></li>
                                                <li class="nav-item"><a class="nav-link">Activity</a></li>
                                                <li class="nav-item"><a class="nav-link">Time off</a></li>
                                                <li class="nav-item"><a class="nav-link">Notes</a></li>
                                                <li class="nav-item"><a class="nav-link">Forms</a></li>
                                                <li class="nav-item"><a class="nav-link">Documents</a></li>
                                                <li class="nav-item"><a class="nav-link">Recognitions</a></li>
                                                <li class="nav-item"><a class="nav-link">Timeline</a></li>
                                                <li class="nav-item"><a class="nav-link">Payslips</a></li>
                                            </ul>

                                            <h6 class="fw-bold text-dark mb-3">Compensation Details</h6>
                                            <div class="p-3 bg-light rounded-3 border mb-4">
                                                <div class="row g-3">
                                                    <div class="col-md-6"><small class="text-muted d-block">Worker Type</small><strong class="text-dark">Regular Staff</strong></div>
                                                    <div class="col-md-6"><small class="text-muted d-block">Pay Type</small><strong class="text-dark">Monthly Rate</strong></div>
                                                    <div class="col-md-6"><small class="text-muted d-block">Overtime Eligibility</small><strong class="text-dark">Eligible</strong></div>
                                                    <div class="col-md-6"><small class="text-muted d-block">Standard Hours</small><strong class="text-dark">8 hrs / day</strong></div>
                                                </div>
                                            </div>

                                            <h6 class="fw-bold text-dark mb-3">Regular working hours</h6>
                                            <div class="p-3 bg-light rounded-3 border">
                                                <div class="d-flex align-items-center gap-3">
                                                    <div class="avatar-circle bg-danger-subtle text-danger fs-6" style="width: 40px; height: 44px;">Mon</div>
                                                    <div>
                                                        <strong class="text-dark d-block">Mon - Fri • 9am - 5pm</strong>
                                                        <small class="text-muted">Defined regular working policy</small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

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
                        <option value="3286" selected>Jaypee Balonzo (System Admin - 3286)</option>
                        <option value="1002">Test Manager (Manager - 1002)</option>
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
                            <small class="text-muted fw-semibold d-block">Clocked In</small>
                            <h3 class="fw-bold text-success m-0 mt-1" id="detail-logged-count">0 / 0</h3>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card-custom p-3">
                            <small class="text-muted fw-semibold d-block">Created info</small>
                            <small class="fw-bold text-dark d-block mt-1">06/05/2026 by Jaypee Balonzo</small>
                        </div>
                    </div>
                </div>

                <div class="d-flex align-items-center gap-2 mb-4">
                    <span class="text-muted fw-semibold" style="font-size: 12px;">Group filtered by</span>
                    <span class="filter-pill" id="filter-brand-pill">Location is Head Office</span>
                    <span class="filter-pill" id="filter-dept-pill">Department is Admin</span>
                    <button class="btn btn-link btn-sm text-primary fw-bold text-decoration-none p-0 ms-2" onclick="showToast('Filter editor opened.')">Edit filters</button>
                </div>

                <div class="card-custom p-0 overflow-hidden">
                    <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                        <input type="text" class="form-control" style="width: 260px;" placeholder="Search group members..." onkeyup="filterDetailMembers(this.value)">
                        <button class="btn btn-primary-custom btn-sm" onclick="openEnrollMembersModal()"><i class="bi bi-person-plus me-1"></i> Add Member</button>
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
                                    <th class="text-end">Actions</th>
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

        <!-- ENROLL MEMBERS MODAL -->
        <div class="modal fade" id="enrollMembersModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-bottom p-4">
                        <h6 class="modal-title fw-bold text-dark m-0">Enroll Members into Group</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="table-responsive" style="max-height: 350px; overflow-y: auto;">
                            <table class="table align-middle m-0">
                                <thead>
                                    <tr>
                                        <th width="30"><input type="checkbox" class="form-check-input" id="select-all-enroll" onclick="toggleSelectAllEnroll(this)"></th>
                                        <th>FULL NAME</th>
                                        <th>EMPLOYEE ID</th>
                                        <th>DEPARTMENT</th>
                                    </tr>
                                </thead>
                                <tbody id="enroll-modal-tbody">
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer border-top p-3">
                        <button type="button" class="btn btn-outline-custom" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary-custom" onclick="confirmEnrollSelectedMembers()">Enroll Selected Members</button>
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
            let map, markersGroup;
            let currentBsModal, currentOffcanvasDrawer;
            let adminToken = '';
            let globalUsersList = [];
            let activeGroupName = 'HO - Admin';
            let selectedBrandView = 'ALL';
            let editingBrandNameTarget = '';

            const defaultBrandsInitial = ['Head Office', 'Stores', 'Commissary'];

            const defaultGroupsInitial = [
                { name: 'HO - I. T.', creator: 'Jaypee Balonzo', selected: '17 selected', brand: 'Head Office', dept: 'IT' },
                { name: 'HO - Marketing', creator: 'Jaypee Balonzo', selected: '13 selected', brand: 'Head Office', dept: 'Marketing' },
                { name: 'HO - Admin', creator: 'Jaypee Balonzo', selected: '15 selected', brand: 'Head Office', dept: 'Admin' },
                { name: 'HO - Human Resource', creator: 'Jaypee Balonzo', selected: '14 selected', brand: 'Head Office', dept: 'HR' },
                { name: 'HO - Accounting', creator: 'Jaypee Balonzo', selected: '13 selected', brand: 'Head Office', dept: 'Accounting' },
                { name: 'HO - Sales', creator: 'Jaypee Balonzo', selected: '12 selected', brand: 'Head Office', dept: 'Sales' }
            ];

            const connecteamSampleUsers = [
                { first_name: 'Alejandro', last_name: 'Luanzon Jr.', last_login: '09/15/2026', employment_start: '05/19/2025', department: 'Operations', kiosk_code: '5668', date_added: '05/20/2025', added_by: 'Isabel Anne L.', role: 'Admin', email: 'amluanzon1979@gmail.com', mobile: '+63 912 794 6060' },
                { first_name: 'Angelica', last_name: 'Jabay', last_login: '09/14/2026', employment_start: '11/18/2024', department: 'Admin', kiosk_code: '9674', date_added: '11/18/2024', added_by: 'N/A', role: 'Employee', email: 'angelica.jabay@connect.com', mobile: '+63 917 111 2222' },
                { first_name: 'Angelo Gabriel', last_name: 'Bautista', last_login: '09/16/2026', employment_start: '08/03/2026', department: 'Auditor', kiosk_code: '9268', date_added: '08/12/2026', added_by: 'Jerald Vincent...', role: 'Employee', email: 'angelo.b@connect.com', mobile: '+63 918 333 4444' },
                { first_name: 'Ariane Joy', last_name: 'Pisigan', last_login: '09/15/2026', employment_start: '12/10/2021', department: 'Accounting', kiosk_code: '7433', date_added: '07/09/2024', added_by: 'N/A', role: 'Employee', email: 'ariane.p@connect.com', mobile: '+63 919 555 6666' },
                { first_name: 'Benny II', last_name: 'Villena', last_login: '09/16/2026', employment_start: '07/17/2023', department: 'HR', kiosk_code: '4292', date_added: '07/03/2024', added_by: 'N/A', role: 'Employee', email: 'benny.v@connect.com', mobile: '+63 920 777 8888' },
                { first_name: 'Bianca', last_name: 'Maramot', last_login: '09/16/2026', employment_start: '02/16/2026', department: 'Purchasing', kiosk_code: '8310', date_added: '02/18/2026', added_by: 'Ella Mae Bara...', role: 'Employee', email: 'bianca.m@connect.com', mobile: '+63 921 999 0000' }
            ];

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

            function getGroupMembersStore(groupName) {
                const key = 'smart_group_members_' + groupName;
                const stored = localStorage.getItem(key);
                if (stored) {
                    try { return JSON.parse(stored); } catch(e) {}
                }
                return null;
            }

            function setGroupMembersStore(groupName, members) {
                const key = 'smart_group_members_' + groupName;
                localStorage.setItem(key, JSON.stringify(members));
            }

            function showToast(msg) {
                document.getElementById('toastMessage').innerText = msg;
                const toast = new bootstrap.Toast(document.getElementById('liveToast'), { delay: 3500 });
                toast.show();
            }

            async function getAdminAuthToken() {
                if (adminToken) return adminToken;
                try {
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ employee_id: '3286', password: 'bigtime@123' })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        adminToken = data.access_token;
                        return adminToken;
                    }
                } catch(e) {}
                return '';
            }

            function switchTab(tab) {
                document.getElementById('tab-clock').style.display = 'none';
                document.getElementById('tab-jobs').style.display = 'none';
                document.getElementById('tab-users').style.display = 'none';

                document.getElementById('nav-clock').classList.remove('active');
                document.getElementById('nav-jobs').classList.remove('active');
                document.getElementById('nav-users').classList.remove('active');

                document.getElementById('tab-' + tab).style.display = 'block';
                document.getElementById('nav-' + tab).classList.add('active');

                if (tab === 'clock') {
                    document.getElementById('page-title').innerText = 'Time Clock';
                    setTimeout(() => { if (map) map.invalidateSize(); else initMap(); }, 200);
                    loadPunchMap();
                } else if (tab === 'jobs') {
                    document.getElementById('page-title').innerText = 'Smart Groups';
                    renderBrandSelectorOptions();
                    renderConnecteamProvisioningTable();
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
                    if (markersGroup) markersGroup.clearLayers();

                    let sidebarHtml = '';
                    logs.forEach(log => {
                        sidebarHtml += `
                            <div class="p-3 mb-2 rounded-3 bg-white border">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <span class="fw-semibold text-dark" style="font-size: 12px;">Emp ID: ${log.employee_id}</span>
                                    <span class="badge ${log.punch_type === 'CLOCK_IN' ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'}" style="font-size: 10px;">${log.punch_type}</span>
                                </div>
                                <small class="text-muted d-block" style="font-size: 11px;">${log.timestamp}</small>
                                <small class="text-secondary text-truncate d-block" style="font-size: 11px;">${log.address || 'Duty Shift'}</small>
                            </div>`;

                        if (markersGroup && log.latitude && log.longitude) {
                            L.marker([log.latitude, log.longitude])
                                .bindPopup(`<b>Employee: ${log.employee_id}</b><br>Type: ${log.punch_type}<br>Time: ${log.timestamp}`)
                                .addTo(markersGroup);
                        }
                    });

                    document.getElementById('punch-list-sidebar').innerHTML = sidebarHtml || '<p class="text-muted fs-7">No punch records found.</p>';
                } catch(e) {}
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
                        const members = getGroupMembersStore(g.name) || [];
                        const connectedStr = `${members.length} / ${members.length}`;

                        rowsHtml += `
                            <tr style="cursor: pointer;" onclick="viewGroupDetails('${g.name}', '${brandName}', '${g.dept || 'General'}')">
                                <td><input type="checkbox" class="form-check-input" onclick="event.stopPropagation()"></td>
                                <td><strong class="text-primary">${g.name}</strong></td>
                                <td><span class="fw-bold text-dark">${connectedStr}</span></td>
                                <td>
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="avatar-chip bg-info text-dark" style="margin:0;">JB</span>
                                        <span class="text-secondary fw-semibold">${g.creator || 'Jaypee Balonzo'}</span>
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
                                            <span class="avatar-chip bg-primary text-white">JB</span>
                                            <span class="avatar-chip bg-secondary text-white">EM</span>
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

                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch('/api/auth/users', { headers: { 'Authorization': 'Bearer ' + token } });
                    if (res.ok) globalUsersList = await res.json();
                } catch(e) {}

                let members = getGroupMembersStore(groupName);
                if (!members) {
                    members = [];
                    setGroupMembersStore(groupName, members);
                }

                let clockedInCount = 0;
                try {
                    const activeRes = await fetch('/api/punch/logs');
                    if (activeRes.ok) {
                        const logs = await activeRes.json();
                        const activeEmpIds = logs.filter(p => p.punch_type === 'CLOCK_IN').map(p => p.employee_id);
                        clockedInCount = members.filter(m => activeEmpIds.includes(m.employee_id || m.kiosk_code)).length;
                    }
                } catch(e) {}

                document.getElementById('detail-emp-count').innerText = members.length;
                document.getElementById('detail-logged-count').innerText = `${clockedInCount} / ${members.length}`;
                renderDetailMembers(members);

                const drawerEl = document.getElementById('groupDetailDrawer');
                currentOffcanvasDrawer = new bootstrap.Offcanvas(drawerEl);
                currentOffcanvasDrawer.show();
            }

            function renderDetailMembers(members) {
                let html = '';
                if (!members || members.length === 0) {
                    html = '<tr><td colspan="6" class="text-center text-muted py-4">No members enrolled in this group.</td></tr>';
                } else {
                    members.forEach((u, idx) => {
                        html += `
                            <tr>
                                <td>${u.first_name || u.name}</td>
                                <td>${u.last_name || ''}</td>
                                <td>09/16/2026</td>
                                <td>${u.department || 'Admin'}</td>
                                <td><code>${u.employee_id || u.kiosk_code}</code></td>
                                <td class="text-end">
                                    <button class="btn btn-sm btn-outline-custom text-danger py-1 px-2" onclick="removeMemberFromGroup(${idx})">
                                        <i class="bi bi-trash"></i> Remove
                                    </button>
                                </td>
                            </tr>`;
                    });
                }
                document.getElementById('detail-members-tbody').innerHTML = html;
            }

            function removeMemberFromGroup(index) {
                let members = getGroupMembersStore(activeGroupName) || [];
                members.splice(index, 1);
                setGroupMembersStore(activeGroupName, members);

                document.getElementById('detail-emp-count').innerText = members.length;
                renderDetailMembers(members);
                renderConnecteamProvisioningTable();
                showToast('Member removed from group.');
            }

            function filterDetailMembers(query) {
                const q = query.toLowerCase();
                const members = getGroupMembersStore(activeGroupName) || [];
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
                    creator: 'Jaypee Balonzo',
                    selected: '10 selected',
                    brand: brand,
                    dept: name.replace('HO - ', '')
                });
                setStoredGroups(groups);
                setGroupMembersStore(name, []);

                renderConnecteamProvisioningTable();
                showToast('Smart Group created as empty (0 members enrolled).');
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

                const existingMembers = getGroupMembersStore(activeGroupName) || [];
                setGroupMembersStore(newName, existingMembers);
                localStorage.removeItem('smart_group_members_' + activeGroupName);

                activeGroupName = newName;
                document.getElementById('detail-group-title').innerText = newName;
                renderConnecteamProvisioningTable();
                showToast('Group renamed successfully.');
                if (currentBsModal) currentBsModal.hide();
            }

            async function openEnrollMembersModal() {
                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch('/api/auth/users', { headers: { 'Authorization': 'Bearer ' + token } });
                    if (res.ok) globalUsersList = await res.json();
                } catch(e) {}

                const list = globalUsersList.length > 0 ? globalUsersList : connecteamSampleUsers;
                let html = '';
                list.forEach(u => {
                    const empId = u.employee_id || u.kiosk_code;
                    html += `
                        <tr>
                            <td><input type="checkbox" class="form-check-input enroll-cb" value="${empId}"></td>
                            <td><strong>${u.first_name || u.name} ${u.last_name || ''}</strong></td>
                            <td><code>${empId}</code></td>
                            <td>${u.department || 'General'}</td>
                        </tr>`;
                });
                document.getElementById('enroll-modal-tbody').innerHTML = html;
                currentBsModal = new bootstrap.Modal(document.getElementById('enrollMembersModal'));
                currentBsModal.show();
            }

            function toggleSelectAllEnroll(source) {
                const cbs = document.querySelectorAll('.enroll-cb');
                cbs.forEach(cb => cb.checked = source.checked);
            }

            function confirmEnrollSelectedMembers() {
                const selectedIds = Array.from(document.querySelectorAll('.enroll-cb:checked')).map(cb => cb.value);
                if (selectedIds.length === 0) {
                    showToast('Please select at least one member.');
                    return;
                }

                const list = globalUsersList.length > 0 ? globalUsersList : connecteamSampleUsers;
                let members = getGroupMembersStore(activeGroupName) || [];
                let duplicates = [];
                let addedCount = 0;

                selectedIds.forEach(id => {
                    const found = list.find(u => (u.employee_id || u.kiosk_code) === id);
                    if (found) {
                        const isAlreadyMember = members.some(m => (m.employee_id || m.kiosk_code) === id);
                        if (isAlreadyMember) {
                            duplicates.push(`${found.first_name || found.name} ${found.last_name || ''} (${id})`);
                        } else {
                            members.push(found);
                            addedCount++;
                        }
                    }
                });

                setGroupMembersStore(activeGroupName, members);
                document.getElementById('detail-emp-count').innerText = members.length;
                renderDetailMembers(members);
                renderConnecteamProvisioningTable();

                if (duplicates.length > 0 && selectedIds.length === 1) {
                    showToast('member already in group');
                } else if (duplicates.length > 0) {
                    showToast(`Enrollment complete, members [${duplicates.join(', ')}] are already in the group`);
                } else {
                    showToast(`Successfully enrolled ${addedCount} members into ${activeGroupName}.`);
                }

                if (currentBsModal) currentBsModal.hide();
            }

            async function loadConnecteamDirectory() {
                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch('/api/auth/users', { headers: { 'Authorization': 'Bearer ' + token } });
                    if (res.ok) globalUsersList = await res.json();
                } catch(e) {}

                renderDirectoryRows(globalUsersList.length > 0 ? globalUsersList : connecteamSampleUsers);
            }

            function renderDirectoryRows(users) {
                let html = '';
                users.forEach((u, idx) => {
                    const initials = `${(u.first_name || u.name || 'U').charAt(0)}${(u.last_name || '').charAt(0)}`.toUpperCase();
                    const firstName = u.first_name || u.name;
                    const lastName = u.last_name || '';

                    html += `
                        <tr style="cursor: pointer;" onclick="openUserProfileDashboard('${firstName}', '${lastName}', '${u.role || 'Employee'}', '${u.department || 'General'}', '${u.email || ''}', '${u.mobile_phone || u.mobile || ''}', '${u.employee_id || u.kiosk_code || 'EMP00' + idx}')">
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
                            <td><code>${u.employee_id || u.kiosk_code || '3490'}</code></td>
                            <td><small class="text-muted">${u.date_added || '05/20/2025'}</small></td>
                            <td><small class="text-muted">${u.added_by || 'Admin'}</small></td>
                        </tr>`;
                });
                document.getElementById('directory-users-tbody').innerHTML = html;
            }

            function filterDirectoryRows(query) {
                const q = query.toLowerCase();
                const list = globalUsersList.length > 0 ? globalUsersList : connecteamSampleUsers;
                const filtered = list.filter(u => 
                    ((u.first_name || u.name) && (u.first_name || u.name).toLowerCase().includes(q)) || 
                    (u.last_name && u.last_name.toLowerCase().includes(q)) ||
                    ((u.employee_id || u.kiosk_code) && (u.employee_id || u.kiosk_code).toLowerCase().includes(q))
                );
                renderDirectoryRows(filtered);
            }

            function filterUserCategory(cat) {
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

            function openUserProfileDashboard(first, last, role, dept, email, mobile, empId) {
                document.getElementById('users-directory-list-view').style.display = 'none';
                document.getElementById('user-profile-dashboard-view').style.display = 'block';

                const initials = `${first.charAt(0)}${last.charAt(0)}`.toUpperCase();
                document.getElementById('profile-dashboard-avatar').innerText = initials;
                document.getElementById('profile-dashboard-name').childNodes[0].nodeValue = `${first} ${last} `;
                document.getElementById('profile-dashboard-role').innerText = role;

                document.getElementById('profile-detail-firstname').innerText = first;
                document.getElementById('profile-detail-lastname').innerText = last || '-';
                document.getElementById('profile-detail-mobile').innerText = mobile || '+63 912 794 6060';
                document.getElementById('profile-detail-email').innerText = email || `${first.toLowerCase()}@connecteam.com`;
                document.getElementById('profile-detail-empid').innerText = empId;
                document.getElementById('profile-detail-dept').innerText = dept;

                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function closeUserProfileDashboard() {
                document.getElementById('user-profile-dashboard-view').style.display = 'none';
                document.getElementById('users-directory-list-view').style.display = 'block';
            }

            document.addEventListener("DOMContentLoaded", function() {
                renderBrandSelectorOptions();
                renderConnecteamProvisioningTable();
            });
        </script>
    </body>
    </html>
    """
