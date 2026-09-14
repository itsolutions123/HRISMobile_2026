# DTR App — Project State
Last updated: September 15, 2026

## Stack (confirmed, do not change without discussion)
- Backend: FastAPI (Python 3.11, Uvicorn)
- Frontend Mobile: React Native / Expo Go (JavaScript, Node 20)
- Frontend Web Admin: Connecteam-inspired HTML5/Bootstrap 5 dashboard (integrated into FastAPI `/admin`)
- Database: PostgreSQL 15 (Container: `hris-postgres-db`, Database: `hrisdb`, User: `hrisuser`)
- Auth: Custom Employee ID (`3286`) + Password verification, REST endpoint `/api/auth/login`
- Repo structure:
  - `/backend`: FastAPI service, SQLAlchemy ORM models, database routers, Docker Compose definition
  - `/src`: React Native mobile application screens (`LoginScreen.js`), state context (`AuthContext.js`)

## Infra (fixed facts — never re-derive or guess these)
- App runs in Docker on Proxmox VM `ansible-srv` (10.0.10.37), accessed via SSH
- Backend REST API: `http://10.0.10.37:8089` (Container: `hris-fastapi-backend`)
- Mobile Metro Bundler: `http://10.0.10.37:8087` (Container: `hris-mobile-bundler`)
- SSL/reverse proxy is a SEPARATE Proxmox VM (10.0.10.250) running Nginx — the app itself does not terminate SSL
- Primary Admin / System Administrator: ID `3286` | Password `bigtime@123` | Name `Jaypee Balonzo`

## Done (do not rebuild these)
- [x] Backend REST API (`/api/auth/login`, `/api/auth/users`, `/api/jobs`, `/api/punch`)
- [x] Database schema migrations (Employees table extended with personal details: phone, email, birthday, civil status, agency)
- [x] React Native Mobile App login logic synced to `/api/auth/login`
- [x] Web Admin UI (`/admin`) Connecteam layout:
  - Job List datatable with **Job Titles** (sub-items) and slide-over drawer creation
  - Live GPS OpenStreetMap/Leaflet integration with map auto-re-centering (`map.invalidateSize()`)
  - Real-time DTR punch logs, employee name search filter, CSV export
  - Connecteam dual-pane User Profile Editor allowing full inline editing of Employee IDs & personal details
  - Admin Header dropdown with **Sign out** and profile controls

## In progress
- Nginx Reverse Proxy routing on `10.0.10.250` for external domain SSL access

## Not started
- Standalone Android APK build package generation

## Known decisions / constraints
- Primary user identity relies on string Employee ID (`3286`), allowing admins to update primary key values while cascading to `PunchLog` entries.
- Web Admin Interface is served directly via FastAPI `HTMLResponse` at `/admin` to eliminate additional static container overhead.
