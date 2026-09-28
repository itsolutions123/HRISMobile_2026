# DTR App - Project State
Last updated: September 29, 2026
Source of truth: this file was rebuilt from an audit of the actual repo code, not from memory.

## Stack (confirmed, do not change without discussion)
- Backend: FastAPI (Python 3.11, Uvicorn), SQLAlchemy ORM, slowapi rate limiting
- Mobile: React Native / Expo SDK 57 (JavaScript). Read https://docs.expo.dev/versions/v57.0.0/ before writing mobile code (see AGENTS.md)
- Web Admin: Bootstrap 5 + Leaflet HTML shell, served by FastAPI at `/admin` (lives inside `backend/app/main.py`)
- Database: PostgreSQL 15 (container `hris-postgres-db`, database `hrisdb`, user `hrisuser`). Credentials are in `backend/.env` (gitignored). Never write them in this file.
- Auth: Employee ID or email + password, `POST /api/auth/login`, JWT (HS256, 24h). Roles: `Employee`, `Manager`, `Admin` (`Superadmin` is accepted by some routers)
- Repo structure:
  - `/backend`: FastAPI service (`app/main.py`, `models.py`, `database.py`, `auth_utils.py`, `dtr_engine.py`, `limiter.py`, `routers/`), `Dockerfile`, `docker-compose.yml`
  - `/src`: mobile app (`screens/`: Login, Dashboard, Timesheet, Manager, Home; `context/AuthContext.js`)
  - `App.js`, `index.js`, `app.json`, `package.json` at the repo root

## STRICT ARCHITECTURE & DATA DIRECTIVES
- API-first and dynamic by default. Employee, directory, form, group, brand, job and punch data must come from PostgreSQL via the API. Never from literals, fallback lists or localStorage.
- Static content is allowed only for "as-is" syntax and markup scaffolding.
- Schema or contract changes are decided by the Architect Gem, not during implementation.

## Infra (fixed facts)
- Docker host: Proxmox VM `ansible-srv` (10.0.10.37), accessed via SSH, user `ansibleadmin`
- Backend REST API: `http://10.0.10.37:8089` (container `hris-fastapi-backend`, compose service `hris-backend`)
- Mobile Metro bundler: `http://10.0.10.37:8087` (container `hris-mobile-bundler`). NOT defined in `backend/docker-compose.yml`, so its definition needs to be located.
- SSL / reverse proxy: separate Proxmox VM (10.0.10.250) running nginx. The app does not terminate TLS. Public URL: `https://app.bigtimeempire.com`
- Restart after backend changes:
  `docker compose -f ~/HRISMobileApp/backend/docker-compose.yml up -d --build hris-backend`
- Full deploy: WinSCP transfer, then `docker compose down && docker compose build --no-cache && docker compose up -d`
- Seeded accounts on first startup (only if missing and `INITIAL_SUPERADMIN_PASSWORD` is set): Super Admin `xinxaola`, System Administrator `3286`. Passwords are NOT stored here.

## DONE (verified in code)

### Backend
- Auth: register (PENDING + generated `EMPxxx` ID), login (5/min limit, blocks PENDING/DENIED/ARCHIVED), `/me`, list users, update profile (incl. ID rename), update status
- Punch: `POST /api/punch` (GPS required, range check, mock flag check, duplicate-sequence rejection, Asia/Manila timestamp), `GET /active/{id}`, `GET /logs`, `GET /export` (CSV)
- Jobs: legacy categories/sub-items (list/create/delete), brands (list/create/rename/delete with group cascade), smart groups (list/create/rename/delete/set admins)
- Manager: team list, DTR revision request / my-requests / pending list / approve-reject with signature and note (approval writes the punch), schedule groups, shift schedules
- DTR: `GET /summary/{id}` (late, undertime, overtime, regular hours, night shifts, explicit breaks), `GET /export` (XLSX, optional `simpleeval` custom formula)
- Forms: category CRUD + archive, form list/get/create/update/delete/duplicate, submissions list/create

