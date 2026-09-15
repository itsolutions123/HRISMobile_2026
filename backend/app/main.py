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
def get_admin_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HRIS Connecteam Admin Portal</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { background-color: #f8fafc; font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #1e293b; }
            .sidebar { min-height: 100vh; background: #0f172a; color: #94a3b8; }
            .sidebar .nav-link { color: #94a3b8; padding: 10px 16px; border-radius: 8px; margin-bottom: 4px; font-weight: 500; display: flex; align-items: center; gap: 10px; cursor: pointer; transition: all 0.2s; }
            .sidebar .nav-link:hover, .sidebar .nav-link.active { background: #1e293b; color: #38bdf8; }
            .sidebar .section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin: 16px 16px 8px; }
            .top-bar { background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 14px 28px; }
            .card-custom { background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
            #map { height: 500px; width: 100%; border-radius: 10px; border: 1px solid #cbd5e1; }
            .profile-dropdown .dropdown-toggle::after { display: none; }
            .avatar-circle { width: 38px; height: 38px; background-color: #0284c7; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; }
            .modal-content { border-radius: 16px; border: none; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
            .modal-header { border-bottom: 1px solid #f1f5f9; padding: 20px 24px; }
            .modal-footer { border-top: 1px solid #f1f5f9; padding: 16px 24px; }
            .pending-badge { background-color: #ffe4e6; color: #e11d48; border-radius: 20px; font-size: 11px; font-weight: 700; padding: 2px 8px; }
        </style>
    </head>
    <body>
        <div class="container-fluid p-0">
            <div class="row g-0">
                <div class="col-md-2 sidebar p-3">
                    <div class="d-flex align-items-center gap-2 mb-4 px-2">
                        <i class="bi bi-shield-lock-fill text-primary fs-3"></i>
                        <span class="fs-5 fw-bold text-white">HRIS Admin</span>
                    </div>

                    <div class="section-label">Main</div>
                    <a class="nav-link active" id="nav-clock" onclick="switchTab('clock')"><i class="bi bi-clock-history"></i> Time Clock</a>
                    <a class="nav-link" id="nav-jobs" onclick="switchTab('jobs')"><i class="bi bi-briefcase"></i> Job List</a>
                    <a class="nav-link d-flex justify-content-between align-items-center" id="nav-users" onclick="switchTab('users')">
                        <span><i class="bi bi-people me-2"></i> Users & Directory</span>
                        <span class="pending-badge" id="sidebar-pending-count" style="display:none;">0</span>
                    </a>

                    <div class="section-label">Management</div>
                    <a class="nav-link" onclick="alert('Feature accessible via mobile App screen.')"><i class="bi bi-calendar-event"></i> Scheduling</a>
                    <a class="nav-link" onclick="window.open('/api/dtr/export', '_blank')"><i class="bi bi-file-earmark-excel"></i> Export DTR</a>
                </div>

                <div class="col-md-10">
                    <div class="top-bar d-flex justify-content-between align-items-center">
                        <h5 class="m-0 fw-bold text-dark" id="page-title">Time Clock Operations</h5>

                        <div class="dropdown profile-dropdown">
                            <button class="btn border-0 d-flex align-items-center gap-2 dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                <div class="avatar-circle">JB</div>
                                <div class="text-start d-none d-sm-block">
                                    <div class="fw-bold fs-6 text-dark lh-1">Jaypee Balonzo</div>
                                    <small class="text-muted fs-7">Owner / System Admin (3286)</small>
                                </div>
                                <i class="bi bi-chevron-down text-muted ms-1"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow border-0 mt-2">
                                <li><a class="dropdown-item py-2" onclick="alert('System Admin ID: 3286\\nRole: Admin\\nStatus: Active')"><i class="bi bi-person me-2"></i> Profile & Roles</a></li>
                                <li><a class="dropdown-item py-2" onclick="alert('Settings configured via environment.')"><i class="bi bi-gear me-2"></i> Settings</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item py-2 text-danger" onclick="location.reload()"><i class="bi bi-box-arrow-right me-2"></i> Sign out</a></li>
                            </ul>
                        </div>
                    </div>

                    <div class="p-4">
                        <div id="tab-clock" class="card-custom">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="fw-bold m-0"><i class="bi bi-geo-alt text-primary me-2"></i> Live Clock In / Out Map</h5>
                                <button class="btn btn-sm btn-outline-primary rounded-2" onclick="loadPunchMap()"><i class="bi bi-arrow-clockwise me-1"></i> Refresh Map</button>
                            </div>
                            <div class="row">
                                <div class="col-md-4">
                                    <div class="card border-0 bg-light p-3 mb-3 rounded-3">
                                        <h6 class="fw-bold text-secondary">Active Clocked In Today</h6>
                                        <h2 id="active-punch-count" class="text-primary fw-bold">0</h2>
                                    </div>
                                    <div id="punch-list-sidebar" style="max-height: 400px; overflow-y: auto;">
                                        <p class="text-muted fs-7">Loading recent punches...</p>
                                    </div>
                                </div>
                                <div class="col-md-8">
                                    <div id="map"></div>
                                </div>
                            </div>
                        </div>

                        <div id="tab-jobs" class="card-custom" style="display:none;">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="fw-bold m-0"><i class="bi bi-briefcase text-primary me-2"></i> Job Categories & Sub-items</h5>
                                <div>
                                    <button class="btn btn-sm btn-outline-danger me-2 rounded-2" onclick="bulkDeleteJobs()"><i class="bi bi-trash me-1"></i> Bulk Delete</button>
                                    <button class="btn btn-sm btn-primary rounded-2" onclick="openAddJobModal()"><i class="bi bi-plus-lg me-1"></i> Add Category</button>
                                </div>
                            </div>
                            <div class="table-responsive">
                                <table class="table table-hover align-middle">
                                    <thead class="table-light">
                                        <tr>
                                            <th width="40"><input type="checkbox" id="select-all-jobs" onclick="toggleSelectAllJobs(this)"></th>
                                            <th>Category Name</th>
                                            <th>Code</th>
                                            <th>Duties / Sub-items</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="jobs-table-body">
                                        <tr><td colspan="5" class="text-center text-muted">Loading job categories...</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div id="tab-users" class="card-custom" style="display:none;">
                            <!-- JOIN REQUEST NOTIFICATION CARD -->
                            <div id="join-requests-card" class="card border-primary mb-4 shadow-sm" style="display:none;">
                                <div class="card-header bg-primary text-white fw-bold d-flex justify-content-between align-items-center">
                                    <span><i class="bi bi-bell-fill me-2"></i> Pending Join Requests</span>
                                    <span class="badge bg-light text-primary fw-bold" id="pending-requests-count">0</span>
                                </div>
                                <div class="card-body p-0">
                                    <div class="table-responsive">
                                        <table class="table table-hover align-middle m-0">
                                            <thead class="table-light">
                                                <tr>
                                                    <th>Applicant Name</th>
                                                    <th>Email</th>
                                                    <th>Department</th>
                                                    <th>Mobile Phone</th>
                                                    <th>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody id="pending-users-table-body">
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="fw-bold m-0"><i class="bi bi-people text-primary me-2"></i> Active Employee Directory</h5>
                            </div>
                            <div class="table-responsive">
                                <table class="table table-hover align-middle">
                                    <thead class="table-light">
                                        <tr>
                                            <th>Employee ID</th>
                                            <th>Full Name</th>
                                            <th>Role</th>
                                            <th>Department</th>
                                            <th>Status</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="users-table-body">
                                        <tr><td colspan="6" class="text-center text-muted">Loading employees...</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </div>

        <div class="modal fade" id="jobModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title fw-bold" id="jobModalTitle">Add Job Category</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="mb-3">
                            <label class="form-label fw-bold fs-7 text-secondary">Category Name</label>
                            <input type="text" class="form-control" id="modalJobName" placeholder="e.g. HO IT">
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold fs-7 text-secondary">Code</label>
                            <input type="text" class="form-control" id="modalJobCode" placeholder="e.g. HO-IT">
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold fs-7 text-secondary">Duties / Roles (Comma-separated)</label>
                            <textarea class="form-control" id="modalJobSubItems" rows="3" placeholder="e.g. IT Assistant, System Administrator, Technical Support"></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-light rounded-2" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary rounded-2 px-4" onclick="saveJobFromModal()">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let map, markersGroup;
            let currentBsModal;
            let adminToken = '';

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
                } catch(e) { console.error('Auth login error:', e); }
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
                    document.getElementById('page-title').innerText = 'Time Clock Operations';
                    setTimeout(() => { if (map) map.invalidateSize(); }, 200);
                    loadPunchMap();
                } else if (tab === 'jobs') {
                    document.getElementById('page-title').innerText = 'Job List & Categories';
                    loadJobsTable();
                } else if (tab === 'users') {
                    document.getElementById('page-title').innerText = 'Users & Directory';
                    loadUsersTable();
                }
            }

            function initMap() {
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
                    markersGroup.clearLayers();

                    let activeCount = 0;
                    let sidebarHtml = '';

                    logs.forEach(log => {
                        if (log.punch_type === 'CLOCK_IN') activeCount++;
                        sidebarHtml += `
                            <div class="card p-2 mb-2 border-0 bg-white shadow-sm rounded-3">
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="fw-bold fs-7">Emp ID: ${log.employee_id}</span>
                                    <span class="badge ${log.punch_type === 'CLOCK_IN' ? 'bg-success' : 'bg-secondary'} fs-8">${log.punch_type}</span>
                                </div>
                                <small class="text-muted mt-1">${log.timestamp}</small>
                                <small class="text-truncate text-secondary">${log.address || 'Duty Shift'}</small>
                            </div>`;

                        if (log.latitude && log.longitude) {
                            L.marker([log.latitude, log.longitude])
                                .bindPopup(`<b>Employee: ${log.employee_id}</b><br>Type: ${log.punch_type}<br>Time: ${log.timestamp}`)
                                .addTo(markersGroup);
                        }
                    });

                    document.getElementById('active-punch-count').innerText = activeCount;
                    document.getElementById('punch-list-sidebar').innerHTML = sidebarHtml || '<p class="text-muted fs-7">No punch records found.</p>';
                } catch(e) {
                    console.log('Error loading map data:', e);
                }
            }

            async function loadJobsTable() {
                try {
                    const res = await fetch('/api/jobs');
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    const jobs = await res.json();
                    let html = '';
                    jobs.forEach(j => {
                        const subs = Array.isArray(j.sub_items) ? j.sub_items : [];
                        let subsHtml = subs.length > 0
                            ? subs.map(s => `<span class="badge bg-light text-dark border me-1 mb-1">${s.name || s}</span>`).join('')
                            : '<span class="text-muted fs-8">No sub-items</span>';

                        const encodedJob = encodeURIComponent(JSON.stringify(j));

                        html += `
                            <tr>
                                <td><input type="checkbox" class="job-checkbox" value="${j.id}"></td>
                                <td><strong>${j.name || ''}</strong></td>
                                <td><code>${j.code || '-'}</code></td>
                                <td>${subsHtml}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary me-1 rounded-2" onclick="openEditJobModal('${encodedJob}')"><i class="bi bi-pencil"></i></button>
                                    <button class="btn btn-sm btn-outline-danger rounded-2" onclick="deleteSingleJob(${j.id})"><i class="bi bi-trash"></i></button>
                                </td>
                            </tr>`;
                    });
                    document.getElementById('jobs-table-body').innerHTML = html || '<tr><td colspan="5" class="text-center text-muted">No job categories defined.</td></tr>';
                } catch(e) {
                    console.error('Error in loadJobsTable:', e);
                    document.getElementById('jobs-table-body').innerHTML = '<tr><td colspan="5" class="text-center text-danger">Failed to load jobs. Check console for details.</td></tr>';
                }
            }

            function openAddJobModal() {
                document.getElementById('jobModalTitle').innerText = 'Add Job Category';
                document.getElementById('modalJobName').value = '';
                document.getElementById('modalJobCode').value = '';
                document.getElementById('modalJobSubItems').value = '';

                currentBsModal = new bootstrap.Modal(document.getElementById('jobModal'));
                currentBsModal.show();
            }

            function openEditJobModal(encodedJobStr) {
                const job = JSON.parse(decodeURIComponent(encodedJobStr));
                document.getElementById('jobModalTitle').innerText = 'Edit Job Category';
                document.getElementById('modalJobName').value = job.name || '';
                document.getElementById('modalJobCode').value = job.code || '';

                const currentSubNames = (job.sub_items || []).map(s => s.name || s).join(', ');
                document.getElementById('modalJobSubItems').value = currentSubNames;

                currentBsModal = new bootstrap.Modal(document.getElementById('jobModal'));
                currentBsModal.show();
            }

            async function saveJobFromModal() {
                const name = document.getElementById('modalJobName').value.trim();
                const code = document.getElementById('modalJobCode').value.trim() || name.toUpperCase();
                const subItemsStr = document.getElementById('modalJobSubItems').value.trim();

                if (!name) {
                    alert('Please enter a job category name.');
                    return;
                }

                const sub_items = subItemsStr.split(',').map(s => s.trim()).filter(s => s.length > 0).map(s => ({ name: s }));

                try {
                    const res = await fetch('/api/jobs', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, code, description: name, sub_items })
                    });
                    if (res.ok) {
                        if (currentBsModal) currentBsModal.hide();
                        loadJobsTable();
                    } else {
                        const err = await res.json();
                        alert(err.detail || 'Failed to save job category.');
                    }
                } catch(e) { alert('Error connecting to backend server.'); }
            }

            async function loadUsersTable() {
                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch('/api/auth/users', {
                        headers: { 'Authorization': 'Bearer ' + token }
                    });
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    const users = await res.json();

                    const pendingUsers = users.filter(u => u.status === 'PENDING');
                    const activeUsers = users.filter(u => u.status !== 'PENDING');

                    // Render Pending Requests Card
                    if (pendingUsers.length > 0) {
                        document.getElementById('join-requests-card').style.display = 'block';
                        document.getElementById('pending-requests-count').innerText = pendingUsers.length;
                        document.getElementById('sidebar-pending-count').innerText = pendingUsers.length;
                        document.getElementById('sidebar-pending-count').style.display = 'inline-block';

                        let pendingHtml = '';
                        pendingUsers.forEach(u => {
                            pendingHtml += `
                                <tr>
                                    <td><strong>${u.name}</strong> (${u.employee_id})</td>
                                    <td>${u.email || '-'}</td>
                                    <td><span class="badge bg-secondary">${u.department || 'General'}</span></td>
                                    <td>${u.mobile_phone || '-'}</td>
                                    <td>
                                        <button class="btn btn-sm btn-success me-1 fw-bold" onclick="updateUserStatus('${u.employee_id}', 'APPROVED')"><i class="bi bi-check-lg me-1"></i> Accept</button>
                                        <button class="btn btn-sm btn-outline-danger fw-bold" onclick="updateUserStatus('${u.employee_id}', 'DENIED')"><i class="bi bi-x-lg me-1"></i> Deny</button>
                                    </td>
                                </tr>`;
                        });
                        document.getElementById('pending-users-table-body').innerHTML = pendingHtml;
                    } else {
                        document.getElementById('join-requests-card').style.display = 'none';
                        document.getElementById('sidebar-pending-count').style.display = 'none';
                    }

                    // Render Active Users Table
                    let html = '';
                    activeUsers.forEach(u => {
                        const statusBadge = u.status === 'APPROVED' 
                            ? '<span class="badge bg-success">Approved</span>' 
                            : '<span class="badge bg-danger">Denied</span>';

                        html += `
                            <tr>
                                <td><strong>${u.employee_id}</strong></td>
                                <td>${u.name}</td>
                                <td><span class="badge bg-info text-dark">${u.role}</span></td>
                                <td>${u.department || 'N/A'}</td>
                                <td>${statusBadge}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-secondary" onclick="alert('User ID: ${u.employee_id}')"><i class="bi bi-gear"></i> Manage</button>
                                </td>
                            </tr>`;
                    });
                    document.getElementById('users-table-body').innerHTML = html || '<tr><td colspan="6" class="text-center text-muted">No active employees found.</td></tr>';
                } catch(e) {
                    console.error('Error loading users:', e);
                    document.getElementById('users-table-body').innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load users.</td></tr>';
                }
            }

            async function updateUserStatus(empId, newStatus) {
                try {
                    const token = await getAdminAuthToken();
                    const res = await fetch(`/api/auth/users/${empId}/status`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({ status: newStatus })
                    });
                    if (res.ok) {
                        loadUsersTable();
                    } else {
                        alert('Failed to update user status.');
                    }
                } catch(e) { alert('Server error updating user request.'); }
            }

            function toggleSelectAllJobs(source) {
                const checkboxes = document.querySelectorAll('.job-checkbox');
                checkboxes.forEach(cb => cb.checked = source.checked);
            }

            async function deleteSingleJob(id) {
                if (!confirm('Are you sure you want to delete this job category?')) return;
                try {
                    const res = await fetch(`/api/jobs/${id}`, { method: 'DELETE' });
                    if (res.ok) {
                        loadJobsTable();
                    } else {
                        alert('Failed to delete job.');
                    }
                } catch(e) { alert('Server error deleting job.'); }
            }

            async function bulkDeleteJobs() {
                const selected = Array.from(document.querySelectorAll('.job-checkbox:checked')).map(cb => cb.value);
                if (selected.length === 0) {
                    alert('Please select at least one job category to delete.');
                    return;
                }
                if (!confirm(`Delete ${selected.length} selected job categories?`)) return;

                for (let id of selected) {
                    await fetch(`/api/jobs/${id}`, { method: 'DELETE' });
                }
                loadJobsTable();
            }

            document.addEventListener("DOMContentLoaded", function() {
                initMap();
                loadPunchMap();
            });
        </script>
    </body>
    </html>
    """
