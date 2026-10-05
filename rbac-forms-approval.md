# Feature Blueprint: RBAC rework and per-smart-group form approval
Decision: D-003 (PROPOSED)
Date: 2026-10-02
Owner gem: Architect
Status: PROPOSED. Nothing here is final until the user says "Approved".
Evidence base: repo code pasted 2026-10-02 (routers, models, main.py web panel, mobile src). Commit hash not captured. Code reading only, not runtime.

## 0. Open decisions (defaults apply if you do not answer)
| ID | Question | Default used in this blueprint |
|---|---|---|
| OD-1 | The diagram says Admin "can only be assigned by Super Admin" AND "can make other user Admin". These conflict. | Only Super Admin can grant or revoke Admin and Super Admin. Admin can assign Manager and Basic only. |
| OD-2 | Which accounts become Super Admin? The seed forces every seeded account to Admin today, so nobody holds Superadmin. | Only `xinxaola`. `3286` stays Admin. |
| OD-3 | Can Admin approve or deny any form submission (override), even outside a group? The diagram is silent. | Yes, recorded in `decided_by`. |
| OD-4 | Approver rule: all managers of the submitter's smart group, or only managers assigned to that form? | Both layers: manager must manage the submission's group AND (the form has no approver list OR the manager is on it). |
| OD-5 | Can an employee belong to several smart groups? | Yes. If a form matches several of their groups, the user picks one at submit time. |
| OD-6 | The diagram says Manager "can edit assigned modules based on smart group". What does "edit" cover? | Nothing beyond viewing and deciding for their groups: DTR, time clock, DTR revisions, form submissions. Managers cannot edit forms, groups or users. |
| OD-7 | Do Managers get the web panel and the mobile Admin tab? | Yes, both, with server-scoped content. Basic (Employee) gets mobile only. |
| OD-8 | Where does the role-to-capability map live? | One backend module (code), exposed through `/api/auth/me`. A DB-editable permission table is overkill for 4 fixed roles. |
| OD-9 | Can a manager decide their own submission? | No. Another manager of the group or an Admin decides. |
| OD-10 | Is a note required when denying? | Yes. |

## 1. Goal and users
Make roles mean the same thing in the database, the API, the web panel and the mobile app. Add smart-group membership and smart-group managers as real data, so that managers only see and decide what belongs to their groups. Use that to add form approval: a form is applied to smart groups, an employee submits it from mobile, and the managers of that employee's group approve or deny it.
- Basic (stored as `Employee`): clock in/out, timesheet, submit forms, see own submissions. Mobile only.
- Manager: sees time clock, DTR, DTR revisions and form submissions for the groups they manage. Approves or denies form submissions.
- Admin: manages Manager and Basic users, smart groups, brands, form categories and forms. Mobile Admin module.
- Super Admin: everything, including granting Admin.

## 2. Reuse check (what exists today, file and function)
- Roles are plain strings on `Employee.role`: `Employee`, `Manager`, `Admin` (`Superadmin` accepted in some routers, never assigned). Checks are scattered: `require_roles([...])` in `punch.py`/`auth.py`, inline `current_user.role not in [...]` in `jobs.py`, `forms.py`, `dtr.py`, and `verify_manager_or_admin` in `manager.py`. They disagree on whether Superadmin counts.
- Scope today: `GET /api/manager/team` and `/revisions` use `Employee.manager_id` OR `department` string equality. `GET /api/dtr/summary/{id}` lets ANY Manager read ANY employee. `GET /api/punch/logs` returns every employee's punches to any Manager. `POST /api/manager/revisions/{id}/action` has no scope check. (`manager.py`, `dtr.py`, `punch.py`)
- `PUT /api/auth/users/{emp_id}` and `/status` are Admin-only, but an Admin can set any role (including Admin) and edit other Admins.
- `get_current_user` (`auth_utils.py`) does not check `Employee.status`.
- Seed (`main.py`): forces `xinxaola` and `3286` to role Admin and status APPROVED on every startup.
- Smart groups exist (`smart_groups`, `brand_locations`). Managers of a group are stored as a JSON string in `SmartGroup.admins`; the endpoint `PUT /api/jobs/groups/{name}/admins` exists but no client calls it. Membership does not exist: `Employee.department` is a free string matched by name.
- Forms: `custom_forms.assigned_groups` is a comma-joined string of group names ("All users group" is a pseudo-group). `GET /api/forms` ignores it. `form_submissions.submitted_by` stores the display name, not the employee id; `status` is the fixed string "Submitted"; `smart_group` is a name taken from the client body.
- Any logged-in user can `GET /api/forms/{id}/submissions` (all answers and signatures).
- Reused as-is: `smart_groups`, `brand_locations`, `custom_forms`, `form_submissions`, `dtr_revisions`, the `PENDING/APPROVED/DENIED/ARCHIVED` user statuses, the existing revision approval screens.
- Not used by this design: `Employee.manager_id` (never settable from any UI), `ScheduleGroup` (scheduling has no UI; out of scope).

