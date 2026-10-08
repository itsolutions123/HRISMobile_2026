# DTR App (atWork) - Project State
Last updated: October 8, 2026
Source of truth: rebuilt from the repo files pasted on this date (backend incl. web panel in `main.py`, mobile `src/`, docs, config). Commit hash not captured: run `git log --oneline -1` and add it here. docs/API.md was verified against 56c3675, docs/SECURITY.md against cff48c2.
Method: code reading only. Nothing below was run against the live server unless marked VERIFIED-RUNTIME. UNVERIFIED items need a command or doc check before anyone builds on them.

Status tags: [OK] works as written, [PARTIAL] works with gaps, [BROKEN] will fail, [MOCK] static or fake data shown as real.

## HARD RULE: FEATURE LOG
1. Every feature the user has CONFIRMED as done (said "Awesome", or pasted passing output) MUST be added to the FEATURE LOG below in the SAME commit as the code. No PROJECT_STATE.md change = no commit.
2. Each entry: ID (F-nn, next number), date, one-line description, sides touched (backend / web / mobile), evidence (file and function), confirmed by (user message or output).
3. A feature that fixes a B-xx / S-xx / H-xx item also moves that item to RESOLVED in the same commit.
4. Not confirmed = not in the log. Unconfirmed work goes under IN PROGRESS.
5. Every gem ends its response with the section 10 note and, when a feature was confirmed, the exact F-nn line to append.
6. Never delete log entries. If a feature is later removed or replaced, mark it SUPERSEDED with the date.

