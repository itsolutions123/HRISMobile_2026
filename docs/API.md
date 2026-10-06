# API Contract

Last verified: 2026-10-07 against commit 56c3675 (code read; not runtime-tested)
Owner: API Gem

## Rules
1. MUST: every endpoint requires `Authorization: Bearer <JWT>` unless listed under Public. Check: `grep -n "Depends(get_current_user)\|require_roles" backend/app/routers/*.py`.
2. MUST: acting user comes from the token, never the request body.
3. MUST: update this file in the SAME commit as any endpoint or call-site change (preamble 12.3). Check: `git diff --stat -- docs/API.md`.
4. MUST: record contract changes here BEFORE implementing (Architect decides, API Gem records).
5. MUST NOT: clients call a path not listed here. Check: `grep -rn "/api/" src backend/app/main.py`.
6. SHOULD: new endpoints use snake_case JSON and ISO 8601 times.
7. MUST: role strings are exactly as stored: `Employee`, `Manager`, `Admin`, `Superadmin`. Do not invent others.

## Base URLs
- Web panel: relative paths (served by the backend at `/admin`). Token key in localStorage: `atwork_jwt_token`.
- Mobile: `process.env.EXPO_PUBLIC_API_BASE_URL` (via `AuthContext` as `API_BASE_URL`); token from `AuthContext`.
- Backend container: port 8000, published on host 8089. TLS is terminated by the nginx VM.

## Conventions
- Errors: HTTP status + `{"detail": "<message>"}` (422 validation returns a list in `detail`).
- Times: server writes naive Asia/Manila local time for punches. Formats differ per endpoint, see Notes column.
- Roles shorthand: U = any logged-in user; M = Manager; A = Admin; S = Superadmin.

## Public endpoints (no token)
| Method | Path | Notes |
|---|---|---|
| GET | `/` | `{status, service, admin_panel}` health |
| GET | `/admin`, `/admin/{path}` | Web panel HTML |
| GET | `/Favicon.png` | Favicon file |
| GET | `/api/auth/departments` | `[str]` SmartGroup names |
| GET | `/api/jobs/public` | Job categories with `sub_items` |
| POST | `/api/auth/login` | Rate limit 5/min |
| POST | `/api/auth/register` | Creates PENDING Employee |
| POST | `/api/auth/reset-requests` | Rate limit 3/hour; same reply whether or not a match |

## Auth `/api/auth`
| Method | Path | Roles | Request | Response |
|---|---|---|---|---|
| POST | `/login` | public | `{employee_id, password}` (`employee_id` may be an email) | `{status, access_token, token_type, user:{employee_id,name,position,department,role}}`. 401 bad creds; 403 if status PENDING/DENIED/ARCHIVED |
| POST | `/register` | public | `{first_name,last_name,suffix?,email,password,department,mobile_phone?,name?}` | `{status,message,employee_id}` (id generated `EMPnnn`); 400 duplicate email |
| GET | `/me` | U | none | `{employee_id,name,first_name,last_name,suffix,position,department,role,email,mobile_phone,status}` |
| GET | `/users` | A, M, S | none | `[{employee_id,name,first_name,last_name,suffix,position,department,mobile_phone,email,birthday,gender,civil_status,agency,role,status,created_at,date_added,kiosk_code}]` |
| PUT | `/users/{emp_id}` | A only | `UserUpdateRequest` (all optional: `new_employee_id,first_name,last_name,suffix,mobile_phone,email,position,department,birthday,gender,civil_status,agency,role,status`) | `{status,message,employee_id}`; 404; 400 id exists |
| PUT | `/users/{emp_id}/status` | A only | `{status}` (`APPROVED/DENIED/PENDING/ARCHIVED`, not validated) | `{status,message}` |
| PUT | `/users/{emp_id}/password` | `Super Admin`, `Superadmin` | `{new_password}` (min 6) | `{message,employee_id}`; 400 if same as current |
| POST | `/reset-requests` | public | `{employee_id, mobile_phone}` | `{message}` |
| GET | `/admin/reset-requests` | `Super Admin`, `Admin` | none | `[{id,employee_id,name,requested_at,status}]` PENDING only |