## 3. Role model

### 3.1 Stored role values (no data migration needed)
`Employee` (shown as "Basic"), `Manager`, `Admin`, `Superadmin` (shown as "Super Admin"). Rank: Employee 10, Manager 20, Admin 30, Superadmin 40. All role strings are defined once in a backend permissions module (see 8) and used everywhere.

### 3.2 Hierarchy rules (server-enforced)
1. An actor may edit, archive, un-archive or change the role of a user only if the actor's rank is higher than the target's rank. Super Admin may also act on other Super Admins, but never on themselves for role or status (prevents locking out the last Super Admin).
2. Assignable roles: Admin may assign Employee and Manager. Super Admin may assign all four (OD-1).
3. A user whose status is not `APPROVED` is rejected on every endpoint, not only at login (today an archived user keeps working until the 24h JWT expires).
4. Group manager assignment requires the target to hold role Manager or higher. Assigning a group manager does not change a role automatically.

### 3.3 Capabilities returned by the API
`GET /api/auth/me` and the login response gain: `capabilities` (list of strings), `assignable_roles` (list), `smart_groups` ([{id, name}]), `managed_group_ids` ([int]). Clients show or hide screens from these lists. Servers still enforce everything.

| Capability | Basic (Employee) | Manager | Admin | Super Admin |
|---|---|---|---|---|
| (always) clock in/out, active status, own timesheet, submit assigned forms, own submissions | yes | yes | yes | yes |
| `web_panel` (may use /admin) | no | yes | yes | yes |
| `admin_module` (mobile Admin tab) | no | yes (manager view) | yes | yes |
| `view_team_dtr` (time clock, DTR summary) | no | own groups | all | all |
| `review_revisions` (DTR edit requests) | no | own groups | all | all |
| `review_forms` (view, approve, deny submissions) | no | own groups + assigned forms | all (override, OD-3) | all |
| `export_dtr` | no | own groups | all | all |
| `manage_users` (edit, archive, approve sign-up) | no | no | lower ranks only | all |
| `manage_groups` (brands, smart groups, members, managers) | no | no | yes | yes |
| `manage_forms` (categories, forms, assignments, approvers) | no | no | yes | yes |
| Assign Employee / Manager | no | no | yes | yes |
| Assign Admin / Super Admin | no | no | no (OD-1) | yes |

"own groups" means smart groups where the actor is in `smart_group_managers`. "all" means unrestricted. Scheduling endpoints are out of scope and unchanged.

## 4. Data model

### 4.1 New tables (created automatically by `create_all` on the next backend start)
All FKs to `employees.employee_id` use `ON UPDATE CASCADE` so an employee id rename does not orphan rows.