## FEATURE LOG (confirmed done)
F-01 to F-22 were rebuilt from code on 2026-10-07 and are tagged CODE-VERIFIED (read in code, not runtime-confirmed in this file). Entries from F-23 on need a user confirmation line.
| ID | Date | Feature | Sides | Evidence | Confirmed by |
|---|---|---|---|---|---|
| F-01 | 2026-10-07 | GPS clock in/out with Manila timestamp, duplicate-sequence and mock/range rejection, identity from token | backend, mobile | punch.py `record_punch`; DashboardScreen `submitPunch` | CODE-VERIFIED; APK confirmed working over mobile data (earlier file) |
| F-02 | 2026-10-07 | Active-shift status and live timer | backend, mobile | punch.py `get_active_punch`; HomeScreen, DashboardScreen | CODE-VERIFIED |
| F-03 | 2026-10-07 | Switch duty role during an active shift | backend, mobile | punch.py `switch_active_job`; DashboardScreen job modal | CODE-VERIFIED |
| F-04 | 2026-10-07 | Own punch history endpoint, used by Timesheet and Weekly Hours | backend, mobile | punch.py `get_my_punch_logs` | CODE-VERIFIED |
| F-05 | 2026-10-07 | Login (ID or email), register join request (PENDING), status gating, 5/min login limit | backend, mobile, web | auth.py `login`, `register_user`; LoginScreen; main.py login overlay | CODE-VERIFIED |
| F-06 | 2026-10-07 | Dynamic department list from smart groups on sign-up | backend, mobile | auth.py `get_public_departments`; LoginScreen `fetchDynamicDepartments` | CODE-VERIFIED |
| F-07 | 2026-10-07 | Admin password reset (D-007) | backend, web | auth.py `reset_user_password`; main.py `submitPasswordReset` | CODE-VERIFIED |
| F-08 | 2026-10-07 | User "Forgot password" request + admin bell/list (D-008 behaviour, DECISIONS still says PROPOSED) | backend, mobile, web | auth.py `create_reset_request`, `get_reset_requests`; LoginScreen `handlePasswordReset`; main.py `fetchResetRequests` | CODE-VERIFIED |
| F-09 | 2026-10-07 | Smart groups, brands, group admins picker | backend, web | jobs.py; main.py `saveGroupAdmins`, brand functions | CODE-VERIFIED |
| F-10 | 2026-10-07 | Department-specific jobs stored in DB (D-006), used by web chips and mobile duty roles | backend, web, mobile | jobs.py `get_group_jobs`, `update_group_jobs`; DashboardScreen `fetchJobs`; main.py `renderDepartmentJobsChips` | CODE-VERIFIED (ALTER TABLE run: UNVERIFIED) |
| F-11 | 2026-10-07 | Forms: categories, form builder, duplicate, assignment drawer, submissions, submission viewer + PDF, delete submissions (D-003) | backend, web | forms.py; main.py form functions, `deleteSelectedSubmissions`, `downloadSubmissionPDF` | CODE-VERIFIED |
| F-12 | 2026-10-07 | Forms visible to non-admins by department assignment | backend | forms.py `list_forms`, `list_categories` | CODE-VERIFIED |
| F-13 | 2026-10-07 | Mobile Forms fill + submit (text, yes/no, dropdown, checkbox, signature, description) | mobile | FormsScreen | CODE-VERIFIED |
| F-14 | 2026-10-07 | Revision requests and manager approve/reject with signature and note | backend, mobile | manager.py; TimesheetScreen, DashboardScreen, ManagerScreen | CODE-VERIFIED |
| F-15 | 2026-10-07 | Mobile Timesheet calendar, per-day punches, shift edit request | mobile | TimesheetScreen | CODE-VERIFIED |
| F-16 | 2026-10-07 | Mobile Weekly Hours screen (cut-off period list) | mobile | WeeklyHoursScreen, App.js | CODE-VERIFIED (has bugs B-24, B-31) |
| F-17 | 2026-10-07 | Web Home (attendance history + map), Time Clock live feed + history + detail map | web | main.py `loadHomeHistory`, `loadPunchMap`, `loadTimeClockHistory` | CODE-VERIFIED |
| F-18 | 2026-10-07 | Web Users & Directory: tabs, search, approve/deny/archive, profile editor | web, backend | main.py; auth.py | CODE-VERIFIED (see B-26) |
| F-19 | 2026-10-07 | DTR computation engine + summary and XLSX export endpoints | backend | dtr_engine.py; dtr.py | CODE-VERIFIED (no working client for export, see B-05) |
| F-20 | 2026-10-07 | Logout confirm modal, global styled alert (ClayAlert), pull-to-refresh and back handling | mobile | LogoutModal, GlobalAlert, ClayAlert, HomeScreen, FormsScreen | CODE-VERIFIED |
| F-21 | 2026-10-07 | Auto clock-out sweep every 30 min (D-005, backend half) | backend | main.py `auto_clock_out_task` | CODE-VERIFIED, buggy (B-22), NOT confirmed |
| F-22 | 2026-10-07 | Local clock-out reminder (D-005, mobile half) | mobile | DashboardScreen `submitPunch` | CODE-VERIFIED, test value left in (B-23), NOT confirmed |
| F-23 | 2026-10-07 | Add drag-and-drop reordering functionality to elements in the custom form builder modal | web | backend/app/main.py:handleBuilderDrop | User replied awesome to drag and drop testing |
| F-24 | 2026-10-07 | Fix mobile form date/time pickers and description image height in FormsScreen | mobile | src/screens/FormsScreen.js | Confirmed visually by user on mobile app |
| F-25 | 2026-10-08 | Updated Smart Groups UI to a claymorphism card grid layout | web | backend/app/main.py:renderConnecteamProvisioningTable | cards render and tables load on click |
| F-26 | 2026-10-08 | Adjusted PDF export layout for forms to left-align title and submitter, and added optimized company logo to the right. | backend, web | backend/app/main.py (downloadSubmissionPDF, get_logo) | verified layout on web panel |
| F-27 | 2026-10-08 | Fixed empty PDF downloads, external image CORS issues, and right edge clipping by passing raw HTML string to html2pdf. | web | backend/app/main.py:downloadSubmissionPDF | PDF successfully downloads with correct images and layout margins |
Next ID: F-28.

## Stack (confirmed, do not change without discussion)
- Backend: FastAPI (Python 3.11, Uvicorn), SQLAlchemy ORM, slowapi (login 5/min, reset-requests 3/hour), bcrypt, python-jose (HS256 JWT, 24h), openpyxl + simpleeval (XLSX export), apscheduler (BackgroundScheduler, auto clock-out)
- Mobile: React Native 0.86 / Expo SDK 57 (JavaScript), React Navigation (native-stack + bottom-tabs), expo-notifications, expo-location, expo-file-system, expo-sharing, react-native-webview, react-native-calendars. Read https://docs.expo.dev/versions/v57.0.0/ before writing mobile code (AGENTS.md).
- Web Admin: Bootstrap 5 + Leaflet + html2pdf, one HTML/JS string inside `backend/app/main.py`, served at `/admin` and `/admin/{path}`
- Database: PostgreSQL 15 (container `hris-postgres-db`). Credentials live in `backend/.env` (gitignored). Never write them in this file.
- Auth: Employee ID or email + password, `POST /api/auth/login`, JWT HS256, 24h, no refresh, no revocation. Stored roles: `Employee`, `Manager`, `Admin`, `Superadmin` (seed account `xinxaola` now holds `Superadmin`). Some code also accepts `Super Admin`.
- Employee.status values: `PENDING`, `APPROVED`, `DENIED`, `ARCHIVED`

