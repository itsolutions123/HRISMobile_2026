# DTR App — Project State
Last updated: September 16, 2026

## Stack (confirmed, do not change without discussion)
- Backend: FastAPI (Python 3.11, Uvicorn)
- Frontend Mobile: React Native / Expo Go (JavaScript, Node 20)
- Frontend Web Admin: Connecteam-inspired HTML5/Bootstrap 5 dashboard (integrated into FastAPI `/admin`)
- Database: PostgreSQL 15 (Container: `hris-postgres-db`, Database: `hrisdb`, User: `hrisuser`, Pass: `hrispassword`)
- Auth: Custom Employee ID + Password verification, REST endpoint `/api/auth/login`
- Repo structure:
  - `/backend`: FastAPI service, SQLAlchemy ORM models, database routers, Docker Compose definition
  - `/src`: React Native mobile application screens (`LoginScreen.js`, `DashboardScreen.js`, `HomeScreen.js`, `ManagerScreen.js`, `TimesheetScreen.js`), state context (`AuthContext.js`)

## STRICT ARCHITECTURE & DATA DIRECTIVES
- NEVER hardcode sample user records in JavaScript or fallback lists. All employee, user directory, and group enrollment data MUST strictly come from the PostgreSQL database via backend endpoints (`/api/auth/users`, `/api/jobs`, `/api/punch/logs`).

## Infra (fixed facts — never re-derive or guess these)
- App runs in Docker on Proxmox VM `ansible-srv` (10.0.10.37), accessed via SSH
- Backend REST API: `http://10.0.10.37:8089` (Container: `hris-fastapi-backend`)
- Mobile Metro Bundler: `http://10.0.10.37:8087` (Container: `hris-mobile-bundler`)
- SSL/reverse proxy is a SEPARATE Proxmox VM (10.0.10.250) running Nginx — the app itself does not terminate SSL
- Superadmin: ID `xinxaola` | Password `xenonjay@123` | Name `Super Admin Xenon`
- System Administrator: ID `3286` | Password `bigtime@123` | Name `Jaypee Balonzo`

## Done (do not rebuild these)
- [x] Backend REST API (`/api/auth/login`, `/api/auth/users`, `/api/jobs`)
- [x] Database baseline ORM models (`Employee`, `JobCategory`, `JobSubItem`, `PunchLog`, `Schedule`, `ScheduleGroup`, `ScheduleGroupAssignment`, `DtrRevision`, `LeaveRequest`)
- [x] React Native Mobile App scaffolding (`LoginScreen`, `DashboardScreen`, `HomeScreen`, `ManagerScreen`, `TimesheetScreen`)
- [x] Web Admin UI (`/admin`) Connecteam layout: Job datatables, OpenStreetMap Leaflet GPS map integration, User profile editor drawer
- [x] GPS Clock In/Out Core Backend (`POST /api/punch`, `GET /api/punch/active/{employee_id}`, duplicate rejection validation, mock location detection flags, PST timestamping)
- [x] Manager & Scheduling Backend (`/api/manager/team`, `/api/manager/schedules`, `/api/manager/revisions`)
- [x] DTR Engine & Computation API (`app/dtr_engine.py`, `GET /api/dtr/summary/{employee_id}`, `GET /api/dtr/export`)
- [x] Mobile User Registration with separate First Name, Last Name, Suffix, Email, Password, Department, and Mobile Phone.
- [x] Mobile "Remember password on this device" credentials caching via `AsyncStorage`.
- [x] Web Admin Users & Directory: Connecteam-aligned user directory datatable and read-only User Profile dashboard drilldown view.
- [x] Mobile DTR Shift Review modal on Clock Out with "Edit Shift" revision requests sent to the user's manager for approval.
- [x] Mobile Timesheet Screen calendar date filtering, 12-hour AM/PM time formatting, and direct shift edit request action.
- [x] Web Admin Smart Groups: Collapsible & editable main Brands (`Head Office`, `Stores`, `Commissary`), `+ Add Brand` creation, removable sub-groups, animated Pop-out Offcanvas detail drawer with close button, dynamic Clocked In metric, group admin assigner, and duplicate enrollment warnings.
- [x] Superadmin Auto-Seeding (`xinxaola` / `xenonjay@123`) & Automated Web Admin Token Acquisition.
- [x] Dynamic User Department Dropdown & Smart Group Membership Migration on Web Admin Profile Edit.
- [x] Mobile Duty Role Modal Sync & Comprehensive Punch Metadata Payload (Full Name, Employee ID, Department, Brand/Sub-Group, Timestamp, Date).
- [x] Cleaned Smart Groups Member Drawer UI (Removed redundant `+ Add Member` and `Remove` row actions).
- [x] Live Clock Feed Auto-Zoom on Map Marker & Interactive Time Clock History Table with Leaflet Popup Modal.
- [x] Mobile Clock Out Shift Review Modal with Location Verification, Map Refresh, Inline `| Edit` Revision Requests, and Fixed Navigation Tab Bar.

## Done (do not rebuild these)
- [x] Fix Smart Group connected count reload on page load (pre-fetch directory on init/tab switch).
- [x] Fix upper-right account header to dynamically reflect current logged-in user via `/api/auth/me`.

## In Progress / Ready for Next Steps
- [ ] Manager Approval Dashboard view for reviewing team DTR shift revision requests on mobile/web.