| Table | Columns | Constraints |
|---|---|---|
| `smart_group_members` | id PK, group_id FK smart_groups.id ON DELETE CASCADE, employee_id FK employees.employee_id, created_at | UNIQUE(group_id, employee_id); index on employee_id |
| `smart_group_managers` | id PK, group_id FK smart_groups.id ON DELETE CASCADE, employee_id FK employees.employee_id, created_at | UNIQUE(group_id, employee_id); index on employee_id |
| `form_group_assignments` | id PK, form_id FK custom_forms.id ON DELETE CASCADE, group_id FK smart_groups.id ON DELETE CASCADE | UNIQUE(form_id, group_id) |
| `form_approvers` | id PK, form_id FK custom_forms.id ON DELETE CASCADE, employee_id FK employees.employee_id | UNIQUE(form_id, employee_id) |

### 4.2 Changed tables (need ALTER, `create_all` will not do it)
| Table | New column | Type / default | Purpose |
|---|---|---|---|
| `custom_forms` | `requires_approval` | BOOLEAN NOT NULL DEFAULT FALSE | Submissions start as PENDING |
| `custom_forms` | `assign_all` | BOOLEAN NOT NULL DEFAULT FALSE | Replaces the "All users group" pseudo-group |
| `form_submissions` | `submitted_by_employee_id` | VARCHAR NULL, FK employees ON UPDATE CASCADE | Real submitter (legacy rows only have a name) |
| `form_submissions` | `smart_group_id` | INTEGER NULL, FK smart_groups ON DELETE SET NULL | Group whose managers decide |
| `form_submissions` | `decided_by` | VARCHAR NULL, FK employees ON UPDATE CASCADE | Who decided |
| `form_submissions` | `decided_at` | TIMESTAMP NULL | When (naive Asia/Manila like punches: ASSUMPTION, confirm against docs/DATABASE.md) |
| `form_submissions` | `decision_note` | VARCHAR NULL | Reason, required when DENIED |

Kept but deprecated (do not drop in this decision): `smart_groups.admins` (replaced by `smart_group_managers`), `custom_forms.assigned_groups` (replaced by `form_group_assignments` + `assign_all`), `Employee.manager_id` (unused), `form_submissions.smart_group` and `submitted_by` (kept as display snapshots, they survive renames).
`Employee.department` stays for registration and for the duty-role lookup on the mobile Dashboard. It is NOT used for access control any more. Keeping both in step is a known drift risk until the group model decision for duty roles is made.

### 4.3 Status values (single list, exact strings)
- Form submission: `SUBMITTED` (form needs no approval, final), `PENDING`, `APPROVED`, `DENIED`. The legacy value `Submitted` is migrated to `SUBMITTED`.
- Transitions: `PENDING` to `APPROVED` or `DENIED` once. A decided submission cannot be decided again (409).
- Note on naming: user status uses `DENIED`, DTR revisions use `REJECTED`. This decision uses `DENIED` for forms; unifying revisions is out of scope.

