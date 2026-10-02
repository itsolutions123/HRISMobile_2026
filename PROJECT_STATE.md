# DTR App - Project State
Last updated: October 2, 2026
Source of truth: rebuilt from the repo files pasted on this date (backend, web panel in `main.py`, mobile `src/`, docs, config). Commit hash not captured: run `git log --oneline -1` and add it here.
Method: code reading only. Nothing below was run against the live server unless marked VERIFIED-RUNTIME. Items marked UNVERIFIED need a command or doc check before anyone builds on them.

Status tags used in this file: [OK] works as written, [PARTIAL] works with gaps, [BROKEN] will fail, [MOCK] static or fake data shown as real.

## Stack (confirmed, do not change without discussion)
- Backend: FastAPI (Python 3.11, Uvicorn), SQLAlchemy ORM, slowapi (login rate limit only), bcrypt, python-jose (HS256 JWT), openpyxl + simpleeval (XLSX export with optional formula)
- Mobile: React Native 0.86 / Expo SDK 57 (JavaScript), React Navigation (native-stack + bottom-tabs). Read https://docs.expo.dev/versions/v57.0.0/ before writing mobile code (see AGENTS.md)
- Web Admin: Bootstrap 5 + Leaflet, one HTML/JS string inside `backend/app/main.py`, served at `/admin` and `/admin/{path}`
- Database: PostgreSQL 15 (container `hris-postgres-db`, database `hrisdb`, user `hrisuser`). Credentials live in `backend/.env` (gitignored). Never write them in this file.
- Auth: Employee ID or email + password, `POST /api/auth/login`, JWT HS256, 24h, no refresh, no revocation. Roles in use: `Employee`, `Manager`, `Admin`. `Superadmin` is accepted by some routers but is never assigned by any UI or seed.
- Employee.status values: `PENDING`, `APPROVED`, `DENIED`, `ARCHIVED`

## STRICT ARCHITECTURE & DATA DIRECTIVES
- API-first and dynamic by default. Employee, directory, form, group, brand, job and punch data must come from PostgreSQL via the API. Never from literals, fallback lists or localStorage.
- Static content is allowed only for "as-is" syntax and markup scaffolding.
- Schema or contract changes are decided by the Architect Gem, not during implementation.

## Infra (fixed facts)
- Docker host: Proxmox VM `ansible-srv` (10.0.10.37), SSH user `ansibleadmin`. Repo clone: `~/HRISMobileApp` (confirm with `git rev-parse --show-toplevel`).
- Backend REST API: `http://10.0.10.37:8089` (container `hris-fastapi-backend`, compose service `hris-backend`, container port 8000)
- Database container has no published port (only reachable on the compose network `hris-network`).
- Mobile Metro bundler: `http://10.0.10.37:8087` (container `hris-mobile-bundler`). NOT defined in `backend/docker-compose.yml`, so its definition still needs to be located.
- SSL / reverse proxy: separate Proxmox VM (10.0.10.250) running nginx. The app does not terminate TLS. Public URL: `https://app.bigtimeempire.com`
- Backend code is baked into the image (`COPY app ./app`, no bind mount). A plain `docker restart` does NOT pick up code changes: always rebuild.
- Restart after ANY backend or web-panel change (the panel lives in `main.py`):
  `docker compose -f ~/HRISMobileApp/backend/docker-compose.yml up -d --build hris-backend`
- Check after restart: `docker logs --tail 30 hris-fastapi-backend` and `curl -s http://localhost:8089/` (expects `{"status":"online",...}`)
- Full deploy: WinSCP transfer, then `docker compose down && docker compose build --no-cache && docker compose up -d`. Never add `-v` (it deletes the `hris_pgdata` volume).
- Seeded accounts on first startup (only if missing and `INITIAL_SUPERADMIN_PASSWORD` is set): `xinxaola` and `3286`. Passwords are NOT stored here. On EVERY startup the seed forces both to role Admin and status APPROVED.

