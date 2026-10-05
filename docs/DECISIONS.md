## D-001 - Secure API Contracts for Punch, Jobs, and Exports
Date: 2026-10-01   Status: APPROVED
Mode: architecture decision (security remediation)
Context: Security Ruling S-R001 flagged `/api/punch`, `/api/jobs`, and export endpoints for lacking authentication, blocking the public exposure needed for the test APK. Evidence: `backend/app/routers/punch.py:30,50,67,120` and `jobs.py:40,55,77`.
Decision: Implement Strict Token Identity and Native File Downloads (Option A).
Alternatives rejected: Option B (Short-Lived URL Tokens for exports) was rejected to avoid stateful token management and unnecessary database/memory complexity.
Contract: 
  - `GET /api/punch/active/me` (replaces `/active/{employee_id}`) - Auth: Token (Depends(get_current_user)).
  - `POST /api/punch` - Auth: Token (Depends(get_current_user)). Body `employee_id` ignored; identity derived strictly from the token.
  - `GET /api/punch/logs` & `GET /api/punch/export` - Auth: Token (Depends(get_current_user) + require_roles).
  - `GET /api/jobs/public` - Auth: None. Read-only minimal category list for Login/Registration screens.
  - `GET /api/jobs` and write endpoints - Auth: Token (Depends(get_current_user)).
  - Exports - Auth: Token. Mobile app drops `Linking.openURL` and uses authenticated `fetch` with `expo-file-system` and `expo-sharing`.
Schema: no change
Migration: none
Config: Mobile will require `expo-file-system` and `expo-sharing` added to package.json/app.json.
Security impact: Resolves S-R001. Secures public-facing endpoints prior to exposing the backend.
Affects: backend yes | web panel yes | mobile yes
Hardcodes removed / remaining: none directly affected by this contract change.
Hand back to: Full-Stack (implement) -> API Gem (record)
Docs to update: docs/API.md | docs/SECURITY.md