### 4.4 Migration (run in this order)
1. Backup (shell): `docker exec hris-postgres-db pg_dump -U hrisuser hrisdb > ~/backup_$(date +%F_%H%M).sql`
2. ALTER (run BEFORE deploying the new models, otherwise form queries fail):
```
ALTER TABLE custom_forms ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE custom_forms ADD COLUMN IF NOT EXISTS assign_all BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE form_submissions ADD COLUMN IF NOT EXISTS submitted_by_employee_id VARCHAR REFERENCES employees(employee_id) ON UPDATE CASCADE;
ALTER TABLE form_submissions ADD COLUMN IF NOT EXISTS smart_group_id INTEGER REFERENCES smart_groups(id) ON DELETE SET NULL;
ALTER TABLE form_submissions ADD COLUMN IF NOT EXISTS decided_by VARCHAR REFERENCES employees(employee_id) ON UPDATE CASCADE;
ALTER TABLE form_submissions ADD COLUMN IF NOT EXISTS decided_at TIMESTAMP;
ALTER TABLE form_submissions ADD COLUMN IF NOT EXISTS decision_note VARCHAR;
CREATE INDEX IF NOT EXISTS ix_form_submissions_status ON form_submissions(status);
CREATE INDEX IF NOT EXISTS ix_form_submissions_group ON form_submissions(smart_group_id);
CREATE INDEX IF NOT EXISTS ix_form_submissions_submitter ON form_submissions(submitted_by_employee_id);
```
3. Deploy the new backend (restart command from the preamble). This creates the four new tables.
4. Dry-run checks (read-only), then show the output to the user BEFORE any backfill:
```
-- employees whose department matches zero or several smart groups
SELECT e.employee_id, e.department, count(sg.id) AS matches
FROM employees e LEFT JOIN smart_groups sg ON (sg.name = e.department OR sg.dept = e.department)
GROUP BY e.employee_id, e.department HAVING count(sg.id) <> 1;
-- group names inside forms that match no smart group
SELECT cf.id, n AS unmatched_name
FROM custom_forms cf CROSS JOIN LATERAL unnest(string_to_array(cf.assigned_groups, ',')) AS n
WHERE n <> 'All users group' AND NOT EXISTS (SELECT 1 FROM smart_groups sg WHERE sg.name = n);
-- manager ids in SmartGroup.admins that are not valid JSON or not employees: if the cast below errors, fix that row first
SELECT id, name, admins FROM smart_groups WHERE admins IS NOT NULL AND admins NOT IN ('', '[]');
```
5. Backfill (only after the user has reviewed step 4; unmatched rows are fixed by an Admin in the web panel, never guessed):
```
INSERT INTO smart_group_members (group_id, employee_id)
SELECT sg.id, e.employee_id FROM employees e
JOIN smart_groups sg ON (sg.name = e.department OR sg.dept = e.department)
ON CONFLICT DO NOTHING;

INSERT INTO smart_group_managers (group_id, employee_id)
SELECT sg.id, a.val FROM smart_groups sg
CROSS JOIN LATERAL jsonb_array_elements_text(CASE WHEN sg.admins IS NULL OR sg.admins = '' THEN '[]'::jsonb ELSE sg.admins::jsonb END) AS a(val)
WHERE EXISTS (SELECT 1 FROM employees e WHERE e.employee_id = a.val)
ON CONFLICT DO NOTHING;

UPDATE custom_forms SET assign_all = TRUE
WHERE assigned_groups IS NULL OR assigned_groups = '' OR assigned_groups LIKE '%All users group%';

INSERT INTO form_group_assignments (form_id, group_id)
SELECT cf.id, sg.id FROM custom_forms cf
JOIN smart_groups sg ON sg.name = ANY(string_to_array(cf.assigned_groups, ','))
ON CONFLICT DO NOTHING;

UPDATE form_submissions fs SET submitted_by_employee_id = e.employee_id FROM employees e
WHERE fs.submitted_by_employee_id IS NULL AND e.name = fs.submitted_by
  AND (SELECT count(*) FROM employees x WHERE x.name = fs.submitted_by) = 1;
UPDATE form_submissions fs SET smart_group_id = sg.id FROM smart_groups sg
WHERE fs.smart_group_id IS NULL AND sg.name = fs.smart_group;
UPDATE form_submissions SET status = 'SUBMITTED' WHERE status = 'Submitted';
```
6. Super Admin (after OD-2 is answered): `UPDATE employees SET role = 'Superadmin' WHERE employee_id IN ('<confirmed ids>');`
7. Remove the seed's forced `role = "Admin"` / `status = "APPROVED"` update in `main.py` (create only if missing). Otherwise step 6 is undone at the next restart.
Rollback: restore the backup from step 1. New tables and columns are additive, so old code keeps working if the ALTERs are left in place.

## 5. API contract
Conventions: new endpoints use snake_case keys. Extended response objects keep their existing camelCase and add keys in the same style (marked "camel"). New list endpoints return `{"items": [...], "total": N, "limit": N, "offset": N}` with `limit` default 50, max 200. Errors are `{"detail": "<message>"}`. Auth is the Bearer token on every endpoint below.

