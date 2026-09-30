# API Contract Documentation
Last verified: 2026-09-30 against commit 7b21276
Owner: API Gem

## Principles
1. **API-first**: The FastAPI server is the source of truth for all data, roles, and business rules.
2. **Default Deny**: All endpoints must require a valid JWT token via the `Authorization: Bearer <token>` header unless explicitly documented as public.
3. **Contract Changes**: Any changes to request/response shapes must be recorded in this document before implementation.

## Base URLs & Environments
*   **Web Panel**: Calls relative paths (e.g., `/api/auth/me`) or uses `window.location.origin` because it is served by the backend itself.
*   **Mobile App**: Configured via `API_BASE_URL` in `src/context/AuthContext.js` (currently `http://10.0.10.37:8089`). 

## Conventions
*   **JSON Naming**: Request/response payloads generally use `snake_case` (e.g., `smart_group`), but some older endpoints use `camelCase` (e.g., `isArchived`). Client must map exactly to the documented contract.
*   **Date/Time**: Returned as formatted strings (e.g., `MM/DD/YYYY, HH:MM AM/PM`) for display, or ISO 8601 for computations.

## Forms API Reference

| Method | Path | Auth | Request Body | Response Shape | Consumers |
|---|---|---|---|---|---|
| `GET` | `/api/forms` | User | None (Query: `category`, `is_archived`) | `[{id, title, description, category, form_data: []}]` | Web, Mobile |
| `GET` | `/api/forms/{id}` | User | None | `{id, title, form_data: []}` | Web, Mobile |
| `POST` | `/api/forms/{id}/submissions` | User | `{"smart_group": "...", "form_data": [...]}` | `{"status": "success", "id": 123}` | Mobile |
| `GET` | `/api/forms/{id}/submissions` | User | None | `[{id, submittedBy, dateTime, smartGroup, status, formData: [...]}]` | Web |

*(Note: Additional endpoints for Authentication, Jobs, DTR, and Scheduling exist but are abbreviated here for brevity during the current task.)*

## Current State & Known Gaps
*   **API-01 / API-02 / API-03**: The form submissions endpoints (`/api/forms/{form_id}/submissions`) and `FormSubmission` DB model do not currently handle the `form_data` payload. This is a known gap blocking the mobile form submission feature.

## Change Process
1. Architect/User requests a contract change.
2. API Gem records the contract in `docs/API.md`.
3. Full-Stack Gem implements the backend schema and routers.
4. Full-Stack Gem wires the web and mobile clients to match.

## Gem Checklist
Before touching any endpoint, the Full-Stack Gem MUST verify:
- [ ] Method and Path match exactly.
- [ ] Authentication depends (`Depends(get_current_user)`) is present.
- [ ] Pydantic request models map all incoming fields.
- [ ] Database models contain columns for all stored fields.
- [ ] Response dictionary/model matches the documented shape.