## D-002 - Test APK Build Configuration and Release Setup
Date: 2026-10-01   Status: APPROVED
Mode: build-release
Context: External testing of GPS clock in/out requires an installable Android APK pointing to https://app.bigtimeempire.com. Security blockers cleared in D-001. Evidence: app.json, src/context/AuthContext.js:8.
Decision: Configure Expo SDK 57 for a local standalone test APK build:
  1. API Base URL: Environment-driven via EXPO_PUBLIC_API_BASE_URL in src/context/AuthContext.js (defaults to http://10.0.10.37:8089 if unset).
  2. Android Identity: package "com.bigtime.hrismobileapp.test", version "1.0.0", versionCode 1 in app.json.
  3. Permissions: Foreground location permissions (ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION) in app.json.
  4. Build Method: Local Gradle build via `npx expo prebuild` and `./gradlew assembleRelease` (100% self-hosted).
  5. Test Data Handling: Use dedicated test employee account created via DB/admin panel (no hardcoded credentials). Post-test punch cleanup via targeted SQL DELETE after pg_dump backup.
  6. Rollback / Revocation: Set test user `is_active = false` post-testing to disable access immediately.
Alternatives rejected:
  - Cloud EAS build (rejected to avoid SaaS/cloud dependencies).
  - Hardcoding HTTPS URL in JS (rejected as it breaks local dev workflow).
  - Production package ID (rejected to allow side-by-side installation with future release).
Contract: no change
Schema: no change
Migration: none
Config: app.json (android block), src/context/AuthContext.js (EXPO_PUBLIC_API_BASE_URL usage), .env.production / .env.local.
Security impact: None added beyond D-001. External endpoints are token-protected and served over TLS via Nginx.
Affects: backend no | web panel no | mobile yes
Hardcodes removed / remaining: Removed hardcoded API URL http://10.0.10.37:8089 in src/context/AuthContext.js.
Hand back to: Full-Stack (implement) -> API Gem / Database Gem (record)
Docs to update: docs/API.md

## D-003 - Add Endpoint to Delete Form Submissions
Date: 2026-10-02   Status: APPROVED
Mode: new feature
Context: The web panel needs a way to delete custom form submissions (either single or bulk from a table selection). Evidence: backend/app/routers/forms.py lacks a DELETE endpoint for FormSubmission.
Decision: Implement a single-resource RESTful deletion endpoint. The web panel will handle batch deletions by issuing concurrent requests (e.g., via `Promise.all`).
Alternatives rejected: A custom batch endpoint (`POST /api/forms/submissions/batch-delete` or `DELETE` with a JSON body) was rejected to keep the API surface strictly RESTful and avoid HTTP client edge cases with DELETE bodies, as admin deletion volumes are small enough for concurrent fetches.
Contract: `DELETE /api/forms/submissions/{submission_id}` - Auth: Token (Depends(get_current_user)) + role check for "Admin" or "Superadmin". Request: path parameter `submission_id` (int). Response: `{"detail": "Submission deleted successfully"}`. Errors: 404 if not found, 403 if insufficient permissions.
Schema: no change
Migration: none
Config: none
Security impact: Data deletion endpoint created. Secured by token authentication and restricted strictly to Admin/Superadmin roles, matching existing form management endpoints.
Affects: backend yes | web panel yes | mobile no
Hardcodes removed / remaining: none
Hand back to: Full-Stack (implement) -> API Gem (record)
Docs to update: docs/API.md

## D-004 - RBAC Redesign and Smart Group Form Routing
**Date:** 2026-10-02
**Status:** APPROVED
**Mode:** SCHEMA CHANGE / NEW FEATURE DESIGN
**Context:** Transitioning to a 4-tier RBAC (Super Admin, Admin, Manager, Basic). Managers need to approve forms scoped strictly to their assigned Smart Groups.
**Decision:** 
- Basic users are assigned exactly one Smart Group (`smart_group_id` on `employees`).
- Managers can manage multiple Smart Groups via a new `smart_group_managers` join table.
- Legacy role 'Employee' becomes 'Basic'. 'SuperAdmin' becomes 'Super Admin'.
**Alternatives rejected:** Storing manager IDs in a JSON column on SmartGroup (rejected for referential integrity and query performance).
**Contract:** Updates to `/api/auth/me`, `/api/forms`, `/api/smart_groups/{id}/managers`, `/api/employees/{id}/role`.
**Schema:** Add `employees.smart_group_id`, create `smart_group_managers` join table.
**Migration:** Backup DB, run ALTER/CREATE tables, map string 'Employee' to 'Basic'.
**Config:** None.
**Security impact:** Form visibility strictly enforced on the backend based on `smart_group_id` and role.
**Affects:** Backend, Web Panel (restart).
**Blueprint:** docs/features/rbac-forms-approval.md
**Hardcodes removed/remaining:** SmartGroup.selected legacy behavior kept for now.
**Hand back to:** Full-Stack Gem
**Docs to update:** API.md, DATABASE.md, SECURITY.md

## D-005 - Task Scheduling and Notification Strategy
Date: 2026-10-05   Status: APPROVED
Mode: new feature / build-release
Context: The app needs to automatically clock out users after 21 hours (backend) and alert them at 9.5 hours (mobile). Neither apscheduler nor expo-notifications currently exist in the repo, and the database has no device token storage.
Decision: 
1. Use `APScheduler` (AsyncIOScheduler) within the FastAPI application lifecycle for the 21-hour auto-clock-out sweep.
2. Use `expo-notifications` for Local Notifications on the mobile client for the 9.5-hour alert, scheduled at the moment of clock-in and cancelled upon clock-out.
Alternatives rejected: Celery/Redis (overkill for backend scheduling); Push Notifications (rejected as it requires external push infrastructure and schema changes for device tokens).
Contract: no change
Schema: no change
Migration: none
Config: none
Security impact: none (no external services, no new endpoints, notifications are local to the device)
Affects: backend yes | web panel no | mobile yes
Hardcodes removed / remaining: none
Hand back to: Full-Stack (implement)
Docs to update: none