### 5.1 Identity and users
| Method | Path | Roles | Change |
|---|---|---|---|
| POST | /api/auth/login | public (5/min) | Response `user` gains `capabilities`, `assignable_roles`, `smart_groups`, `managed_group_ids` (additive) |
| GET | /api/auth/me | any active user | Same four additive keys |
| (all) | every authenticated endpoint | | `status != APPROVED` is rejected with 401 `{"detail":"Account is not active"}` |
| GET | /api/auth/users | manage_users or manager scope | Manager: only members of managed groups. Admin/Super Admin: all. Optional `smart_group_id` filter |
| PUT | /api/auth/users/{emp_id} | manage_users | 403 if target rank >= actor rank (Super Admin exception, 3.2). 403 if `role` not in actor's `assignable_roles`. 403 if actor edits own role or status |
| PUT | /api/auth/users/{emp_id}/status | manage_users | Same hierarchy rules |

### 5.2 Smart groups
| Method | Path | Roles | Request / response |
|---|---|---|---|
| GET | /api/jobs/groups | any active user | Additive: `member_count`, `manager_ids`. Existing `admins` is kept and filled from `smart_group_managers` |
| GET | /api/jobs/groups/{group_id}/members | manage_groups; Manager for own groups | `[{"employee_id","name","position","role","status"}]` |
| PUT | /api/jobs/groups/{group_id}/members | manage_groups | Body `{"employee_ids":["..."]}` replaces the member set. Response `{"status":"success","member_count":N}`. 422 listing unknown ids |
| PUT | /api/jobs/groups/{group_id}/managers | manage_groups | Body `{"employee_ids":["..."]}` replaces the manager set. Each id must hold role Manager or higher (422 otherwise). Response `{"status":"success","manager_ids":[...]}` |
| PUT | /api/jobs/groups/{group_name}/admins | manage_groups | Existing endpoint, deprecated: now writes `smart_group_managers` |

### 5.3 Form definitions
| Method | Path | Roles | Change |
|---|---|---|---|
| GET | /api/forms | any active user | Employee: only forms where `assign_all` or one of the user's groups is assigned, not archived. Manager: forms assigned to their own or managed groups. Admin/Super Admin: all. Camel additive keys `requiresApproval`, `assignAll`, `assignedGroupIds`, `approverIds`. Existing `assignedGroups` (names) kept |
| GET | /api/forms/{id} | any active user | Same visibility; not visible returns 404. Additive snake keys `requires_approval`, `assign_all`, `assigned_group_ids`, `approver_ids` |
| POST, PUT | /api/forms, /api/forms/{id} | manage_forms | Body additive: `requires_approval` (bool), `assign_all` (bool), `assigned_group_ids` ([int]), `approver_ids` ([employee_id]; each must be Manager or higher). Old `assigned_groups` (names) is still accepted and mapped; "All users group" sets `assign_all`; unknown name returns 422. Response gains `warnings` (list of strings, for example a group with no managers while `requires_approval` is true) |

### 5.4 Submissions and approval
Static routes (`/submissions/mine`, `/submissions/pending-approval`) are declared before `/submissions/{submission_id}`.

