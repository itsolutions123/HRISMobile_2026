# Security Rules and Guidelines - DTR App
Last verified: 2026-10-06 against commit cff48c2
Owner: Security Gem

## Rules (MUST / MUST NOT / SHOULD)
1. **MUST**: Every endpoint declares `get_current_user` or `require_roles([...])`, except an approved public list. 
   *Check*: `grep -n "APIRouter(" backend/app/routers/*.py`
2. **MUST**: The acting user comes from the token, never the request body. 
   *Check*: `grep -n "employee_id" backend/app/routers/*.py` on request models.
3. **MUST**: One consistent set of role names, defined in one place. 
   *Check*: `grep -n "require_roles" backend/app/routers/*.py`
4. **MUST**: Managers are limited to their team's records. 
   *Check*: `grep -n "manager_id\|department ==" backend/app/routers/manager.py`
5. **MUST**: JWT signing key from env, no fallback literal. 
   *Check*: `grep -n "SECRET_KEY" backend/app/auth_utils.py`
6. **MUST NOT**: Plaintext comparison of stored passwords. 
   *Check*: `sed -n '1,45p' backend/app/auth_utils.py`
7. **MUST NOT**: Passwords stored on the device or in the browser. Tokens only, in the mechanism the Expo SDK 57 docs recommend.
8. **MUST NOT**: Credentials, tokens, or real employee data in tracked files, commits, PROJECT_STATE.md, or docs. 
   *Check*: `git ls-files | grep -i -E ".env|.pem|.key|credential"`
9. **MUST**: Login rate limit keyed on the real client IP. 
   *Check*: `cat backend/app/limiter.py` + nginx proxy headers.
10. **MUST**: Public access HTTPS only via the nginx VM; app containers never terminate TLS.
11. **MUST**: GPS and punch data readable only by the owner, their manager, or an Admin.
12. **MUST**: Exports require a token; no bare-URL downloads.
13. **MUST**: Escape user text before innerHTML; no interpolated values in inline onclick. 
   *Check*: `grep -c "innerHTML" backend/app/main.py`
14. **SHOULD**: Token lifetime and refresh documented and justified.
15. **SHOULD**: Audit-log approvals and role changes.

## Current State
Verified routes: Most routes are correctly utilizing token-based auth (`get_current_user` or `require_roles`). Identity for punches is correctly derived from `current_user.employee_id`.

## Known Gaps (Findings)
| ID | Finding | Status | Severity | Impact |
|---|---|---|---|---|
| S-17 | Four routes are OPEN: `/api/auth/departments`, `/api/auth/register`, `/api/auth/login`, `/api/jobs/public`. | VERIFIED | LOW | Intentional, but registration lacks rate limits. |
| S-18 | Role names are inconsistent ("Admin", "Superadmin", "Super Admin", "SUPERADMIN", "ADMIN") and hardcoded strings. | VERIFIED | LOW | Maintenance burden; risk of bypass. |
| S-20 | `require_roles` is underutilized; most endpoints manually check `current_user.role not in [...]`. | VERIFIED | LOW | Code smell; potential for missed checks. |
| S-21 | Application falls back to a hardcoded plaintext JWT secret (`hris_dtr_secret_key...`) if env var is missing. | VERIFIED | HIGH | Forgeable admin tokens if deployed without env var. |
| S-22 | Application falls back to hardcoded PostgreSQL credentials if `DATABASE_URL` is missing. | VERIFIED | HIGH | Credentials in source control. |
| S-23 | `verify_password` falls back to plaintext comparison if hash check fails or exception is raised. | VERIFIED | HIGH | Bypasses hashing entirely. |
| S-24 | Registration has no rate limit. Login uses `get_remote_address` which may throttle all users if proxy headers aren't handled. | VERIFIED | MEDIUM | Brute-force / DoS risks. |
| S-25 | Token lifetime is hardcoded to 24 hours with no refresh mechanism. | VERIFIED | LOW | Archiving users does not kick them out until expiry. |
| S-26 | Mobile app stores `hris_last_password` in plaintext in `AsyncStorage`. | VERIFIED | HIGH | Password extraction from device. |
| S-27 | Web panel stores JWT in `localStorage` making it vulnerable to XSS. | VERIFIED | MEDIUM | Session hijacking risk. |
| S-28 | Web panel heavily relies on `innerHTML` (67 instances) and inline `onclick` (158 instances). | VERIFIED | HIGH | Stored XSS path. |

## Change Process
Schema/API Contract changes -> Architect Gem.
Feature implementation -> Full-Stack Gem.
Security review & rulings -> Security Gem.

## Gem Checklist (Before touching security logic)
1. Check `docs/SECURITY.md` for existing gaps.
2. Run Endpoint auth matrix (E1).
3. Run Role and Ownership checks (E2).
4. Run Hardcode and Secret audit (E3).
5. Verify TLS/Proxy headers if modifying rate limits (E4/E6).

## Rulings
- **S-R001**: Admin-Initiated Password Reset API. Approved transmission of plaintext password over TLS in JSON body. Requires `require_roles(["Admin", "Superadmin"])` and strict backend hashing.

## Public Exposure Gate
G1: All non-public routes require token (VERIFIED - E1)
G2: Acting employee comes from token (VERIFIED - E2)
G3: OPEN routes are approved (VERIFIED - Registration/Login/Jobs)
G4: No default/fallback secret (FAIL - S-21)
G5: Rate limit keyed on real client (FAIL - S-24/UNVERIFIED proxy config)
G6: HTTPS only (UNVERIFIED - nginx config missing)
G7: Clients send token/handle errors (FAIL - S-27 localStorage)
G8: DB not publicly reachable (UNVERIFIED)
G9: Test accounts documented (UNVERIFIED)
G10: Rollback written (UNVERIFIED)