## Punch `/api/punch`
| Method | Path | Roles | Request | Response |
|---|---|---|---|---|
| POST | `` | U | `{employee_id (required, IGNORED), punch_type, latitude, longitude, accuracy?, address?, is_mock?}` | `{status,punch_id,timestamp}` (ISO, Manila). 400: missing GPS, mock GPS, bad range, duplicate consecutive type |
| GET | `/active/me` | U | none | `{is_clocked_in, elapsed_seconds, clock_in_time?, job_name?}` (`job_name` = last punch `address`) |
| PUT | `/switch-job` | U | `{job_title}` | `{status, job_name}`; 400 if not clocked in |
| GET | `/my-logs` | U | none | `[{id,employee_id,punch_type,timestamp (ISO),latitude,longitude,accuracy,address}]` newest first |
| GET | `/logs` | A, S, M | none | Same fields; `timestamp` is `MM/DD/YYYY, HH:MM:SS AM/PM`; ALL employees |
| GET | `/export` | A, S, M | none (no date filter) | CSV file of all logs |

Punch types: `CLOCK_IN`, `CLOCK_OUT`, `BREAK_IN`, `BREAK_OUT`. Extra body fields sent by mobile (`full_name, department, brand_subgroup, job_title, date, timestamp`) are dropped by Pydantic.

## DTR `/api/dtr`
| Method | Path | Roles | Request | Response |
|---|---|---|---|---|
| GET | `/summary/{employee_id}` | self, or M/A | Query `start_date`, `end_date` (`YYYY-MM-DD`) | `{employee_id,start_date,end_date,totals:{regular_hours,late_minutes,undertime_minutes,overtime_hours},daily_details:[{date,clock_in,clock_out,regular_hours,late_minutes,undertime_minutes,overtime_hours,status}]}`. `status` = PRESENT/INCOMPLETE/ABSENT. 403 for S viewing others |
| GET | `/export` | M, A | Query `start_date`, `end_date` (required), `employee_id?`, `custom_formula?` | `.xlsx` stream. Formula variables: `regular_hours,late_minutes,undertime_minutes,overtime_hours`. Bad formula yields `ERR: ...` in the cell |

Engine fixed values (UNVERIFIED as business rules, hardcodes in router): grace 15 min, fallback shift 08:00-17:00, break 60 min, overtime never approved (`overtime_approved=False`).

## Manager `/api/manager`
| Method | Path | Roles | Request | Response |
|---|---|---|---|---|
| GET | `/team` | M, A | none | `[{employee_id,name,position,department,role,email,mobile_phone,status}]` (A: all; M: direct reports or same department). S gets 403 |
| POST | `/revisions/request` | U | `{punch_log_id?, requested_punch_type, requested_timestamp (datetime), reason}` | `{message, revision_id}` |
| GET | `/revisions/my-requests` | U | none | `[{id,employee_id,punch_log_id,requested_punch_type,requested_timestamp,reason,status,manager_signature,manager_note,reviewed_by,reviewed_at,created_at}]` |
| GET | `/revisions` | M, A | none | Pending only: `[{id,employee_id,employee_name,smart_group,punch_log_id,requested_punch_type,requested_timestamp,reason,status,created_at}]` |
| POST | `/revisions/{id}/action` | M, A | `{action: APPROVED|REJECTED, manager_signature?, manager_note?}` | `{message}`. APPROVED edits the punch or inserts a new one. No check that a manager owns the employee |
| GET | `/groups` | M, A | none | `[{id,name,description,assigned_count,employee_ids}]` (ScheduleGroup, separate from SmartGroup) |
| POST | `/groups` | M, A | `{name,description?,employee_ids[]}` | `{message, group_id}` |
| GET | `/schedules` | U (no role check) | Query `employee_id?`, `group_id?` | `[{id,employee_id,group_id,day_of_week,shift_start,shift_end,break_duration_mins}]` |
| POST | `/schedules` | M, A | `{employee_id?, group_id?, day_of_week (0=Mon), shift_start "HH:MM", shift_end "HH:MM", break_duration_mins=60}` | `{message, schedule_id}`. Always inserts; no update |

