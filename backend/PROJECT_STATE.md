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
- Target Models: `Employee`, `JobCategory`, `JobSubItem`, `PunchLog`, `Schedule`, `LeaveRequest`
- Punches Supported: `CLOCK_IN`, `CLOCK_OUT`, `BREAK_IN`, `BREAK_OUT`
- API Matrix Ownership:
  - `/api/auth/login`, `/api/auth/users`, `/api/auth/users/{emp_id}` -> Auth/RBAC Gem
  - `/api/punch/log`, `/api/punch/logs` -> GPS Clock In/Out Gem
  - `/api/manager/team`, `/api/manager/schedules` -> Manager & Scheduling Gem
  - `/api/dtr/timesheet`, `/api/dtr/export` -> DTR & Payroll Export Gem

## Done (do not rebuild these)
- [x] Backend REST API (`/api/auth/login`, `/api/auth/users`, `/api/jobs`, `/api/punch`)
- [x] Database baseline ORM models (`Employee`, `JobCategory`, `JobSubItem`, `PunchLog`, `Schedule`, `LeaveRequest`)
- [x] React Native Mobile App scaffolding (`LoginScreen`, `DashboardScreen`, `HomeScreen`, `ManagerScreen`, `TimesheetScreen`)
- [x] Web Admin UI (`/admin`) Connecteam layout: Job datatables, OpenStreetMap Leaflet GPS map integration, User profile editor drawer

## In Progress / Ready for Part-Gems
- [ ] Auth/RBAC Gem: Add `role`, `manager_id`, and `kiosk_code` fields to router endpoints
- [ ] GPS Clock In/Out Gem: Support `BREAK_IN`/`BREAK_OUT` & `job_sub_item_id` in `/api/punch/log`
- [ ] Manager & Scheduling Gem: Implement `/api/manager/team` and shift schedule endpoints
- [ ] DTR & Payroll Export Gem: Implement late/undertime calculation engine and CSV export stream at `/api/dtr/export`