## Repo structure (verified from pasted files)
- `/backend`: `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `app/`
  - `app/main.py`: app setup, CORS, startup seed, the whole web panel HTML/JS (about 3,000 lines), plus a stray block of duplicate form-submission code at the bottom
  - `app/models.py`, `database.py`, `auth_utils.py`, `dtr_engine.py`, `limiter.py`
  - `app/routers/`: `auth.py`, `punch.py`, `jobs.py`, `manager.py`, `dtr.py`, `forms.py`
- Root (mobile): `App.js`, `index.js`, `app.json`, `eas.json`, `package.json`, `.gitignore` (ignores `.env*`), `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `LICENSE` (Expo's template MIT licence, not this project's)
- `/src/context/AuthContext.js` (token and user held in React state only, base URL from `EXPO_PUBLIC_API_BASE_URL`)
- `/src/screens/`: `LoginScreen`, `HomeScreen`, `DashboardScreen` (Time Clock), `TimesheetScreen`, `FormsScreen`, `ProfileScreen`, `ManagerScreen` (shown as the "Admin" tab)
- `/docs`: `API.md` (Forms section only), `DECISIONS.md` (D-001 APPROVED, D-002 PROPOSED). `SECURITY.md`, `CODE_STYLE.md`, `DATABASE.md` were not in the pasted set: UNVERIFIED whether they exist.

## Mobile navigation (App.js)
- Not logged in: `Login` (login or request-to-join mode)
- Logged in: bottom tabs `Home`, `Forms`, `Profile`, plus `Admin` only when role is manager/admin/superadmin (case-insensitive). Stack screens opened from Home: `Dashboard` ("Time Clock") and `Timesheet`.
- Deep-link config in `App.js` uses fixed prefixes and `admin/...` paths: hardcode, and Dashboard/Timesheet are not in it.
- Session is not persisted: closing the app logs the user out.

## API map (from router code)
Auth column: Public / Token / role list. "No client" means no call site in the pasted mobile or web code.

| Method | Path | Auth | Used by |
|---|---|---|---|
| POST | /api/auth/register | Public (no rate limit) | Mobile Login (join request) |
| POST | /api/auth/login | Public, 5/min per IP | Mobile, Web |
| GET | /api/auth/me | Token | Web top bar |
| GET | /api/auth/users | Admin, Manager, Superadmin | Web directory, groups, history |
| PUT | /api/auth/users/{emp_id} | Admin | Web profile editor |
| PUT | /api/auth/users/{emp_id}/status | Admin | Web, Mobile Admin tab |
| POST | /api/auth/users | DOES NOT EXIST | Web "Add users" (fails) |
| GET | /api/punch/active/me | Token | Mobile Home, Dashboard |
| POST | /api/punch | Token (identity from token) | Mobile Dashboard |
| GET | /api/punch/logs | Admin, Superadmin, Manager | Web Home/Time Clock/Activity; Mobile Timesheet |
| GET | /api/punch/export (CSV, all rows, dates ignored) | Admin, Superadmin, Manager | Mobile Admin > Export |
| GET | /api/jobs/public | Public | Mobile Login (department list) |
| GET | /api/jobs | Token | Mobile Dashboard (duty roles) |
| POST, DELETE | /api/jobs, /api/jobs/{id} | Admin, Superadmin | No client |
| GET | /api/jobs/brands | Token (seeds defaults if empty) | Web |
| POST, PUT, DELETE | /api/jobs/brands[/{name}] | Admin, Superadmin | Web |
| GET | /api/jobs/groups | Token (seeds defaults if empty) | Web, Mobile Admin > Smart Groups |
| POST, DELETE | /api/jobs/groups[/{name}] | Admin, Superadmin | Web |
| PUT | /api/jobs/groups/{name} (body `new_name`) | Admin, Superadmin | Web rename (broken client) |
| PUT | /api/jobs/groups/{name}/admins | Admin, Superadmin | No client |
| GET | /api/manager/team | Manager, Admin | Mobile Admin > Users |
| POST | /api/manager/revisions/request | Token | Mobile Timesheet, Dashboard |
| GET | /api/manager/revisions/my-requests | Token | No client |
| GET | /api/manager/revisions | Manager, Admin | Mobile Admin > Attendance |
| POST | /api/manager/revisions/{id}/action | Manager, Admin | Mobile Admin |
| GET, POST | /api/manager/groups | Manager, Admin | No client (ScheduleGroup) |
| GET | /api/manager/schedules | Token (no role check) | No client |
| POST | /api/manager/schedules | Manager, Admin | No client |
| GET | /api/dtr/summary/{emp_id} | Self, or Manager/Admin | Mobile Timesheet |
| GET | /api/dtr/export (XLSX) | Manager, Admin | Web sidebar (broken client) |
| GET/POST/PUT/PATCH/DELETE | /api/forms/categories... | GET: Token; writes: Admin, Superadmin | Web, Mobile (GET) |
| GET | /api/forms | Token (no assignment filter) | Mobile Forms, Web |
| POST, PUT, DELETE, POST duplicate | /api/forms[/{id}[/duplicate]] | Admin, Superadmin | Web |
| GET | /api/forms/{id} | Token | Web |
| GET | /api/forms/{id}/submissions | Token (any user) | Web |
| POST | /api/forms/{id}/submissions | Token | Mobile Forms |
| GET, POST | /api/forms/signatures/my-signature | Token | No client |
| GET | / and /admin, /admin/{path} | Public (HTML shell, no data) | Browser |