### Web Admin (`/admin`)
- Login overlay, JWT session, identity in top bar, URL routing with back/forward
- Time Clock: live clocked-in feed + Leaflet map, history table with date filter and search, punch detail modal with map
- Smart Groups: brands (rename/delete), groups per brand, detail drawer (members, clocked-in count, department job chips)
- Users & Directory: Users/Admins/Archived tabs, search, pending/denied approvals modal, profile editor (details, department, role, archive/un-archive, punch Activity tab)
- Forms: dynamic sidebar categories (rename/delete), forms list (active/archived), form builder (dropdown and description editors, reorder), detail view, assignments drawer

### Mobile
- Login/register with department dropdown, "remember password" via AsyncStorage
- Role-based tabs (Manager tab for managers only)
- Dashboard: GPS map, duty-role picker, active-shift timer, clock-out review with GPS refresh, shift-edit request
- Timesheet: calendar, per-day punches, Google Maps link, revision request
- Manager Hub: Revisions (approve/reject with signature), Team, Groups, Export
- `HomeScreen.js` exists but is NOT wired into `App.js` (orphaned; decide keep or remove)

## KNOWN BROKEN / MISMATCHES (found in audit, not yet fixed)
1. `POST /api/auth/users` does not exist (`UserCreateRequest` is unused). The web "Add users" modal calls it and fails.
2. Web calls `PUT /api/forms/{id}/archive`, which does not exist. Archive works only via `PUT /api/forms/{id}` with `is_archived`.
3. Punch metadata (full name, department, brand/sub-group, job title, date, timestamp) is sent by mobile but not accepted by `PunchRequest`, so it is discarded.
4. Revision requests: `attachment_note` is ignored. Dashboard clock-out edits send `HH:MM:SS AM/PM`, but the API expects a datetime, so it likely returns 422.
5. Export buttons fail: web `/api/dtr/export` is opened with no dates and no auth, and mobile `Linking.openURL` sends no token (401).
6. Web "Rename group" is broken (`setStoredGroups` undefined, async `getStoredGroups` used as sync). Group-admin dropdown helpers are not defined. The rename-group API expects `new_name`.
7. No auth on `/api/punch/*`, `/api/jobs` GET/POST/DELETE, `/api/manager/schedules` GET. `employee_id` is trusted from the client.
8. Stray empty files committed: `-H`, `-d`, `backend/-H`, `backend/-d`.
9. Two `PROJECT_STATE.md` copies (root and `backend/`) had diverged. `backend/PROJECT_STATE.md` is stale.

## HARDCODE BACKLOG (violates dynamic-by-default; some need Architect schema/contract changes)
- Mobile: `API_BASE_URL` in `AuthContext.js`; deep-link prefixes in `App.js`; default map coordinates; "8:00 AM - 5:00 PM" schedule text; fallback job-title lists per department in `DashboardScreen`; fallback department list in `LoginScreen`; fixed "8.0 hrs" in `TimesheetScreen`
- Web (`main.py`): brand "Head Office" on history rows; fake total fallbacks ("0.5 hrs", "8.0 hrs"); default new-user password; assignments modal with fixed groups, fixed users and fixed counts; fixed form counts, date range and "created" date; static Employment tab; `defaultBrandsInitial` / `defaultGroupsInitial`; department jobs stored in localStorage instead of the database
- Backend: fallback JWT secret (`auth_utils.py`) and fallback DB URL with credentials (`database.py`); grace period (15) and break (60) in `dtr.py`; default brands/groups seeded in `jobs.py`; role and status strings scattered across routers; CORS origins in `main.py`

## SECURITY TO-DO
- Passwords for `xinxaola`, `3286` and the DB user were stored in plaintext in earlier versions of this file, so they exist in git history. Rotate all three, and remove the default fallback secrets in code.
- Remove the default new-user password from the web panel.
- Add auth to the open endpoints listed in item 7 above.

## IN PROGRESS / NEXT (pick one at a time)
- [ ] Mobile/tablet responsive layout fix for `/admin`
- [ ] Manager approval dashboard for DTR revisions on web (mobile version exists in `ManagerScreen`)
- [ ] Fix the Known Broken items above (suggested order: 3, 4, 1, 5, 2, 6, 7)
- [ ] Locate the `hris-mobile-bundler` definition and add it to version control