## STRICT ARCHITECTURE & DATA DIRECTIVES
- API-first and dynamic by default. Data comes from PostgreSQL via the API. Never from literals, fallback lists or localStorage.
- Static content only for "as-is" syntax and markup scaffolding.
- Schema or contract changes are decided by the Architect Gem, not during implementation.

## Infra (fixed facts)
- Docker host: Proxmox VM `ansible-srv` (10.0.10.37), SSH user `ansibleadmin`. Repo clone: `~/HRISMobileApp` (confirm with `git rev-parse --show-toplevel`).
- Backend REST API: `http://10.0.10.37:8089` (container `hris-fastapi-backend`, compose service `hris-backend`, container port 8000). DB container has no published port.
- Mobile Metro bundler: `http://10.0.10.37:8087` (container `hris-mobile-bundler`), NOT defined in `backend/docker-compose.yml`: definition still to be located.
- SSL / reverse proxy: separate VM (10.0.10.250), nginx. Public URL: `https://app.bigtimeempire.com`
- Backend code is baked into the image (`COPY app ./app`). Always rebuild:
  `docker compose -f ~/HRISMobileApp/backend/docker-compose.yml up -d --build hris-backend`
- Check after restart: `docker logs --tail 30 hris-fastapi-backend` and `curl -s http://localhost:8089/` (expects `{"status":"online",...}`)
- Full deploy: WinSCP transfer, then `docker compose down && docker compose build --no-cache && docker compose up -d`. Never add `-v` (deletes `hris_pgdata`).
- Android APK: `eas.json` has only a `preview` APK profile (buildType apk) with `EXPO_PUBLIC_API_BASE_URL` set to the public URL. The exact build command in use is UNVERIFIED (D-002 describes a local Gradle build): confirm and record it here.
- Seed on every startup (main.py): `xinxaola` forced to Superadmin and `3286` forced to Admin, both status APPROVED (created only if missing and `INITIAL_SUPERADMIN_PASSWORD` is set). Passwords are NOT stored here.