| Method | Path | Roles | Behaviour |
|---|---|---|---|
| POST | /api/forms/{form_id}/submissions | any active user | Body `{"form_data":[{"label","value"}], "smart_group_id": <int, optional>}` (old `smart_group` string accepted and ignored). Server checks form exists, is not archived and is visible to the user (else 403 "This form is not assigned to you"). Group = intersection of user's groups and the form's groups (all of the user's groups if `assign_all`). One match: used. Several: `smart_group_id` required (422) and must be in the intersection. None while `requires_approval`: 403 "You are not in any smart group". Status = `PENDING` if `requires_approval` else `SUBMITTED`. Submitter comes from the Bearer token. Response `{"status":"success","id":123,"submission_status":"PENDING"}` |
| GET | /api/forms/{form_id}/submissions | review_forms | Employee: 403. Manager: only rows in managed groups where the manager is an approver of the form (OD-4). Admin/Super Admin: all. Optional `status`, `smart_group_id`, `limit`, `offset`. Existing camel keys kept (`id`, `submittedBy`, `dateTime`, `smartGroup`, `status`, `formData`); added `submittedById`, `smartGroupId`, `decidedBy`, `decidedAt`, `decisionNote`. Returns a bare array for web compatibility (legacy shape kept, paging params optional) |
| GET | /api/forms/submissions/mine | any active user | Own submissions across forms: `{"items":[{"id","form_id","form_name","status","smart_group","submitted_at","decided_at","decision_note"}],...}` |
| GET | /api/forms/submissions/pending-approval | review_forms | Queue for the actor (same scope rule), status PENDING, newest first, paged envelope. Items are summaries without `form_data` |
| GET | /api/forms/submissions/{submission_id} | submitter, or review_forms in scope | Full record with `form_data` and the form's `schema_fields` so a client can render the answers |
| POST | /api/forms/submissions/{submission_id}/decision | review_forms | Body `{"decision":"APPROVED"|"DENIED","note":"..."}`. Rules below. Response `{"status":"success","submission_status":"APPROVED","decided_by":"<id>","decided_at":"<ISO 8601>"}` |

Decision rules, in this order: 404 if the submission is not found or not visible to the actor; 403 if the actor is the submitter (OD-9); 403 if the actor is not an eligible approver (Manager of `smart_group_id`, and on the form's approver list when that list is not empty, or Admin/Super Admin by OD-3); 409 "Already decided" unless status is `PENDING`; 422 if `decision` is invalid or `note` is empty when `DENIED` (OD-10). The update is a single guarded write (status must still be `PENDING`) so two managers cannot both decide.

### 5.5 Existing endpoints that change scope only (no shape change)
| Endpoint | New rule |
|---|---|
| GET /api/manager/team | Manager: members of managed groups. Admin/Super Admin: all |
| GET /api/manager/revisions | Same scope |
| POST /api/manager/revisions/{id}/action | 403 if the revision's employee is outside the actor's scope; 409 if not `PENDING`; 403 on own request |
| GET /api/dtr/summary/{employee_id} | Self, or `view_team_dtr` with the employee in scope |
| GET /api/dtr/export | Manager: only employees in managed groups |
| GET /api/punch/logs, /api/punch/export | Manager: only employees in managed groups |

## 6. Connection matrix (web, mobile, API, database)
| # | User action | Web panel | Mobile app | Endpoint | Table.column |
|---|---|---|---|---|---|
| 1 | Admin adds members to a smart group | Smart Groups drawer: members table with add/remove picker (replaces the localStorage and undefined helper code) | Admin > Smart Groups: read-only member count | PUT /api/jobs/groups/{id}/members | smart_group_members |
| 2 | Admin assigns group managers | Same drawer: manager picker (only users with role Manager+) | Admin > Smart Groups: read-only manager count | PUT /api/jobs/groups/{id}/managers | smart_group_managers |
| 3 | Admin applies a form to groups and sets approval | Form detail > Settings > Edit assignments drawer: group checkboxes, "All users", "Requires approval", approver picker | n/a (admin config is web-only) | PUT /api/forms/{id} | form_group_assignments, custom_forms.assign_all/requires_approval, form_approvers |
| 4 | Employee opens the form list | n/a (Basic users have no web access) | Forms tab | GET /api/forms | custom_forms + assignments |
| 5 | Employee submits a form | n/a | Forms > fill > Submit; group picker only when several groups match; shows "Submitted" or "Pending approval"; shows the server error instead of a fake success | POST /api/forms/{id}/submissions | form_submissions.* |
| 6 | Employee checks status | n/a | Profile > My Submissions | GET /api/forms/submissions/mine | form_submissions.status/decision_note |
| 7 | Manager sees what to review | Forms > form > Submissions, filter "Pending" | Admin tab > Form Approvals (pull to refresh, count from `total`) | GET /api/forms/submissions/pending-approval and GET /api/forms/{id}/submissions | form_submissions |
| 8 | Manager approves or denies | Submission viewer: Approve / Deny buttons, note box | Approval detail screen: Approve / Deny, note box | POST /api/forms/submissions/{id}/decision | form_submissions.status/decided_by/decided_at/decision_note |
| 9 | Manager sees group time clock and DTR | Time Clock page and history (server-scoped, no client filtering) | Admin > Attendance, Team (server-scoped) | GET /api/punch/logs, /api/manager/team, /api/dtr/summary | punch_logs, employees, smart_group_members |
| 10 | Admin changes a user's role | Profile editor: role list comes from `assignable_roles` (no hardcoded options) | n/a | PUT /api/auth/users/{id} | employees.role |
| 11 | Login gating | After login, no `web_panel` capability means refuse with a message; sidebar items follow `capabilities` | Admin tab visible only with `admin_module`; content follows `capabilities` | POST /api/auth/login, GET /api/auth/me | employees.role/status |

## 7. Sync and state rules
- Source of truth: PostgreSQL through the API. The role-to-capability map exists in one backend module only. Clients never compute permissions from the role string.
- Refresh: mobile lists (Forms, My Submissions, Form Approvals, Attendance) refetch on screen focus and on pull-to-refresh. Web tables refetch after every write and on tab open. No polling for this feature, no push, no websocket.
- Conflict: first valid write wins. A second approver gets 409 "Already decided" and the client refetches and shows the current state.
- Group snapshot: `smart_group_id` is fixed at submit time. If the employee later moves to another group, the original group's managers still decide that submission. Deleting a group sets it to NULL; such rows are decided by Admin/Super Admin only.
- Offline: mobile shows an error and keeps the form values on screen. It never reports success when the request failed (this fixes the current "Offline mock/Sync pending" alert).
- Role names shown in the UI: stored value `Employee` is displayed as "Basic" where the diagram's label is wanted; the label mapping is presentation only.

## 8. Backend structure (what Full-Stack builds, no code here)
- One new module `backend/app/permissions.py` owns: the role constants and ranks, the capability map, `require_capability(...)` dependencies, helpers `managed_group_ids(user)`, `scope_employee_ids(user)`, `can_manage_user(actor, target)`, `can_decide(actor, submission)`. All routers import from it. Inline role lists in routers are removed as each router is touched.
- `get_current_user` gains the `status == APPROVED` check.
- Seed in `main.py`: create the accounts only if missing and stop re-forcing role and status. Real names, phone and email literals in the seed move to env vars or are removed (separate hardcode item H-16).
- Forms router keeps its own `get_db` duplicate for now (style item for the Code Style Gem).

## 9. Security and privacy
- Closes: S-04 (inactive users keep access), S-06 (anyone can read all submissions, no assignment check), S-07 (revision approval scope and self-approval), S-08 (inconsistent role checks), and the "any Manager reads any employee's DTR" gap.
- Group membership now controls access, so only Admin/Super Admin may edit membership and managers (capability `manage_groups`).
- Not covered, residual risk: there is no audit table for role or membership changes (only `decided_by` on submissions). Recommend a separate decision.
- Not covered: `register` has no rate limit; JWT lifetime and revocation; base64 signatures stored in form data. Tracked in PROJECT_STATE (S-10, S-13).
- Hand to the Security Gem for review before implementation.

## 10. Release impact and old APK behaviour
- Backend and web panel: restart with `docker compose -f ~/HRISMobileApp/backend/docker-compose.yml up -d --build hris-backend`.
- Mobile: new APK build for My Submissions, Form Approvals, group picker and capability-driven tabs. Whether OTA updates exist is UNVERIFIED (`eas.json` has only a preview build profile).
- Old APK, all additive: login/me responses only gain keys. Admin tab still appears for role strings manager/admin/superadmin. Form list shows only forms assigned to the user. Submit works for users who match exactly one group, or when the form needs no approval (the old body field `smart_group` is ignored). Users with several matching groups get a 422 until they update. Old APK shows no approval status and no manager approval screen. Managers see scoped Team/Attendance data.

## 11. Acceptance tests
Setup: six test accounts created through the admin panel (no credentials in docs): E1 (Basic, member of G1), E2 (Basic, member of G2 only), M1 (Manager of G1), M2 (Manager of G2), A1 (Admin), S1 (Super Admin). One form F1 with `requires_approval` on, assigned to G1. Use the hidden-password token helper from the preamble for each actor.

| # | Actor and call | Expected |
|---|---|---|
| T1 | E1 GET /api/forms | F1 listed |
| T2 | E2 GET /api/forms/{F1} | 404 |
| T3 | E2 POST /api/forms/{F1}/submissions | 403 "not assigned" |
| T4 | E1 POST /api/forms/{F1}/submissions | 200, `submission_status` PENDING |
| T5 | E1 GET /api/forms/{F1}/submissions | 403 |
| T6 | M2 GET /api/forms/submissions/pending-approval | E1's submission absent |
| T7 | M2 POST /api/forms/submissions/{id}/decision | 403 |
| T8 | M1 POST decision DENIED with empty note | 422 |
| T9 | M1 POST decision APPROVED | 200; second call 409 |
| T10 | E1 GET /api/forms/submissions/mine | status APPROVED, decided_at set |
| T11 | M1 submits a form and POST decision on own submission | 403 |
| T12 | A1 PUT /api/auth/users/{E1} with role Admin | 403; S1 same call 200 |
| T13 | A1 PUT /api/auth/users/{S1} | 403 |
| T14 | A1 PUT /api/auth/users/{M1}/status ARCHIVED, then M1's old token on GET /api/auth/me | 401 "Account is not active" |
| T15 | M1 GET /api/dtr/summary/{E2} | 403; the same call for E1 returns 200 |
| T16 | M1 GET /api/punch/logs | only G1 members' punches |
| T17 | Old-style body (`smart_group` string, no `smart_group_id`) from E1 | 200 (single-group user) |
| T18 | E1 logs in on the web panel | refused with a message |
| Web | A1: open Smart Groups, add E1 as member of G1 and M1 as manager; open F1 settings, tick G1, "Requires approval"; reload the page | values persist |
| Mobile | E1: Forms > F1 > Submit, then Profile > My Submissions shows Pending; M1: Admin > Form Approvals > open > Approve; E1 pull-to-refresh shows Approved | works end to end |

## 12. Implementation order for the Full-Stack Gem (one step per message, verify after each)
1. Backup and ALTER (section 4.4 steps 1 and 2), user confirms the output.
2. Backend: models, `permissions.py`, `/me` and login additions, status check, seed change. Verify with curl as E1, M1, A1.
3. Backend: scope the existing endpoints (5.1 users, 5.5). Verify T12 to T16.
4. Backend: group members/managers endpoints, then migration steps 3 to 6 with the dry-run reviewed. Verify the counts match.
5. Backend: form definition changes (5.3) and submission/approval endpoints (5.4). Verify T1 to T11, T17.
6. Web: Smart Groups drawer (members and managers), replacing the broken helpers (B-06).
7. Web: form settings drawer (groups, requires approval, approvers), fixing B-10.
8. Web: submissions table with status, filter and Approve/Deny; sidebar and login gating from `capabilities`; role list from `assignable_roles`.
9. Mobile: AuthContext stores `capabilities` and `smart_groups`; tabs follow `capabilities`.
10. Mobile: submit flow (group picker, real errors) and Profile > My Submissions.
11. Mobile: Admin > Form Approvals and approval detail.
12. Architect SYNC AUDIT, then the doc handoffs.

## 13. Docs to update
- docs/API.md (API Gem): section 5, including the capabilities keys and the paged envelope.
- docs/DATABASE.md (Database Gem): section 4, plus the time-zone rule for `decided_at`.
- docs/SECURITY.md (Security Gem): section 3 role matrix, hierarchy rules, scope rules.
- PROJECT_STATE.md: close S-04, S-06, S-07, S-08 and B-10, B-06 when shipped; add the new tables.