## Jobs, Brands, Smart Groups `/api/jobs`
| Method | Path | Roles | Request | Response |
|---|---|---|---|---|
| GET | `` | U | none | Job categories with `sub_items` |
| POST | `` | A, S | `{name,code?,description?,sub_items[]}` | `{status,category_id}` |
| DELETE | `/{category_id}` | A, S | none | `{status,message}` |
| GET | `/brands` | U | none | `[str]`; seeds Head Office/Stores/Commissary if empty |
| POST | `/brands` | A, S | `{name}` | `{status,name}` |
| PUT | `/brands/{old_name}` | A, S | `{name}` | `{status,new_name}` |
| DELETE | `/brands/{brand_name}` | A, S | none | `{status,message}`; also deletes its groups |
| GET | `/groups` | U | Query `brand?` | `[{id,name,dept,brand,creator,selected,admins[]}]`; seeds 6 default groups if empty |
| POST | `/groups` | A, S | `{name,brand_name="Head Office",creator?,admins[]}` | `{status,id,name}` or `{status:"exists",id}` |
| PUT | `/groups/{group_name}` | A, S | `{new_name}` | `{status,new_name}` |
| DELETE | `/groups/{group_name}` | A, S | none | `{status,message}` |
| GET | `/groups/{group_name}/jobs` | U | none | `{jobs:[str]}` |
| PUT | `/groups/{group_name}/jobs` | `Super Admin`, `Admin` | `{jobs:[str]}` | `{detail}`. S (`Superadmin`) is NOT allowed |
| PUT | `/groups/{group_name}/admins` | A, S | `{admins:[employee_id]}` | `{status,admins}` |

## Forms `/api/forms`
| Method | Path | Roles | Request | Response |
|---|---|---|---|---|
| GET | `/categories` | U | Query `is_archived=false` | `[{id,name,isArchived}]`. Non-admins only see categories with a form assigned to their department or `All users group` |
| POST | `/categories` | A, S | `{name}` | `{id,name,isArchived}`; un-archives an existing archived name; 400 if exists |
| PUT | `/categories/{id}` | A, S | `{name}` | `{status,id,name}` |
| PATCH | `/categories/{id}/archive` | A, S | Query `is_archived=true` | `{status,id,isArchived}` |
| DELETE | `/categories/{id}` | A, S | none | `{status,message}`; cascades forms and submissions |
| GET | `` | U | Query `category?`, `is_archived=false` | `[{id,category,name,status,entries,views,assignedGroups[],assignmentType,totalAssignees,createdBy,createdAvatar,administratedBy,dateCreated,isArchived,isNew,schema_fields}]`. `schema_fields` is a JSON STRING here. Non-admins are filtered by department |
| POST | `` | A, S | `{category,name,assigned_groups[],assignment_type="Dynamic",schema_fields[]}` | `{id,name,category,assignmentType}`; 400 `form name already exist` |
| GET | `/{form_id}` | U | none | `{id,category,name,status,entries,assigned_groups[],assignment_type,totalAssignees,createdBy,dateCreated,isArchived,schema_fields[]}` (snake_case, parsed list). No department filter |
| PUT | `/{form_id}` | A, S | any of `{name,status,assigned_groups[],assignment_type,schema_fields[],is_archived}` | `{status}` |
| DELETE | `/{form_id}` | A, S | none | `{status}`; deletes submissions |
| POST | `/{form_id}/duplicate` | A, S | none | `{id,name}` |
| GET | `/{form_id}/submissions` | U (any user, no role check) | none | `[{id,submittedBy,dateTime "MM/DD/YYYY, HH:MM AM/PM",smartGroup,status,formData:[{label,value}]}]` |
| POST | `/{form_id}/submissions` | U | `{smart_group?, form_data:[{label,value}]}` | `{status,id}`. Submitter name comes from the token |
| DELETE | `/submissions/{sub_id}` | A, S | none | `{status}` |
| GET | `/signatures/my-signature` | U | none | `{signature}` |
| POST | `/signatures/my-signature` | U | `{signature}` (data URL) | `{status,message}` |

`schema_fields[]` element: `{id,type,label,required,options[],description/content/value,dateFormat?,timeFormat?}`. `type` in use: `Open Ended, Description, Dropdown, Yes/No, Task, Date, Signature, Location, Rating`.

