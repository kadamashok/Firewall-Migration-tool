# Firewall Migration Tool

Production-ready web-based firewall configuration migration platform with:
- React + Vite + Tailwind enterprise dashboard
- FastAPI backend with RBAC, encrypted credentials, job orchestration
- Vendor-aware detection and migration modules (Palo Alto, Fortinet, Cisco ASA, CheckPoint)
- Compatibility engine, dry-run mode, audit logs, backup/rollback hooks
- Report export (PDF + JSON)

## Project Status

- Current status: `MVP complete` and runnable locally (frontend + backend).
- Frontend and backend boot verified on March 3, 2026.
- Migration logic is implemented with safe dry-run, compatibility scoring, and reporting.
- Vendor modules are scaffolded for Palo Alto, Fortinet, Cisco ASA, and CheckPoint with extendable adapters.
- Production hardening items (HA job queue, persistent storage, enterprise auth integration) are documented below.

## Tech Stack

- Frontend: React 18, Vite 5, TypeScript 5, Tailwind CSS 3, Axios
- Backend: Python 3.11, FastAPI, Uvicorn, Pydantic v2
- Network connectivity: Paramiko, Netmiko, NAPALM
- Security/Auth: JWT (`python-jose`), Passlib, Fernet encryption (`cryptography`)
- Reports: ReportLab (PDF) + JSON export
- Logging/Audit: file-based audit log (`backend/audit/audit.log`)
- Queue mode: FastAPI BackgroundTasks (Celery-ready architecture)

## Project Structure

```text
frontend/
backend/
  main.py
  device_detector.py
  compatibility_engine.py
  config_extractor.py
  transformer.py
  config_pusher.py
  report_generator.py
  security.py
  vendors/
    paloalto.py
    fortinet.py
    ciscoasa.py
    checkpoint.py
```

## Features Implemented

1. Source and destination firewall credential intake (IP, username, password, SSH port).
2. Connectivity test with explicit failures:
   - Invalid IP format (validation)
   - Authentication failed
   - Device unreachable
3. Auto detection:
   - Vendor
   - Model
   - OS/Firmware
4. Compatibility engine:
   - Same-vendor major version checks
   - Cross-vendor policy conversion mode + conversion matrix
5. Migration workflow:
   - Source config extraction
   - Normalization and transform engine
   - Destination backup before push
   - Push with API-preference fallback note (`API disabled` -> SSH CLI fallback)
6. Incompatible handling:
   - Compatibility report with issues and severity
7. Dry-run execution mode.
8. Reports:
   - JSON structured output
   - PDF summary
9. Security:
   - Passwords encrypted in memory (Fernet)
   - JWT auth + RBAC (`Admin`, `Operator`)
10. Enterprise extras:
   - Audit logs
   - Rollback endpoint stub (backup payload available)
   - Bulk migration API
   - Optional email notification on completion

## Implemented vs Planned

Implemented now:
- End-to-end migration workflow orchestration
- Device detection and compatibility checks
- Dry-run and migration job progress tracking
- JSON and PDF reporting
- Basic RBAC and encrypted credential handling

Planned next:
- Redis/Celery-backed distributed job queue
- Persistent database for jobs/reports/users
- Full vendor-native API push/commit/rollback flows
- SSO/LDAP integration and granular permissions
- Deeper validation engine for complex NAT/VPN edge-cases

## Backend Setup (FastAPI)

1. Create and activate a Python virtual environment.
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Copy env template:
   ```bash
   cp backend/.env.example backend/.env
   ```
4. (Recommended) Generate secure values:
   - `JWT_SECRET_KEY`: long random secret
   - `CRED_ENCRYPTION_KEY`: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
5. Start backend:
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

Note:
- `bcrypt` is pinned to `4.0.1` for compatibility with `passlib==1.7.4`.

Default users (override via env):
- `admin / Admin@123`
- `operator / Operator@123`

## Frontend Setup (React + Vite + Tailwind)

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Configure API URL:
   ```bash
   cp .env.example .env
   ```
3. Start frontend:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:5173`.

## API Overview

- `POST /auth/login`
- `POST /connectivity-test`
- `POST /detect-device`
- `POST /check-compatibility`
- `POST /dry-run`
- `POST /start-migration`
- `GET /jobs/{job_id}`
- `GET /reports/{report_id}/json`
- `GET /reports/{report_id}/pdf`
- `POST /rollback/{job_id}` (Admin)
- `POST /bulk-migration` (Admin)

## Production Hardening Notes

- Restrict `allow_origins` in `backend/main.py` (do not leave `*` in production).
- Use a real user store (LDAP/SSO/DB) instead of seeded users.
- Move from in-memory job store to Redis + Celery for horizontal scale.
- Integrate vendor-native APIs (PAN-OS XML/REST, FortiManager/FortiGate API, Cisco API) for commit/rollback guarantees.
- Enable TLS everywhere and run behind a reverse proxy (Nginx/Traefik).

## Ownership

- GitHub owner: `kadamashok`
- Primary contact: `kadamashokna@gmail.com`