## Data model (models.py)
`employees`, `job_categories`, `job_sub_items`, `punch_logs`, `schedules`, `schedule_groups`, `schedule_group_assignments`, `dtr_revisions`, `leave_requests` (no router, no UI), `form_categories`, `custom_forms`, `form_submissions`, `brand_locations`, `smart_groups`, plus `custom_form_submissions` declared in `main.py` (unused, see B-13).
- Three overlapping "group" concepts: `SmartGroup` (web/mobile admin, form assignment), `ScheduleGroup` (scheduling, no UI), `JobCategory` (duty roles, registration department list). `Employee.department` holds a free string that can be a JobCategory name (mobile register) or a SmartGroup name (web profile editor). Architect decision needed.
- `Employee.manager_id` exists but no endpoint or UI can set it, so Manager team = same department only.
- `Employee.kiosk_code` column exists but the API returns `employee_id.zfill(4)` instead.
- `PunchLog.job_sub_item_id` exists but is never written. The job name is carried as text inside `address`.
- Time: punches are stored as naive Asia/Manila time; model defaults and revision timestamps use naive UTC; form `date_created` uses container local time. Mixed: needs a docs/DATABASE.md rule.

## Features that work (verified in code)

### Backend
- Auth: register (PENDING + generated `EMPxxx` id), login (blocks PENDING/DENIED/ARCHIVED, 5/min), `/me`, list users, update profile (incl. employee id rename), update status
- Punch: GPS required, lat/long range check, duplicate-sequence rejection, Manila timestamp, identity from token, active-shift status
- Jobs: categories/sub-items, brands (rename/delete cascades to groups), smart groups (create/rename/delete/admins)
- Manager: team list, revision request, pending list, approve/reject with signature + note (approval rewrites or inserts the punch), schedule groups, shift schedules
- DTR engine: late (after grace), undertime, regular hours, explicit break punches, overtime only when approved (always off today), schedule lookup individual then group, defaults when no schedule
- Forms: category CRUD + archive, form CRUD + duplicate, submissions list/create with `form_data` stored as JSON text

### Web Admin (`/admin`)
- [OK] Login overlay, JWT in localStorage, identity in top bar, URL routing with back/forward
- [PARTIAL] Home: clocked-in-now list works; "Need to clock out" is always empty and names fall back to ids (B-09); Feed is static text
- [OK] Time Clock: live clocked-in list + Leaflet map, history table by date with search, punch detail modal with map
- [PARTIAL] Smart Groups: brands and groups add/delete/rename-brand work; group rename and group-admin picker are broken (B-06); "selected" dropdown is fake
- [PARTIAL] Users & Directory: tabs, search, approve/deny/archive, profile editor save work; Add users fails (B-01); Last login, Employment Start, Added by, Employment tab, Time off, Notes are static
- [PARTIAL] Forms: dynamic sidebar categories (rename/delete work), forms list, builder (Open Ended, Description rich text, Dropdown, Yes/No, Date, Task, Signature, plus Location and Rating which have no editor), preview, submissions table, submission viewer with PDF download. Archive actions are broken or fake (B-02), assignments drawer mis-groups (B-10)
- [MOCK] Sidebar "Scheduling" (toast only), "Company policies", "Settings", legacy `form-creator-view` (lorem ipsum), old `editAssignmentsModal` (fixed users and counts)
- [BROKEN] Sidebar "Export DTR" (B-05)

