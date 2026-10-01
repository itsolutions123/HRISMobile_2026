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
Date: 2026-10-01   Status: PROPOSED
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
