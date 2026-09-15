from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .database import engine, Base, SessionLocal
from .models import JobCategory, JobSubItem, Employee, PunchLog
from .routers import auth, punch, jobs

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
                email="itsupport.associate@bigtimeempire.com"
            )
            db.add(test_user)
            db.commit()

        if db.query(JobCategory).count() == 0:
            default_cat = JobCategory(name="HO IT", code="HO-IT", description="Head Office IT Department")
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
def render_admin_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bigtime Empire - Operations & DTR Management</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            :root {
                --ct-sidebar-bg: #ffffff;
                --ct-primary: #2563eb;
                --ct-border: #e2e8f0;
                --ct-text-dark: #0f172a;
                --ct-text-muted: #64748b;
            }
            body { background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: var(--ct-text-dark); }
            
            .top-navbar { background-color: #ffffff; border-bottom: 1px solid var(--ct-border); height: 60px; padding: 0 24px; position: sticky; top: 0; z-index: 1000; }
            .search-input { background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 20px; padding: 6px 16px 6px 36px; font-size: 13px; width: 280px; }
            .search-wrapper { position: relative; }
            .search-wrapper i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--ct-text-muted); font-size: 14px; }

            .app-sidebar { width: 240px; background-color: #ffffff; border-right: 1px solid var(--ct-border); min-height: calc(100vh - 60px); padding: 16px 12px; }
            .nav-section-title { font-size: 11px; font-weight: 700; color: var(--ct-text-muted); text-transform: uppercase; letter-spacing: 0.5px; padding: 12px 12px 4px 12px; }
            .ct-nav-link { display: flex; align-items: center; gap: 10px; padding: 8px 12px; color: #334155; border-radius: 8px; font-size: 13px; font-weight: 500; text-decoration: none; margin-bottom: 2px; }
            .ct-nav-link:hover { background-color: #f1f5f9; color: var(--ct-primary); }
            .ct-nav-link.active { background-color: #eff6ff; color: var(--ct-primary); font-weight: 600; }
            .ct-nav-link i { font-size: 16px; width: 20px; text-align: center; }

            .main-workspace { flex: 1; padding: 24px; overflow-y: auto; }
            .page-title { font-size: 20px; font-weight: 700; color: var(--ct-text-dark); margin-bottom: 0; }
            .ct-card { background-color: #ffffff; border: 1px solid var(--ct-border); border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); margin-bottom: 20px; }

            .table-ct { margin-bottom: 0; }
            .table-ct th { background-color: #f8fafc; color: var(--ct-text-muted); font-size: 12px; font-weight: 600; text-transform: uppercase; padding: 12px 16px; border-bottom: 1px solid var(--ct-border); }
            .table-ct td { padding: 12px 16px; font-size: 13px; color: #334155; vertical-align: middle; border-bottom: 1px solid #f1f5f9; }
            .table-ct tbody tr:hover { background-color: #f8fafc; cursor: pointer; }

            .ts-pill { background-color: #10b981; color: #ffffff; font-weight: 600; font-size: 11px; padding: 4px 8px; border-radius: 6px; text-align: center; display: inline-block; width: 60px; }
            .ts-pill-off { color: #94a3b8; font-weight: 600; font-size: 12px; }
            
            .offcanvas-ct { width: 440px !important; border-left: 1px solid var(--ct-border); }
            .jobtitle-pill { background-color: #eff6ff; color: var(--ct-primary); border: 1px solid #bfdbfe; font-size: 12px; padding: 2px 10px; border-radius: 12px; font-weight: 600; text-decoration: none; }
            
            #map-container { height: 360px; width: 100%; border-radius: 8px; border: 1px solid var(--ct-border); }

            /* User Detail Panel Layout */
            .profile-left-panel { width: 320px; border-right: 1px solid var(--ct-border); padding-right: 20px; }
            .profile-right-panel { flex: 1; padding-left: 20px; }
            .form-label-sm { font-size: 11px; font-weight: 700; color: var(--ct-text-muted); margin-bottom: 4px; }
            .form-control-sm-ct { font-size: 13px; border-radius: 6px; border: 1px solid #cbd5e1; }
            
            .activity-timeline-item { position: relative; padding-left: 28px; padding-bottom: 16px; border-left: 2px solid #e2e8f0; margin-left: 10px; }
            .activity-timeline-dot { position: absolute; left: -7px; top: 0; width: 12px; height: 12px; border-radius: 6px; background-color: var(--ct-primary); }
        </style>
    </head>
    <body>
        <div class="top-navbar d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center gap-3">
                <span class="fw-bold fs-5 text-primary"><i class="bi bi-box-fill me-2"></i>BIGTIME EMPIRE</span>
                <div class="search-wrapper">
                    <i class="bi bi-search"></i>
                    <input type="text" id="globalSearchInput" class="search-input" placeholder="Search anything..." onkeyup="filterLogs()">
                </div>
            </div>
            <div class="d-flex align-items-center gap-3">
                <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-3 py-2 rounded-pill"><i class="bi bi-person-check-fill me-1"></i> Admin Workspace</span>
                
                <div class="dropdown">
                    <button class="btn btn-link p-0 text-decoration-none d-flex align-items-center gap-2" type="button" data-bs-toggle="dropdown">
                        <div class="bg-primary text-white rounded-circle fw-bold d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;">JB</div>
                        <div class="text-start">
                            <div class="fw-bold text-dark d-flex align-items-center" style="font-size: 13px;">Jaypee Balonzo <i class="bi bi-chevron-down ms-1 text-muted" style="font-size: 10px;"></i></div>
                            <div class="text-muted" style="font-size: 11px;">Owner / IT Administrator</div>
                        </div>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-sm border-light" style="width: 220px; border-radius: 12px;">
                        <li class="px-3 py-2 bg-light rounded-top">
                            <div class="fw-bold small">Jaypee Balonzo</div>
                            <div class="text-muted extra-small" style="font-size: 11px;">Owner</div>
                        </li>
                        <li><hr class="dropdown-divider my-1"></li>
                        <li><a class="dropdown-item small" href="#"><i class="bi bi-person me-2"></i>Switch to user's view</a></li>
                        <li><a class="dropdown-item small" href="#"><i class="bi bi-gear me-2"></i>Settings</a></li>
                        <li><a class="dropdown-item small" href="#"><i class="bi bi-bell me-2"></i>Notifications</a></li>
                        <li><a class="dropdown-item small text-danger" href="#" onclick="alert('Logging out of Admin Session...'); window.location.href='/admin';"><i class="bi bi-box-arrow-right me-2"></i>Sign out</a></li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="d-flex">
            <div class="app-sidebar">
                <a href="#" class="ct-nav-link" onclick="switchTab('overview')"><i class="bi bi-grid-1x2"></i> Overview</a>
                <a href="#" class="ct-nav-link" onclick="switchTab('activity')"><i class="bi bi-activity"></i> Activity</a>
                <a href="#" class="ct-nav-link" id="nav-users" onclick="switchTab('users')"><i class="bi bi-people"></i> Users</a>
                <a href="#" class="ct-nav-link" onclick="switchTab('groups')"><i class="bi bi-diagram-3"></i> Smart groups</a>
                <a href="#" class="ct-nav-link active" id="nav-jobs" onclick="switchTab('jobs')"><i class="bi bi-briefcase"></i> Job list</a>

                <div class="nav-section-title">Operations</div>
                <a href="#" class="ct-nav-link" id="nav-dtr" onclick="switchTab('dtr')"><i class="bi bi-clock-history text-primary"></i> Time Clock <span class="badge bg-danger rounded-pill ms-auto">LIVE</span></a>
                <a href="#" class="ct-nav-link" onclick="switchTab('scheduling')"><i class="bi bi-calendar-event"></i> Job Scheduling</a>
                <a href="#" class="ct-nav-link" onclick="switchTab('timeoff')"><i class="bi bi-calendar2-minus"></i> Time Off</a>
                <a href="#" class="ct-nav-link" onclick="switchTab('tasks')"><i class="bi bi-check2-square"></i> Quick Tasks</a>
            </div>

            <div class="main-workspace">
                
                <!-- 1. USERS DIRECTORY VIEW -->
                <div id="tab-users" style="display: none;">
                    <div id="users-list-view">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <div>
                                <h4 class="page-title"><i class="bi bi-people me-2"></i>Users</h4>
                                <p class="text-muted small mb-0">Directory of registered employees, kiosk access codes, and department assignments</p>
                            </div>
                            <button class="btn btn-primary rounded-pill px-4" onclick="alert('User Creation Drawer')">
                                <i class="bi bi-plus-lg me-1"></i> Add users
                            </button>
                        </div>

                        <div class="ct-card">
                            <div class="table-responsive">
                                <table class="table table-ct">
                                    <thead>
                                        <tr>
                                            <th style="width: 40px;"><input type="checkbox" class="form-check-input"></th>
                                            <th>Full Name</th>
                                            <th>Employee ID</th>
                                            <th>Position</th>
                                            <th>Department</th>
                                            <th>Kiosk Code</th>
                                            <th>Last Login</th>
                                            <th>Date Added</th>
                                        </tr>
                                    </thead>
                                    <tbody id="usersTableBody">
                                        <tr><td colspan="8" class="text-center py-4 text-muted">Loading employee directory...</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- Connecteam User Profile Editor View (image_525de1.png) -->
                    <div id="user-profile-editor-view" style="display: none;">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div class="d-flex align-items-center gap-2">
                                <button class="btn btn-sm btn-light border rounded-circle" onclick="hideUserProfile()"><i class="bi bi-arrow-left"></i></button>
                                <div class="bg-danger text-white rounded-circle fw-bold d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;" id="profileAvatar">JB</div>
                                <h4 class="fw-bold mb-0" id="profileHeaderName">Jaypee Balonzo</h4>
                                <span class="badge bg-light text-dark border" id="profileHeaderDept">Admin</span>
                            </div>
                            <div class="d-flex gap-2">
                                <button class="btn btn-outline-secondary btn-sm rounded-pill"><i class="bi bi-gift me-1"></i> Send reward</button>
                                <button class="btn btn-outline-secondary btn-sm rounded-pill">Options <i class="bi bi-chevron-down ms-1"></i></button>
                                <button class="btn btn-outline-primary btn-sm rounded-pill"><i class="bi bi-chat-text me-1"></i> Text Message</button>
                            </div>
                        </div>

                        <div class="ct-card p-4">
                            <div class="d-flex">
                                <!-- Left Panel: Editable Personal Details -->
                                <div class="profile-left-panel">
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <h6 class="fw-bold mb-0">Personal Details</h6>
                                        <button class="btn btn-sm btn-primary py-0" onclick="saveUserProfile()"><i class="bi bi-check-lg"></i> Save Changes</button>
                                    </div>
                                    
                                    <div class="mb-2">
                                        <label class="form-label-sm">First name *</label>
                                        <input type="text" id="editFirstName" class="form-control form-control-sm form-control-sm-ct">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Last name *</label>
                                        <input type="text" id="editLastName" class="form-control form-control-sm form-control-sm-ct">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Mobile phone *</label>
                                        <input type="text" id="editMobilePhone" class="form-control form-control-sm form-control-sm-ct">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Email *</label>
                                        <input type="email" id="editEmail" class="form-control form-control-sm form-control-sm-ct">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Employee ID *</label>
                                        <input type="text" id="editEmployeeId" class="form-control form-control-sm form-control-sm-ct" readonly>
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Birthday</label>
                                        <input type="date" id="editBirthday" class="form-control form-control-sm form-control-sm-ct">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Gender</label>
                                        <select id="editGender" class="form-select form-select-sm form-control-sm-ct">
                                            <option value="Male">Male</option>
                                            <option value="Female">Female</option>
                                        </select>
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Civil Status</label>
                                        <input type="text" id="editCivilStatus" class="form-control form-control-sm form-control-sm-ct">
                                    </div>
                                    <div class="mb-2">
                                        <label class="form-label-sm">Agency</label>
                                        <input type="text" id="editAgency" class="form-control form-control-sm form-control-sm-ct">
                                    </div>
                                </div>

                                <!-- Right Panel: Navigation Tabs & Activity Timeline -->
                                <div class="profile-right-panel">
                                    <ul class="nav nav-tabs mb-3">
                                        <li class="nav-item"><a class="nav-link" href="#">Employment</a></li>
                                        <li class="nav-item"><a class="nav-link active" href="#">Activity</a></li>
                                        <li class="nav-item"><a class="nav-link" href="#">Time off</a></li>
                                        <li class="nav-item"><a class="nav-link" href="#">Notes</a></li>
                                        <li class="nav-item"><a class="nav-link" href="#">Forms</a></li>
                                        <li class="nav-item"><a class="nav-link" href="#">Documents</a></li>
                                    </ul>

                                    <div class="activity-timeline mt-4">
                                        <h6 class="fw-bold mb-3">Recent Activity Logs</h6>
                                        <div class="activity-timeline-item">
                                            <div class="activity-timeline-dot"></div>
                                            <div class="fw-bold small" id="activityUserName">Jaypee Balonzo</div>
                                            <div class="text-muted extra-small" style="font-size:12px;">Clocked in today via Mobile DTR</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 2. JOB LIST MODULE -->
                <div id="tab-jobs">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <h4 class="page-title"><i class="bi bi-briefcase me-2"></i>Job list</h4>
                            <p class="text-muted small mb-0">Manage duty categories, departments, and active Job Titles</p>
                        </div>
                        <button class="btn btn-primary rounded-pill px-4" data-bs-toggle="offcanvas" data-bs-target="#addJobDrawer">
                            <i class="bi bi-plus-lg me-1"></i> Add new Job
                        </button>
                    </div>

                    <div class="ct-card">
                        <div class="table-responsive">
                            <table class="table table-ct">
                                <thead>
                                    <tr>
                                        <th style="width: 40px;"><input type="checkbox" class="form-check-input"></th>
                                        <th>Item Name</th>
                                        <th>Code</th>
                                        <th>Job Titles</th>
                                        <th>Qualified Department</th>
                                        <th>Address / Geofence</th>
                                        <th class="text-end">Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="jobTableBody">
                                    <tr><td colspan="7" class="text-center py-4 text-muted">Loading active job list...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- 3. TIME CLOCK & TIMESHEETS MODULE -->
                <div id="tab-dtr" style="display: none;">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h4 class="page-title"><i class="bi bi-clock me-2"></i>Time Clock & Timesheets</h4>
                            <p class="text-muted small mb-0">Real-time attendance tracking, matrix timesheets, and GPS location pins</p>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-outline-secondary rounded-pill" onclick="loadDTRLogs()"><i class="bi bi-arrow-clockwise me-1"></i> Refresh</button>
                            <button class="btn btn-success rounded-pill px-4" onclick="window.open('/api/punch/export', '_blank')"><i class="bi bi-file-earmark-excel me-1"></i> Export Timesheet (CSV)</button>
                        </div>
                    </div>

                    <div class="ct-card p-3 mb-3">
                        <div class="row g-2 align-items-center">
                            <div class="col-md-4">
                                <div class="input-group input-group-sm">
                                    <span class="input-group-text bg-light"><i class="bi bi-search"></i></span>
                                    <input type="text" id="employeeSearchInput" class="form-control" placeholder="Search by name or Employee ID..." onkeyup="filterLogs()">
                                </div>
                            </div>
                            <div class="col-md-3">
                                <select id="deptFilter" class="form-select form-select-sm" onchange="filterLogs()">
                                    <option value="ALL">All Departments</option>
                                    <option value="Admin">Admin</option>
                                    <option value="HO IT">Head Office IT</option>
                                    <option value="Operations">Operations</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <select id="viewTypeFilter" class="form-select form-select-sm" onchange="toggleViewType()">
                                    <option value="LOGS">View Mode: Live Punch Logs</option>
                                    <option value="TIMESHEET">View Mode: Weekly Matrix Timesheet</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div id="view-logs" class="row g-3 mb-4">
                        <div class="col-md-7">
                            <div class="ct-card p-0">
                                <div class="table-responsive">
                                    <table class="table table-ct">
                                        <thead>
                                            <tr>
                                                <th>Timestamp</th>
                                                <th>Employee ID</th>
                                                <th>Punch Type</th>
                                                <th>Job Title / Note</th>
                                                <th>GPS Pin</th>
                                                <th>Accuracy</th>
                                            </tr>
                                        </thead>
                                        <tbody id="dtrLogsBody">
                                            <tr><td colspan="6" class="text-center py-4 text-muted">Loading punch records...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-5">
                            <div class="ct-card p-3">
                                <h6 class="fw-bold mb-3"><i class="bi bi-geo-alt-fill text-danger me-1"></i> Live GPS Map Location</h6>
                                <div id="map-container"></div>
                                <div class="mt-2 text-muted small text-center fw-bold" id="mapLocationText">Click any log row to pinpoint GPS coordinates</div>
                            </div>
                        </div>
                    </div>

                    <div id="view-timesheet" class="ct-card p-3 mb-4" style="display: none;">
                        <h6 class="fw-bold mb-3"><i class="bi bi-calendar-week me-2"></i>Weekly Timesheet Matrix</h6>
                        <div class="table-responsive">
                            <table class="table table-ct text-center align-middle">
                                <thead>
                                    <tr>
                                        <th class="text-start">Full Name</th>
                                        <th>Mon 9/1</th>
                                        <th>Tue 9/2</th>
                                        <th>Wed 9/3</th>
                                        <th>Thu 9/4</th>
                                        <th>Fri 9/5</th>
                                        <th>Sat 9/6</th>
                                        <th>Sun 9/7</th>
                                        <th>Total Hours</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td class="text-start fw-bold">Jaypee Balonzo <br><small class="text-muted">ID: 3286</small></td>
                                        <td><span class="ts-pill">16:00</span></td>
                                        <td><span class="ts-pill">16:00</span></td>
                                        <td><span class="ts-pill">11:30</span></td>
                                        <td><span class="ts-pill">16:00</span></td>
                                        <td><span class="ts-pill">16:00</span></td>
                                        <td><span class="ts-pill-off">--</span></td>
                                        <td><span class="ts-pill-off">--</span></td>
                                        <td class="fw-bold text-primary">75:30 hrs</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                </div>

            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let map, marker;
            let rawLogs = [];
            let cachedUsers = [];

            document.addEventListener("DOMContentLoaded", () => {
                loadJobList();
                initMap();
            });

            function switchTab(tab) {
                document.getElementById('tab-jobs').style.display = tab === 'jobs' ? 'block' : 'none';
                document.getElementById('tab-dtr').style.display = tab === 'dtr' ? 'block' : 'none';
                document.getElementById('tab-users').style.display = tab === 'users' ? 'block' : 'none';

                document.querySelectorAll('.ct-nav-link').forEach(el => el.classList.remove('active'));
                if(document.getElementById('nav-' + tab)) document.getElementById('nav-' + tab).classList.add('active');

                if (tab === 'jobs') loadJobList();
                if (tab === 'users') { hideUserProfile(); loadUsersList(); }
                if (tab === 'dtr') {
                    loadDTRLogs();
                    setTimeout(() => { if (map) map.invalidateSize(); }, 200);
                }
            }

            async function loadUsersList() {
                try {
                    const res = await fetch('/api/auth/users');
                    cachedUsers = await res.json();
                    const tbody = document.getElementById('usersTableBody');
                    tbody.innerHTML = '';

                    cachedUsers.forEach(u => {
                        const initial = u.name ? u.name.charAt(0) : 'U';
                        tbody.innerHTML += `
                            <tr onclick="showUserProfile('${u.employee_id}')">
                                <td><input type="checkbox" class="form-check-input" onclick="event.stopPropagation()"></td>
                                <td>
                                    <div class="d-flex align-items-center gap-2">
                                        <div class="bg-primary text-white rounded-circle fw-bold d-flex align-items-center justify-content-center" style="width: 28px; height: 28px; font-size: 11px;">${initial}</div>
                                        <span class="fw-bold text-primary">${u.name}</span>
                                    </div>
                                </td>
                                <td><strong>${u.employee_id}</strong></td>
                                <td>${u.position}</td>
                                <td><span class="badge bg-secondary-subtle text-secondary px-2 py-1">${u.department}</span></td>
                                <td><code>${u.kiosk_code}</code></td>
                                <td>${u.last_login}</td>
                                <td>${u.date_added}</td>
                            </tr>
                        `;
                    });
                } catch (e) {
                    console.log('Error loading users:', e);
                }
            }

            function showUserProfile(empId) {
                const user = cachedUsers.find(u => u.employee_id === empId);
                if (!user) return;

                document.getElementById('editFirstName').value = user.first_name || '';
                document.getElementById('editLastName').value = user.last_name || '';
                document.getElementById('editMobilePhone').value = user.mobile_phone || '';
                document.getElementById('editEmail').value = user.email || '';
                document.getElementById('editEmployeeId').value = user.employee_id;
                document.getElementById('editBirthday').value = user.birthday || '';
                document.getElementById('editGender').value = user.gender || 'Male';
                document.getElementById('editCivilStatus').value = user.civil_status || 'Single';
                document.getElementById('editAgency').value = user.agency || 'Direct Hire';

                document.getElementById('profileHeaderName').innerText = user.name;
                document.getElementById('profileHeaderDept').innerText = user.department;
                document.getElementById('profileAvatar').innerText = user.name.charAt(0);
                document.getElementById('activityUserName').innerText = user.name;

                document.getElementById('users-list-view').style.display = 'none';
                document.getElementById('user-profile-editor-view').style.display = 'block';
            }

            function hideUserProfile() {
                document.getElementById('users-list-view').style.display = 'block';
                document.getElementById('user-profile-editor-view').style.display = 'none';
            }

            async function saveUserProfile() {
                const empId = document.getElementById('editEmployeeId').value;
                const payload = {
                    first_name: document.getElementById('editFirstName').value,
                    last_name: document.getElementById('editLastName').value,
                    mobile_phone: document.getElementById('editMobilePhone').value,
                    email: document.getElementById('editEmail').value,
                    birthday: document.getElementById('editBirthday').value,
                    gender: document.getElementById('editGender').value,
                    civil_status: document.getElementById('editCivilStatus').value,
                    agency: document.getElementById('editAgency').value
                };

                const res = await fetch('/api/auth/users/' + empId, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    alert('User profile updated successfully!');
                    loadUsersList();
                } else {
                    alert('Failed to update user profile.');
                }
            }

            function initMap() {
                map = L.map('map-container', { zoomControl: true }).setView([14.5764, 121.0851], 15);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
                marker = L.marker([14.5764, 121.0851]).addTo(map);
            }

            function updateMapPin(lat, lng, label) {
                if(lat && lng) {
                    map.setView([lat, lng], 16);
                    marker.setLatLng([lat, lng]);
                    setTimeout(() => map.invalidateSize(), 100);
                    document.getElementById('mapLocationText').innerText = `GPS Pin: ${lat.toFixed(5)}, ${lng.toFixed(5)} (${label})`;
                }
            }

            async function loadJobList() {
                const res = await fetch('/api/jobs');
                const data = await res.json();
                const tbody = document.getElementById('jobTableBody');
                tbody.innerHTML = '';

                data.forEach(job => {
                    const titlesCount = job.sub_items ? job.sub_items.length : 0;
                    const titlesListText = titlesCount > 0 ? `<span class="jobtitle-pill"><i class="bi bi-arrow-return-right me-1"></i>${titlesCount} Job Titles</span>` : '<span class="text-muted small">No Job Title</span>';
                    
                    tbody.innerHTML += `
                        <tr>
                            <td><input type="checkbox" class="form-check-input"></td>
                            <td><div class="fw-bold"><i class="bi bi-circle-fill text-primary me-2" style="font-size:10px;"></i>${job.name}</div></td>
                            <td><span class="badge bg-light text-dark border">${job.code || 'N/A'}</span></td>
                            <td>${titlesListText}</td>
                            <td><span class="badge bg-secondary-subtle text-secondary px-2 py-1">${job.description || 'Head Office'}</span></td>
                            <td><span class="text-muted small">Head Office Geofence</span></td>
                            <td class="text-end">
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteJob(${job.id})"><i class="bi bi-trash"></i></button>
                            </td>
                        </tr>
                    `;
                });
            }

            async function loadDTRLogs() {
                try {
                    const res = await fetch('/api/punch/logs');
                    rawLogs = await res.json();
                    renderLogsTable(rawLogs);
                } catch (e) {
                    console.log('Error loading logs:', e);
                }
            }

            function renderLogsTable(logs) {
                const tbody = document.getElementById('dtrLogsBody');
                tbody.innerHTML = '';

                if (logs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No matching punch records found.</td></tr>';
                    return;
                }

                logs.forEach((log, index) => {
                    const badgeClass = log.punch_type === 'CLOCK_IN' ? 'bg-success' : 'bg-danger';
                    const lat = log.latitude || 14.5764;
                    const lng = log.longitude || 121.0851;
                    
                    tbody.innerHTML += `
                        <tr onclick="updateMapPin(${lat}, ${lng}, '${log.address}')">
                            <td>${log.timestamp}</td>
                            <td><strong>${log.employee_id}</strong></td>
                            <td><span class="badge ${badgeClass}">${log.punch_type}</span></td>
                            <td>${log.address}</td>
                            <td><span class="text-primary text-decoration-underline">${lat.toFixed(4)}, ${lng.toFixed(4)}</span></td>
                            <td>${log.accuracy}m</td>
                        </tr>
                    `;

                    if (index === 0) {
                        updateMapPin(lat, lng, log.address);
                    }
                });
            }

            function filterLogs() {
                const query = (document.getElementById('employeeSearchInput').value || document.getElementById('globalSearchInput').value || '').toLowerCase();
                const filtered = rawLogs.filter(log => {
                    return log.employee_id.toLowerCase().includes(query) || log.address.toLowerCase().includes(query);
                });
                renderLogsTable(filtered);
            }
        </script>
    </body>
    </html>
    """