### Mobile
- Login/register: [OK] department dropdown (feeds registration only), remember-me (see S-03)
- Home: [PARTIAL] live timer and clocked-in status work; Feed is mock; "Weekly Hours" is a "coming soon" alert
- Dashboard (Time Clock): [PARTIAL] GPS map (Leaflet in WebView), duty-role picker from `/api/jobs`, clock in/out, switch role, review modal with GPS refresh. Failed punches show no message (B-12). Revision edit flow likely fails (B-04)
- Timesheet: [PARTIAL] calendar and per-day punches; broken for Employee role (B-07); duration pill hardcoded
- Forms: [PARTIAL] categories > forms > fill > submit works; field support is limited (B-14), required not enforced, false success on failure (B-08)
- Profile: [MOCK] leave counts 0/0/0, "My Submissions", "Personal Information", "Settings" are placeholders; Logout works
- Admin tab: [PARTIAL] Attendance (revisions approve/reject with typed signature) works; Users tab list works but approve/deny needs Admin (B-11); Smart Groups list works; Export fails (B-05); attendance counter is mock
- Android APK: `preview` profile in `eas.json`, package `com.bigtime.hrismobileapp.test`, built with `EXPO_PUBLIC_API_BASE_URL=https://app.bigtimeempire.com`. Confirmed working over mobile data.

### Form field support (web builder vs mobile renderer)
| Field | Web builder | Mobile renderer |
|---|---|---|
| Open Ended | yes | multiline text |
| Description | yes (rich HTML) | HTML in WebView |
| Dropdown | yes | radio list |
| Yes/No | yes | buttons |
| Task / Checkbox | yes | checkbox group |
| Signature | yes | draw or upload (WebView canvas) |
| Date | yes (date/time flags) | plain text `mm/dd/yyyy`, flags ignored |
| Location, Rating | yes (no editor) | falls back to plain text |
| Number, File Upload | legacy builder only | falls back to plain text |

## KNOWN BROKEN / MISMATCHES (found in code audit, not yet fixed)
1. B-01 `POST /api/auth/users` does not exist (`UserCreateRequest` is unused). Web "Add users" fails. The web code also sends a hardcoded default password.
2. B-02 Web calls `PUT /api/forms/{id}/archive`, which does not exist (archive works via `PUT /api/forms/{id}` with `is_archived`). "Archive Category" and the form-detail "Archive" only show a success toast and call no API.
3. B-03 `PunchRequest` accepts only employee_id (ignored), punch_type, lat, long, accuracy, address, is_mock. Mobile also sends full_name, department, brand_subgroup, job_title, date, timestamp: silently dropped. Job name travels inside `address`; clock-out overwrites it with "Shift Ended". `punch_type` is not validated against the allowed set.
4. B-04 Dashboard revision edits send a time-only locale string (for example "08:00:00 AM") where the API expects a datetime: likely 422 (UNVERIFIED at runtime). `attachment_note` is ignored. Timesheet sends `YYYY-MM-DD HH:MM:SS`.
5. B-05 Exports: web opens `/api/dtr/export` with no dates and no token. Mobile Export calls `/api/punch/export?start_date&end_date`, which ignores dates, returns a CSV of ALL logs, while the button says ".xlsx". Mobile uses `FileSystem.documentDirectory` and `downloadAsync` from `expo-file-system`: UNVERIFIED against the SDK 57 docs (the legacy API may have moved).
6. B-06 Web "Rename group" is broken (`setStoredGroups` undefined, async `getStoredGroups` used as sync, no API call). Group-admin dropdown helpers are undefined and no client calls `PUT /api/jobs/groups/{name}/admins`. The rename API expects `new_name`.
7. B-07 Mobile Timesheet calls `/api/punch/logs`, which needs Manager/Admin: Employees get 403 and see no punches. Managers download every employee's logs. The duration pill shows a fixed "8.0 hrs" even though `/api/dtr/summary` already returns `regular_hours`.
8. B-08 Mobile Forms: on a non-OK response it alerts "Form submitted (Offline mock/Sync pending)" and returns to the list. Data is lost. `required` fields are not enforced. Answers are keyed by label, so duplicate labels collide.
9. B-09 Web Home reads `full_name` and `clock_out_time` from `/api/punch/logs`, which does not return them. Result: empty "Need to clock out" list, names shown as ids.
10. B-10 Web assignments drawer groups by `g.brand_name`, but the API returns `brand`: every group lands under "General".
11. B-11 Mobile Admin tab: Manager role sees it but approve/deny calls Admin-only `PUT /api/auth/users/{id}/status` (403). "Deny" sends `ARCHIVED` while web sends `DENIED`. Archive button is a "coming soon" alert.
12. B-12 Mobile Dashboard `submitPunch` ignores non-OK responses: a rejected duplicate punch or GPS error shows nothing.
13. B-13 `main.py` bottom declares `CustomFormSubmission`, and `POST/GET /api/forms/{form_id}/submissions` after `include_router(forms.router)`. They are shadowed by the router versions (dead code by registration order, confirm with `/openapi.json`) and reference `CustomForm.entries`, which does not exist. The extra table `custom_form_submissions` is still created.
14. B-14 Mobile form renderer has no component for Number, Location, File Upload, Rating; Date is free text.
15. B-15 Web has no 401 handling: after the 24h token expires, screens silently show empty data instead of returning to login.
16. B-16 Web builds inline `onclick="...('${name}')"` from data. `.replace(/'/g, "\'")` inside the Python string becomes a no-op (`"\'"` is `"'"`), so names containing an apostrophe break handlers.
17. B-17 Scheduling has API only: no web or mobile UI. `POST /api/manager/schedules` always inserts (no update), while `dtr.py` takes `.first()`, so duplicates give arbitrary results.
18. B-18 Night shifts: the engine handles a shift ending after midnight, but punches are fetched per calendar day, so a clock-out on the next day makes the day INCOMPLETE.
19. B-19 Stray empty files committed: `PYEOF` (repo root, from a heredoc mishap), plus `-H`, `-d`, `backend/-H`, `backend/-d` from the earlier audit (re-confirm with `git ls-files`).
20. B-20 `TimesheetScreen` style `summaryBar` uses invalid key `justify` (should be `justifyContent`). `HomeScreen` and `Dashboard` both poll status (5s and 4s).
21. B-21 `registration` generates `EMP{count+1}`: collides after deletes or id renames (unique constraint, 500 error). `PUT /api/jobs/groups/{name}` rename does not update `employees.department` or forms' `assigned_groups`.