## Current state: contract mismatches found (VERIFIED by code read)
| ID | Finding | Evidence | Impact |
|---|---|---|---|
| API-01 | Web panel calls `PUT /api/forms/{id}/archive`, which has no route. Archiving a form fails | `main.py` `archiveCustomForm` vs `forms.py` | Archive button broken. Use `PUT /api/forms/{id}` `{is_archived:true}` |
| API-02 | Web panel calls `POST /api/auth/users` (Add user), which has no route (`UserCreateRequest` exists but is unused) | `main.py` `saveDirectNewUser`, `auth.py` | Add user fails; also sends a fixed default password |
| API-03 | Sidebar "Export DTR" does `window.open('/api/dtr/export')`: no token, and `start_date`/`end_date` are required | `main.py` sidebar | Always 401/422 |
| API-04 | Reset-requests poll reads `localStorage['hris_token']`; login stores `atwork_jwt_token` | `main.py` `fetchResetRequests` | Bell badge always 401 |
| API-05 | `saveRenameGroup` edits localStorage helpers, never calls `PUT /api/jobs/groups/{name}` | `main.py` | Rename does not persist |
| API-06 | Role lists disagree: `Admin` only (users PUT/status), `Super Admin`+`Admin` (group jobs PUT), `Superadmin` missing from `/dtr/*`, `/manager/*` | `auth.py`, `jobs.py`, `dtr.py`, `manager.py` | Superadmin `xinxaola` gets 403 on several endpoints. Needs Architect decision |
| API-07 | Mobile `ManagerScreen` export calls `/api/punch/export` (CSV, all logs, no dates) but the UI says `.xlsx` with a date range; `/api/dtr/export` is the xlsx endpoint | `ManagerScreen.js` | Dates ignored, wrong format |
| API-08 | Mobile `FormsScreen` reads `item.description` and category `color`/`icon`; the API returns none of them | `FormsScreen.js` vs `forms.py` | Always uses fallbacks |
| API-09 | `main.py` registers a second `POST/GET /api/forms/{form_id}/submissions` (table `custom_form_submissions`) after `forms.router`. The router version wins; the main.py copy is dead code and references `CustomForm`, which is not imported there | `main.py` end of file | Confusing; remove after Architect confirm |
| API-10 | `GET /api/forms/{id}/submissions` and `GET /api/manager/schedules` have no role check; `POST /revisions/{id}/action` has no ownership check | `forms.py`, `manager.py` | Security Gem to review |
| API-11 | `GET /api/forms` returns `schema_fields` as a string, `GET /api/forms/{id}` as a list; list uses camelCase, detail uses snake_case | `forms.py` | Clients must parse both |
| API-12 | The previous "form_data not handled" gap is NOT reproduced: `FormSubmissionCreate.form_data` and `FormSubmission.form_data` exist | `forms.py`, `models.py` | Needs a runtime test to close |

## Hardcodes seen in the API layer
`SECRET_KEY` fallback string in `auth_utils.py`; fixed grace 15 / shift 08:00-17:00 / break 60 in `dtr.py`; default groups/brands seeded in `jobs.py`; `smart_group` fallback `"HO - I.T."` in `forms.py`; `kiosk_code = employee_id.zfill(4)`; default password in the web panel add-user call; CORS origins list and super-admin seed data in `main.py`.

## Change process
1. Architect decides the contract change.
2. API Gem records it here (rule 4).
3. Full-Stack Gem implements backend, then web panel, then mobile.
4. Same commit updates this file (rule 3).

## Gem checklist (before touching any endpoint or call site)
- [ ] Ran `grep -n "@router\.\|@app\." backend/app/main.py backend/app/routers/*.py` this session.
- [ ] Method and path match this file exactly.
- [ ] Roles match the code (`Depends(get_current_user)` or `require_roles`).
- [ ] Pydantic request model maps every field the client sends.
- [ ] Response keys match the table (check camelCase vs snake_case).
- [ ] Every client call site found with `grep -rn "<path>" src backend/app/main.py`.
- [ ] Time format of the endpoint noted (ISO vs display string).
- [ ] This file edited in the same commit, "Last verified" updated.