## Repo structure (from pasted files)
- `/backend`: `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `app/`
  - `app/main.py`: app setup, CORS, scheduler, startup seed, the whole web panel (about 3,000 lines), plus dead duplicate form-submission code at the bottom
  - `app/models.py`, `database.py`, `auth_utils.py`, `dtr_engine.py`, `limiter.py`
  - `app/routers/`: `auth.py`, `punch.py`, `jobs.py`, `manager.py`, `dtr.py`, `forms.py`
- Root (mobile): `App.js`, `index.js`, `app.json` (v1.0.2, package `com.atwork`), `eas.json`, `package.json` (v1.0.0), `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `LICENSE` (Expo's template MIT licence)
- `/src/context/AuthContext.js` (token and user in React state only)
- `/src/screens/`: Login, Home, Dashboard (Time Clock), Timesheet, WeeklyHours, Forms, Profile, Manager (Admin tab)
- `/src/components/`: LogoutModal, GlobalAlert, ClayAlert
- `/docs`: `SECURITY.md`, `API.md`, `DECISIONS.md` (D-001..D-008). `DATABASE.md`, `CODE_STYLE.md`: UNVERIFIED whether they exist.
- Gem files in repo: `fullstack_gem.md`, `architect_gem.md`. Blueprint `rbac-forms-approval.md` appeared at repo root in the paste: expected location is `docs/features/` (UNVERIFIED).
- Stray files: see B-19.

## Mobile navigation (App.js)
- Not logged in: `Login` (sign in, request to join, forgot password)
- Logged in: tabs `Home`, `Forms`, `Profile`, plus `Admin` for manager/admin/superadmin (case-insensitive). Stack screens from Home: `Dashboard` (Time Clock), `Timesheet`, `WeeklyHours`.
- Deep-link prefixes hardcoded in `App.js`; Dashboard/Timesheet/WeeklyHours not in the linking config.
- Session is not persisted: closing the app logs the user out.

## API map (from router code)
Auth: Public / Token / role list. "No client" = no call site in pasted code. Details in docs/API.md.
| Method | Path | Auth | Used by |
|---|---|---|---|
| GET | /api/auth/departments | Public | Mobile Login |
| POST | /api/auth/register | Public (no rate limit) | Mobile |
| POST | /api/auth/login | Public, 5/min | Mobile, Web |
| POST | /api/auth/reset-requests | Public, 3/hour | Mobile Login |
| GET | /api/auth/admin/reset-requests | Admin, Superadmin | Web bell |
| GET | /api/auth/me | Token | Web top bar |
| GET | /api/auth/users | Admin, Manager, Superadmin | Web, (Mobile via /manager/team) |
| PUT | /api/auth/users/{id} | Admin only | Web profile editor |
| PUT | /api/auth/users/{id}/status | Admin only | Web, Mobile Admin tab |
| PUT | /api/auth/users/{id}/password | Admin, Superadmin, Super Admin (D-007 says Super Admin only) | Web |
| POST | /api/auth/users | DOES NOT EXIST | Web "Add users" (fails) |
| GET | /api/punch/active/me, /my-logs | Token | Mobile |
| POST | /api/punch | Token | Mobile Dashboard |
| PUT | /api/punch/switch-job | Token | Mobile Dashboard |
| GET | /api/punch/logs, /export | Admin, Superadmin, Manager (all employees, no scope, export ignores dates) | Web; Mobile Admin export |
| GET | /api/jobs/public | Public | none seen (Login now uses /api/auth/departments) |
| GET/POST/DELETE | /api/jobs, /api/jobs/{id} | Token / Admin, Superadmin | No client |
| GET/POST/PUT/DELETE | /api/jobs/brands | Token / Admin, Superadmin | Web |
| GET/POST/PUT/DELETE | /api/jobs/groups[/{name}] | Token / Admin, Superadmin | Web, Mobile Admin |
| GET | /api/jobs/groups/{name}/jobs | Token (404 if group name not found) | Mobile Dashboard, Timesheet; Web |
| PUT | /api/jobs/groups/{name}/jobs | Admin, Super Admin (Superadmin excluded) | Web |
| PUT | /api/jobs/groups/{name}/admins | Admin, Superadmin | Web |
| GET | /api/manager/team, /revisions | Manager, Admin | Mobile Admin |
| POST | /api/manager/revisions/request | Token | Mobile Timesheet, Dashboard |
| POST | /api/manager/revisions/{id}/action | Manager, Admin (no scope check) | Mobile Admin |
| GET | /api/manager/revisions/my-requests, /schedules; GET/POST /groups, POST /schedules | see API.md | No client |
| GET | /api/dtr/summary/{id} | Self, or Manager/Admin | Mobile Timesheet |
| GET | /api/dtr/export (XLSX) | Manager, Admin | Web sidebar (broken client) |
| /api/forms/categories..., /api/forms..., /{id}/submissions, DELETE /submissions/{id}, signatures | see API.md | Web, Mobile |
| GET | / and /admin, /admin/{path} | Public HTML shell | Browser |

## Data model (models.py)
`employees`, `job_categories`, `job_sub_items`, `punch_logs`, `schedules`, `schedule_groups`, `schedule_group_assignments`, `dtr_revisions`, `leave_requests` (no router, no UI), `form_categories`, `custom_forms`, `form_submissions`, `brand_locations`, `smart_groups` (now has `jobs` JSON text column), `password_reset_requests`, plus `custom_form_submissions` declared in `main.py` (unused, B-13).
- `smart_groups.jobs` was added by D-006: create_all does not ALTER, so the ALTER statement must have been run. UNVERIFIED: ask for `\d smart_groups` output.
- D-004 (RBAC redesign, APPROVED) is NOT implemented: no `smart_group_id`, no `smart_group_managers` table in models.py.
- Three overlapping group concepts: `SmartGroup`, `ScheduleGroup`, `JobCategory`. `Employee.department` holds a free string (now usually a SmartGroup name). Architect decision pending.
- `Employee.manager_id` exists, nothing sets it. `Employee.kiosk_code` unused (API returns `employee_id.zfill(4)`).
- `PunchLog.job_sub_item_id` never written. Job name is stored as text in `address`.
- Time: punches are naive Asia/Manila; model defaults, revisions, reset requests and the auto clock-out sweep use naive UTC; form `date_created` uses container local time. Needs a docs/DATABASE.md rule.

## Features by area (code-verified status)

### Backend
- [OK] Auth, register, login gating, admin password reset, user reset requests, user list/update/status
- [OK] Punch, my-logs, switch-job, active status
- [OK] Jobs/brands/groups, group jobs, group admins
- [OK] Manager revisions, team, schedule APIs (no UI)
- [OK] DTR engine, summary, export
- [OK] Forms CRUD, duplicate, submissions, delete submission, department visibility filter
- [PARTIAL] Auto clock-out sweep (B-22)

### Web Admin (`/admin`)
- [OK] Login overlay, JWT in localStorage (`atwork_jwt_token`), URL routing
- [OK] Home attendance history + map; Time Clock live feed, history, detail modal
- [PARTIAL] Smart Groups: brands, groups, group admins picker, jobs chips, per-group form assignment dropdown work; group rename broken (B-06); assignment drawer groups wrong (B-10)
- [PARTIAL] Users & Directory: B-01, B-26, B-27; Last login, Employment Start, Added by, Employment tab, Time off, Notes are static
- [PARTIAL] Forms: builder (Open Ended, Description, Dropdown, Yes/No, Task, Date, Signature, Location, Rating), preview, submissions table, viewer + PDF, delete. Archive actions broken or fake (B-02)
- [MOCK] Home Feed ("CELEBRATING TODAY"), sidebar Scheduling, Company policies, Settings, legacy `form-creator-view` (lorem ipsum), old `editAssignmentsModal` (fake users and counts)
- [BROKEN] Sidebar Export DTR (B-05), Add users (B-01)

### Mobile
- [OK] Login, register, forgot password (alert text B-25), logout modal
- [PARTIAL] Home: live timer, quick buttons; Feed is mock (mockFeed)
- [PARTIAL] Dashboard: GPS, WebView map, duty roles from DB, clock in/out, switch role, review modal, shift edit request. B-12, B-23, B-24, B-28, B-29
- [PARTIAL] Timesheet: calendar, punches, edit request. Job label uses `user.job_title`, which login never returns
- [PARTIAL] Weekly Hours: B-24, B-31
- [PARTIAL] Forms: B-08, B-14
- [MOCK] Profile: leave counts 0/0/0, My Submissions, Personal Information, Settings are placeholders. Logout works.
- [PARTIAL] Admin tab: Attendance (revisions) works; Users list works but approve/deny needs Admin (B-11); Smart Groups list works; Export (B-05); attendance counter is mock; archive confirm (B-25)

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
| Location, Rating | yes (no editor) | plain text fallback |
| Number, File Upload | legacy builder only | plain text fallback |

## KNOWN BROKEN / MISMATCHES
Legend: OPEN, PARTIAL, RESOLVED (kept for history), NEW (found 2026-10-07).
1. B-01 OPEN. `POST /api/auth/users` does not exist (`UserCreateRequest` unused). Web "Add users" fails and sends a hardcoded default password.
2. B-02 OPEN. Web calls `PUT /api/forms/{id}/archive` (no route). "Archive Category" and form-detail "Archive" only show a toast. Use `PUT /api/forms/{id}` with `is_archived`.
3. B-03 OPEN. `PunchRequest` requires `employee_id` (ignored). Mobile also sends full_name, department, brand_subgroup, job_title, date, timestamp: dropped. Job name travels inside `address`; clock-out overwrites it with "Shift Ended". `punch_type` not validated.
4. B-04 PARTIAL. Dashboard revision edit now sends `YYYY-MM-DD HH:MM:SS` (likely accepted). Date part comes from UTC (B-24). `attachment_note` ignored.
5. B-05 OPEN. Web export opens `/api/dtr/export` with no dates and no token. Mobile Export calls `/api/punch/export?start_date&end_date`: dates ignored, CSV of ALL logs, button says ".xlsx". ManagerScreen uses `FileSystem.documentDirectory` and `downloadAsync` from `expo-file-system`: UNVERIFIED against SDK 57 docs (legacy API may have moved to a separate import).
6. B-06 PARTIAL. Group admins picker works. Group rename still broken: `saveRenameGroup` uses undefined `setStoredGroups` and un-awaited async `getStoredGroups`, no API call. Rename API expects `new_name` and does not update `employees.department` or forms' `assigned_groups` (B-21).
7. B-07 RESOLVED 2026-10-07. Timesheet and Weekly Hours use `/api/punch/my-logs`; fixed "8.0 hrs" pill gone.
8. B-08 OPEN. Mobile Forms: on non-OK response it alerts "Form submitted (Offline mock/Sync pending)" and returns to the list, data lost. `required` not enforced. Answers keyed by label (duplicates collide).
9. B-09 RESOLVED/MOOT. Web Home rebuilt; the old clocked-in/out tables are dead code (their element ids no longer exist). Remove `renderHomeAttendanceTables`, `filterHomeAttendance` leftovers.
10. B-10 OPEN. Assignments drawer groups by `g.brand_name`; API returns `brand`: every group lands under "General".
11. B-11 OPEN. Mobile Admin tab: Manager sees approve/deny but `PUT /api/auth/users/{id}/status` is Admin-only (403). "Deny" sends `ARCHIVED`, web sends `DENIED`. Archive button is "coming soon".
12. B-12 OPEN. Dashboard `submitPunch` ignores non-OK responses: rejected duplicate or GPS error shows nothing.
13. B-13 OPEN. `main.py` bottom: `CustomFormSubmission` and duplicate `POST/GET /api/forms/{form_id}/submissions`, shadowed by the router versions (confirm via `/openapi.json`); references `CustomForm`, not imported (swallowed by bare except). Extra table `custom_form_submissions` still created.
14. B-14 OPEN. Mobile form renderer lacks Number, Location, File Upload, Rating; Date is free text.
15. B-15 OPEN. Web has no 401 handling: expired token shows empty screens.
16. B-16 OPEN. Web builds inline `onclick="...('${name}')"` from data; `.replace(/'/g, "\'")` inside the Python string is a no-op, names with an apostrophe break handlers.
17. B-17 OPEN. Scheduling has API only. `POST /api/manager/schedules` always inserts, `dtr.py` takes `.first()`: duplicates give arbitrary results.
18. B-18 OPEN. Night shifts: engine handles it, but punches are fetched per calendar day, so a next-day clock-out makes the day INCOMPLETE.
19. B-19 OPEN. Stray files committed: `PYEOF` (root, empty), a file literally named `Screen ==="` (contains a `less` help dump), plus possibly `-H`, `-d`, `backend/-H`, `backend/-d`. Re-confirm with `git ls-files`, then remove with explicit confirmation.
20. B-20 OPEN. Invalid style key `justify` in `TimesheetScreen` `pickerSelectorsRow` (should be `justifyContent`). Home and Dashboard both poll status (5s and 4s).
21. B-21 OPEN. Registration generates `EMP{count+1}`: collides after deletes or id renames. Group rename does not update `employees.department` or forms' `assigned_groups`.
22. B-22 NEW. Auto clock-out sweep (`main.py auto_clock_out_task`) compares Manila-time punches with `datetime.utcnow()` and inserts the CLOCK_OUT with a UTC timestamp. Effective cap is about 29h not 21h, and the inserted punch is 8h earlier than Manila time. D-005 said AsyncIOScheduler, code uses BackgroundScheduler. 21h and 30 min are hardcoded. Needs Architect ruling on where the cap lives.
23. B-23 NEW. Dashboard clock-in schedules the reminder with `trigger: { seconds: 10 }` (test value) and text "9hrs 30mins". It fires 10 seconds after clock-in. D-005 says 9.5h. `shouldShowAlert` handler and the trigger shape are UNVERIFIED against SDK 57 docs.
24. B-24 NEW. Mobile builds dates with `new Date().toISOString().split('T')[0]` (UTC) in Dashboard, WeeklyHours, Timesheet month range and ManagerScreen defaults. Before 08:00 Manila the date is yesterday. Web Time Clock history default has the same issue.
25. B-25 NEW. `GlobalAlert` override shows only an OK button and runs the first button that has `onPress`. Confirm dialogs lose Cancel (ManagerScreen archive runs the action on OK). `LoginScreen` passes a function as the third argument, so the callback never runs. Alert title for password reset is a long sentence.
26. B-26 NEW. Web `saveAdminUserProfileEdit` always sends `status: 'APPROVED'`: editing an archived or denied user re-approves them.
27. B-27 NEW. Web `openResetPasswordModal` reads undefined `origEmpId` when opened from a profile's Actions menu (works only from the reset-request row, which sets an implicit global).
28. B-28 NEW. `GET /api/jobs/groups/{name}/jobs` returns 404 when the user's department is not a SmartGroup name (seed users have department "Admin", group is "HO - Admin"). Mobile then has no duty roles and punches with `job_name` null ("Job: null"). `PUT .../jobs` excludes `Superadmin`, the role `xinxaola` actually has.
29. B-29 NEW. `switch-job` replaces the whole punch `address`, dropping the GPS address text.
30. B-30 NEW. `Superadmin` is rejected by `/api/dtr/*`, `/api/manager/*` and `PUT /api/jobs/groups/{name}/jobs` (role lists disagree).
31. B-31 NEW. Weekly Hours: cut-off periods (1-15 / 16-end) hardcoded, hours = first in to last out with no break, no use of `/api/dtr/summary`.
32. B-32 NEW. Renaming an employee id (`PUT /api/auth/users/{id}` with `new_employee_id`) does not cascade: `punch_logs.employee_id` has no FK and is orphaned; FKs from revisions/schedules may reject the update.
33. B-33 NEW. Mobile `user.job_title`, `user.smart_group` are read in Timesheet and Dashboard but login never returns them.

## HARDCODE BACKLOG
- Mobile
  - H-01 Deep-link prefixes in `App.js`
  - H-02 Default department 'IT Operations' in `LoginScreen`; `userDept` fallback 'HO - IT' and default map coordinates (14.5764, 121.0851) in `DashboardScreen`
  - H-03 `HomeScreen` mockFeed; `ProfileScreen` leave counts; `ManagerScreen` attendance `{clockedIn: 12, total: 45}` and `|| 45`
  - H-04 Fallback times '08:00 AM' / '05:00 PM' in Dashboard review modal; time picker minutes list `['00','15','30','45','58','20']`
  - H-05 GPS timeout 6s and Accuracy.Highest; reminder 10s / "9hrs 30mins"; Nominatim URL and User-Agent
  - H-06 Weekly Hours cut-off rule (1-15 / 16-end)
- Web (`main.py`)
  - H-07 Identity literals in markup ("Super Admin Xenon", "xinxaola", "SA"), brand 'Head Office' on history rows, fake totals ('0.5 hrs', '8.0 hrs'), "Celebrating" text, "06/05/2026 by Super Admin", "06/11/2024 - 09/18/2026" date range
  - H-08 Default new-user password literal in `saveDirectNewUser`; role `<option>`s hardcoded (no Superadmin); fake directory columns; fixed counts (151, 5, 16, 86, 15 per group)
  - H-09 RESOLVED for jobs (now DB). Remaining: `defaultBrandsInitial` / `defaultGroupsInitial` (include a real employee name)
  - H-10 Default map coordinates (14.5995, 120.9842)
  - H-11 Third-party CDN assets (jsdelivr, unpkg, Google Fonts, cdnjs)
- Backend
  - H-12 Fallback JWT secret (`auth_utils.py`) and fallback DB URL with credentials (`database.py`)
  - H-13 Grace 15, break 60, shift 08:00-17:00, `overtime_approved=False` in `dtr.py`; 21h cap and 30-min sweep in `main.py`
  - H-14 Default brands/groups seeded in `jobs.py`; "HO - " prefix stripping; `SmartGroup.selected` default "15 selected"; `creator` default "Super Admin"
  - H-15 Forms list: `views` fixed 1, `administrated_by` "+1", `created_avatar` "SA", "All users group" pseudo-group, `smart_group` fallback "HO - I.T."
  - H-16 Seed accounts in `main.py` contain real name, phone and email literals; seed category "Head Office" and four role names
  - H-17 Role and status strings scattered across routers; CORS origins in `main.py`

## SECURITY TO-DO
Numbering note: docs/SECURITY.md uses S-17..S-28 for its own findings. IDs below are the older list; SECURITY.md is authoritative for anything it covers.
- S-01 Passwords for `xinxaola`, `3286` and the DB user were stored in plaintext in earlier versions of this file (git history). Rotate all three.
- S-02 Remove fallback secrets (H-12). Fail at startup if `JWT_SECRET_KEY` or `DATABASE_URL` is missing. (SECURITY.md S-21, S-22)
- S-03 Mobile "remember password" stores plaintext password in AsyncStorage (`hris_last_password`). (SECURITY.md S-26)
- S-04 `get_current_user` does not check `status`: archived/denied users keep access until the 24h token expires.
- S-05 `verify_password` falls back to plaintext comparison. (SECURITY.md S-23)
- S-06 Any logged-in user can `GET /api/forms/{id}/submissions` and `GET /api/forms/{id}`; submit does not check the form exists, is active or assigned. Department filter exists only on list endpoints.
- S-07 Revision approval: no team scope, no PENDING-only check, self-approval allowed.
- S-08 Role checks inconsistent (Superadmin / Super Admin / SUPERADMIN). Centralize. (B-30)
- S-09 Web writes unescaped data into `innerHTML`; description HTML rendered in mobile WebView with JS on and `originWhitelist` `*`. (SECURITY.md S-28)
- S-10 `register` public with no rate limit. Login limit keyed on client address; behind nginx may be one shared bucket (UNVERIFIED, check `--proxy-headers` / `--forwarded-allow-ips`). Same for the reset-requests 3/hour limit.
- S-11 Anti-spoofing relies on `is_mock`, which mobile never sends. No geofence or accuracy threshold.
- S-12 `usesCleartextTraffic: true` in `app.json`; APK uses HTTPS, probably removable.
- S-13 No pagination or size limits on logs, summary, export; base64 signatures unbounded.
- S-14 Startup seed re-approves and re-promotes both seed accounts on every boot, undoing an archive.
- S-15 Web token in localStorage; no CSP; only one CDN script has SRI.
- S-16 `requirements.txt` unpinned, lists `pip`/`setuptools`/`passlib` (unused); container runs as root; no healthcheck.
- S-17 `PUT /api/auth/users/{id}/password` allows `Admin` as well, while D-007 and API.md say Super Admin only. Admin can reset another Admin's password. Also reveals "already used this password".
- S-18 Reset request match is an exact string compare of `mobile_phone`; format differences silently fail (generic reply hides it).
- S-19 Admin can set any role (including Admin) on any user via `PUT /api/auth/users/{id}`; no hierarchy rule (D-004 not implemented).

## DOC DRIFT (fix in the same commit as the related change)
- `docs/DECISIONS.md`: D-002 says package `com.bigtime.hrismobileapp.test`, version 1.0.0, default URL fallback: code has `com.atwork`, 1.0.2, no fallback, and uses `is_active` (does not exist). D-006 contract paths (`/api/smart_groups/{id}/jobs`) differ from code (`/api/jobs/groups/{name}/jobs`). D-008 is PROPOSED but implemented, and path differs (`/api/admin/reset-requests` vs `/api/auth/admin/reset-requests`). D-005 says AsyncIOScheduler, code uses BackgroundScheduler and a 10s test trigger.
- `docs/DECISIONS.md` D-004 (APPROVED: `employees.smart_group_id`, `smart_group_managers`, rename Employee to Basic) conflicts with `rbac-forms-approval.md` (new tables `smart_group_members`, `smart_group_managers`, `form_group_assignments`, `form_approvers`; keeps `Employee`; blueprint calls itself D-003 PROPOSED). Architect must reconcile before any RBAC work.
- `docs/API.md`: API-04 (reset poll token key) now fixed in code; API-08 (mobile reads `description`/`color`/`icon`) still open; list new endpoints `/api/punch/my-logs`, `/switch-job`, `/api/jobs/groups/{name}/jobs`.
- `docs/SECURITY.md`: add S-17..S-19 of this file; mark G-gates unchanged.
- `package.json` version 1.0.0 vs `app.json` 1.0.2.
- DATABASE.md and CODE_STYLE.md: not seen; record time-zone rule and the `smart_groups.jobs` ALTER in DATABASE.md.

## IN PROGRESS / NEXT (pick one at a time)
- [ ] Mobile UI Revamp
- Quick wins (each a small diff): B-23 (replace test trigger, needs Architect value for 9.5h), B-22 (UTC vs Manila), B-26, B-27, B-24, B-12, B-08, B-10, B-02, B-33, B-19 cleanup
- Needs Architect first: D-004 vs blueprint reconciliation, group model (SmartGroup / ScheduleGroup / JobCategory), where the 21h and 9.5h limits live, export contract (dates, format, auth), form assignment enforcement, role naming
- Needs runtime check: `\d smart_groups` (jobs column), `/openapi.json` route order (B-13), proxy headers (S-10), expo-file-system API (B-05), notification API (B-23)

### Recent Fixes
* Work mode: documentation
* Backend / web panel / mobile: no change in this commit
* Hardcodes: none removed, new ones catalogued above
* Docs: this file rebuilt (adds HARD RULE and FEATURE LOG); doc drift listed above