## HARDCODE BACKLOG (violates dynamic-by-default; some need Architect schema/contract changes)
- Mobile
  - H-01 Deep-link prefixes in `App.js`
  - H-02 Fallback department list and default 'IT Operations' in `LoginScreen`; fallback job-title lists per department in `DashboardScreen`; default map coordinates in `DashboardScreen`
  - H-03 `HomeScreen` mockFeed; `ProfileScreen` leave counts 0/0/0; `ManagerScreen` attendance `{clockedIn: 12, total: 45}`
  - H-04 Fixed "8.0 hrs" (`TimesheetScreen`), fallback '08:00 AM' / '05:00 PM' display times (`DashboardScreen`)
  - H-05 GPS timeout (6s) and accuracy level in `DashboardScreen`
- Web (`main.py`)
  - H-06 Seed-style identity literals in markup ("Super Admin Xenon", "xinxaola", "SA"), brand "Head Office" on history rows, fake totals ("0.5 hrs", "8.0 hrs"), "Celebrating today" text
  - H-07 Default new-user password literal in `saveDirectNewUser`
  - H-08 Fake directory columns (last login, employment start, added by), static Employment tab, fixed form counts (151, 5, 16), fixed date range, "86" assignees, "15 selected"
  - H-09 `defaultBrandsInitial` / `defaultGroupsInitial` (include a real employee name as creator), `getDeptJobsStore` default jobs, and department jobs kept in localStorage instead of the database (so web job chips never reach mobile duty roles)
  - H-10 Default map coordinates (14.5995, 120.9842)
  - H-11 Third-party assets from CDNs (jsdelivr, unpkg, Google Fonts, cdnjs): not data, but the panel does not run offline
- Backend
  - H-12 Fallback JWT secret (`auth_utils.py`) and fallback DB URL with credentials (`database.py`)
  - H-13 Grace period (15), break (60), default shift 08:00-17:00 and `overtime_approved=False` in `dtr.py`
  - H-14 Default brands/groups seeded in `jobs.py`; "HO - " prefix stripping in `jobs.py`; `SmartGroup.selected` default "15 selected"
  - H-15 Forms list: `views` fixed at 1, `administrated_by` "+1", `created_avatar` "SA", default group "All users group", `totalAssignees` = all employees
  - H-16 Seed accounts in `main.py` contain real name, phone and email literals; seed category "Head Office" and four role names
  - H-17 Role and status strings scattered across routers; CORS origins in `main.py`

