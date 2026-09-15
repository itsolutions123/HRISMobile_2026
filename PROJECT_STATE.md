# DTR App — Project State
Last updated: September 15, 2026

## Stack (confirmed, do not change without discussion)
- Backend: FastAPI (Python 3.11, Uvicorn)
- Frontend Mobile: React Native / Expo Go (JavaScript, Node 20)
- Frontend Web Admin: Connecteam-inspired HTML5/Bootstrap 5 dashboard (integrated into FastAPI `/admin`)
- Database: PostgreSQL 15 (Container: `hris-postgres-db`, Database: `hrisdb`, User: `hrisuser`, Pass: `hrispassword`)
- Auth: Custom Employee ID (`3286`) + Password verification, REST endpoint `/api/auth/login`
- Repo structure:
  - `/backend`: FastAPI service, SQLAlchemy ORM models, database routers, Docker Compose definition
  - `/src`: React Native mobile application screens (`LoginScreen.js`, `DashboardScreen.js`, `HomeScreen.js`, `ManagerScreen.js`, `TimesheetScreen.js`), state context (`AuthContext.js`)

## Infra (fixed facts — never re-derive or guess these)
- App runs in Docker on Proxmox VM `ansible-srv` (10.0.10.37), accessed via SSH
- Backend REST API: `http://10.0.10.37:8089` (Container: `hris-fastapi-backend`)
- Mobile Metro Bundler: `http://10.0.10.37:8087` (Container: `hris-mobile-bundler`)
- SSL/reverse proxy is a SEPARATE Proxmox VM (10.0.10.250) running Nginx — the app itself does not terminate SSL
- Primary Admin / System Administrator: ID `3286` | Password `bigtime@123` | Name `Jaypee Balonzo`

## System Architecture & Master Specs (Architect Baseline)
- Primary Keying: `employees.employee_id` (String key, e.g., `"3286"`)
- Roles: `Employee`, `Manager`, `Admin`
- Target Models: `Employee`, `JobCategory`, `JobSubItem`, `PunchLog`, `Schedule`, `ScheduleGroup`, `ScheduleGroupAssignment`, `DtrRevision`, `LeaveRequest`
- Punches Supported: `CLOCK_IN`, `CLOCK_OUT`, `BREAK_IN`, `BREAK_OUT`
- API Matrix Ownership:
  - `/api/auth/login`, `/api/auth/users`, `/api/auth/users/{emp_id}` -> Auth/RBAC Gem
  - `/api/punch`, `/api/punch/active/{employee_id}`, `/api/punch/logs`, `/api/punch/export` -> GPS Clock In/Out Gem
  - `/api/manager/team`, `/api/manager/schedules`, `/api/manager/revisions` -> Manager & Scheduling Gem
  - `/api/dtr/summary/{employee_id}`, `/api/dtr/export` -> DTR & Payroll Export Gem

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
- [x] Web Admin Users & Directory enhancements: Live Search, Department/Role/Status filters, Date Added column, Editable Employee ID, Offcanvas Profile Drawer Editor, Archive User Retention, and Bootstrap Toast feedback.
- [x] Mobile DTR Shift Review modal on Clock Out with "Edit Shift" revision requests sent to the user's manager for approval.
- [x] Mobile Timesheet Screen calendar date filtering, 12-hour AM/PM time formatting, and direct shift edit request action.

## In Progress / Ready for Next Steps
- [ ] Manager Approval Dashboard view for reviewing team DTR shift revision requests on mobile/web.