## SECURITY TO-DO
- S-01 Passwords for `xinxaola`, `3286` and the DB user were stored in plaintext in earlier versions of this file, so they exist in git history. Rotate all three.
- S-02 Remove fallback secrets in code (H-12). Fail at startup if `JWT_SECRET_KEY` or `DATABASE_URL` is missing.
- S-03 Mobile "remember password" stores the plaintext password in AsyncStorage (`hris_last_password`). Remove it or move to a secure store (check SDK 57 docs first).
- S-04 `get_current_user` does not check `status`: ARCHIVED/DENIED users keep access until the 24h token expires. D-002 rollback mentions `is_active`, which does not exist: use `status`.
- S-05 `verify_password` falls back to plaintext comparison for non-bcrypt hashes and when bcrypt raises. Never upgrades old hashes.
- S-06 Any logged-in user can `GET /api/forms/{id}/submissions` (all answers and signatures). `GET /api/forms` ignores assignments. `POST` submission does not check the form exists, is active, or is assigned.
- S-07 Revision approval has no team-scope check, no PENDING-only check, and allows self-approval.
- S-08 Role checks are inconsistent (Superadmin accepted in some routers, not in `manager.py` or `dtr.py`). Centralize.
- S-09 Web writes unescaped data into `innerHTML` (names, form names, submissions, descriptions). Description HTML is also rendered in a mobile WebView with JavaScript on and `originWhitelist` `*`. Admin-authored HTML is a stored-XSS path.
- S-10 `register` is public with no rate limit. Login limit uses the client address; behind nginx it may be one shared bucket for everyone (UNVERIFIED, test with two clients; check `--proxy-headers` / `--forwarded-allow-ips`).
- S-11 Anti-spoofing relies on a client flag (`is_mock`) that mobile never sends. No geofence, no accuracy threshold.
- S-12 Review `usesCleartextTraffic: true` in `app.json`. The APK uses HTTPS, so it is probably no longer needed. Confirm, then remove.
- S-13 No pagination or size limits: `/api/punch/logs` returns all rows; `/api/dtr/summary` and `/export` accept any date range; base64 signatures are stored in String columns with no payload cap.
- S-14 Startup seed re-approves and re-promotes the two seed accounts on every boot, undoing an archive.
- S-15 Web token lives in localStorage; no CSP; only one CDN script has an SRI hash.
- S-16 `requirements.txt` is unpinned (`>=`), lists `pip`/`setuptools`, includes `passlib` (code uses `bcrypt` directly) and `python-jose`. Container runs as root, no healthcheck, DB has no `depends_on` health condition.

## DOC DRIFT (fix in the same commit as the related change)
- `docs/API.md`: forms list/detail shapes do not match `forms.py` (code returns `name`, `status`, `entries`, `schema_fields`, camelCase mix); Known Gaps API-01/02/03 appear resolved (submission stores `form_data`); base URL note is stale (AuthContext now reads `EXPO_PUBLIC_API_BASE_URL`); auth, jobs, dtr, punch, manager sections still missing.
- `docs/DECISIONS.md`: D-002 is still PROPOSED but the APK build exists; it also lists version 1.0.0 and an AuthContext default URL, neither of which matches `app.json` (1.0.2) or `AuthContext.js` (no fallback).
- Earlier versions of this file listed "no auth on /api/punch/* and /api/jobs": fixed by D-001. Only `GET /api/manager/schedules` lacks a role check.

## IN PROGRESS / NEXT (pick one at a time)
- [ ] Mobile UI Revamp
- Candidate quick wins, not yet scheduled (each is a small diff): B-07 (Timesheet uses `/api/dtr/summary`), B-08 (real error message on submit), B-12 (show punch errors), B-10 (`brand` field), B-02 (call `PUT /api/forms/{id}` with `is_archived`)
- Needs Architect first: group model (SmartGroup vs ScheduleGroup vs JobCategory), `manager_id` assignment, department jobs in DB, export contract (dates, format, auth), form assignment enforcement

### Recent Fixes
* **Work mode:** documentation
* **Backend:** no change
* **Web panel:** no change (earlier: rich-text editor image handles persist after insert, alignment applied manually for image targets, drag-handle widths preserved)
* **Mobile:** no change (earlier: APK now uses the production HTTPS URL from `.env.local` / `eas.json`, cleartext fallback removed)
* **Hardcodes:** none removed, new ones catalogued above
* **Docs:** this file rebuilt; API.md and DECISIONS.md drift listed above
