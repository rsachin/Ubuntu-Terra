# Ubuntu Terra — Windows Local Setup Guide

A step-by-step guide to get the full Ubuntu Terra stack running on a clean Windows 10/11 machine. This is the source of truth until Docker support is added.

---

## Prerequisites

| Tool | Required Version | Purpose | Download / Install Notes |
|------|------------------|---------|--------------------------|
| **Python** | 3.10–3.13 (3.11–3.13 recommended) | FastAPI backend | https://www.python.org/downloads/ — check **"Add Python to PATH"** during install |
| **Node.js** | 20.x or newer | Vite frontend | https://nodejs.org/ — download the LTS installer |
| **PostgreSQL** | 15+ | Relational + geospatial database | https://www.postgresql.org/download/windows/ |
| **PostGIS** | 3.4+ | Spatial extension for PostgreSQL | Installed via Stack Builder after PostgreSQL install, or via OSGeo4W |
| **Git** | any | Clone the repository | https://git-scm.com/download/win |
| **A code editor** | any | Edit `.env`, SQL, code | VS Code recommended |

**Note on Python 3.14:** avoid it for now — `pydantic==2.9.2` and `psycopg2-binary==2.9.9` do not provide Python 3.14 wheels. The project declares `requires-python = ">=3.10,<3.14"` in `backend/pyproject.toml`.

---

## Quick Start Option — Docker (Recommended)

If you have Docker Desktop with WSL2 enabled, the fastest way to run everything is:

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra
docker compose up --build
```

Then open http://localhost:5173. Docker handles PostgreSQL + PostGIS, the backend, and the frontend automatically.

---

## Native Windows Setup

### 1. Install PostgreSQL + PostGIS

#### Option A — EnterpriseDB installer + Stack Builder (recommended for beginners)

1. Download the PostgreSQL 15+ Windows installer from https://www.postgresql.org/download/windows/.
2. Run the installer. Keep the default port `5432` and remember the password you set for the `postgres` superuser.
3. At the end of the installer, **launch Stack Builder** when prompted.
4. In Stack Builder:
   - Select your PostgreSQL installation.
   - Open the **"Spatial Extensions"** category.
   - Check **PostGIS** and install it.
5. Add PostgreSQL binaries to your user `PATH`:
   - Open PowerShell and run:
     ```powershell
     [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\15\bin", "User")
     ```
   - Close and reopen PowerShell.

#### Option B — OSGeo4W (if you already use QGIS/osgeo tools)

1. Download the OSGeo4W installer from https://trac.osgeo.org/osgeo4w/.
2. Choose **Advanced Install**.
3. Select the packages `postgresql` and `postgis` and complete the install.
4. Add the OSGeo4W `bin` directory to your `PATH`.

#### Verify PostGIS

Open a new PowerShell window:

```powershell
psql --version
```

You should see a version string. If you get a "command not found" error, PostgreSQL is not on your `PATH` yet — see Troubleshooting.

To confirm PostGIS is available inside PostgreSQL:

```powershell
psql -U postgres -d ubuntu_terra -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

If this fails with "extension 'postgis' is not available", PostGIS is not installed correctly. Re-run Stack Builder or OSGeo4W.

---

### 2. Create the Database

Open **PowerShell** and run:

```powershell
# 1. Create the database (you will be prompted for the postgres password you set during install)
psql -U postgres -c "CREATE DATABASE ubuntu_terra;"

# 2. Enable the PostGIS extension in the new database
psql -U postgres -d ubuntu_terra -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

If you want to use a different superuser/database name, adjust the `DATABASE_URL` accordingly in step 4.

---

### 3. (Optional) One-Command Dev Launcher

Once Python, Node, PostgreSQL, and PostGIS are installed and `.env` is configured, you can start the whole stack from the repository root with:

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra
.\scripts\dev.ps1
```

This will:
- create the Python virtual environment if it does not exist,
- install backend dependencies,
- start PostgreSQL if it is installed as a Windows service,
- apply migrations and seed demo fields,
- start the backend in a new PowerShell window,
- install frontend dependencies and start the frontend in another window.

Useful flags:
```powershell
.\scripts\dev.ps1 -ResetDB      # drop and recreate the database
.\scripts\dev.ps1 -NoSeed       # migrate but do not seed demo fields
.\scripts\dev.ps1 -NoFrontend    # start only the backend and database
```

---

### 4. Clone the Repository

```powershell
cd C:\Users\%USERNAME%\code   # or wherever you keep projects
git clone <your-repo-url> ubuntu-terra
cd ubuntu-terra
```

---

### 5. Environment Variables

1. Copy the example environment file:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` in your editor and set at least the database URL:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/ubuntu_terra
   ```
   Replace `YOUR_POSTGRES_PASSWORD` with the password you set during PostgreSQL install.

3. For local frontend development the remaining defaults are fine:
   ```env
   ALLOWED_ORIGINS=http://localhost:5173
   ```

4. (Optional) For live WhatsApp alerts, fill in:
   ```env
   TWILIO_AUTH_TOKEN=...
   TWILIO_ACCOUNT_SID=...
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   RECIPIENT_WHATSAPP_NUMBER=...
   ```
   Without these, outbound alerts are recorded as `simulated` and inbound webhooks fail closed with HTTP 500.

---

### 6. Apply Database Migrations and Seed Demo Fields

Use the single ordered migration runner:

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra\database
..\venv\Scripts\python migrate.py --seed
```

This creates the database if it does not exist, applies `001` through `005` in order, and seeds the 3 demo fields.

If you need a completely clean database (destroys existing data):

```powershell
..\venv\Scripts\python migrate.py --reset --seed
```

You should see:
```text
Applying 5 migration(s) to ...
Applied 001_initial_schema.sql
...
All migrations applied successfully.
Seeding demo fields...
Seeded 3 demo fields.
Seeded demo NDVI trigger for Patensie field.
```

---

### 7. Start the Backend Manually

If you are not using `scripts\dev.ps1`:

#### Create a Python virtual environment

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra
python -m venv venv
```

#### Install Python dependencies

```powershell
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r backend\requirements.txt
```

#### Run the backend

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra\backend
..\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Leave this PowerShell window open. The API is now at:
- App: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

---

### 8. Start the Frontend Manually

Open a **second** PowerShell window (keep the backend running).

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra\frontend
npm install
npm run dev
```

Leave this window open. The frontend is now at http://localhost:5173.

> If you need to point the frontend at a deployed backend instead of `localhost:8000`, create `frontend\.env` with `VITE_API_BASE_URL=https://your-backend-url`.

---

## Smoke Test Checklist

Open http://localhost:5173 in your browser and verify each item:

- [ ] The page title is "Ubuntu Terra" and the map container loads without a red error banner.
- [ ] The map shows Esri satellite imagery (you may need to zoom/pan).
- [ ] The field list on the left shows **3 demo fields**:
  - Patensie Citrus Block — Gamtoos Valley
  - Hankey Vegetable Field — Gamtoos Valley
  - Kirkwood Citrus Block — Sundays River Valley
- [ ] Clicking a field opens the condition panel on the right.
- [ ] The condition panel shows a risk level badge (**Low**, **Medium**, or **High**).
- [ ] For the Patensie demo field, the panel shows `[Demo data]` next to the update text.
- [ ] The **Recent trend** section shows at least one sparkline.
- [ ] The **WhatsApp Voice Alert Preview** section shows a generated message and an MP3 audio player.
- [ ] Clicking the "Draw New Field Boundary" button lets you click points on the map and save a new field.
- [ ] After saving a new field, it appears in the field list under "My Fields".
- [ ] The health endpoint returns OK: http://localhost:8000/api/health

---

## Run the Tests

Open a third PowerShell window (with the backend stopped or with a different `DATABASE_URL` if you want to avoid polluting the demo DB).

### Tests that do not need a database

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra\backend
..\venv\Scripts\python -m pytest tests\test_health.py tests\test_risk_engine.py tests\test_weather.py tests\test_satellite.py -q
```

Expected: all pass.

### Tests that need a seeded PostGIS database

Make sure PostgreSQL is running and migrations + seed are applied, then:

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra\backend
..\venv\Scripts\python -m pytest tests\ -q
```

Expected: the full suite should now be green.

---

## Build for Production

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra\frontend
npm run build
```

The static build is output to `frontend\dist`. You can preview it locally:

```powershell
npm run preview
```

---

## Troubleshooting

### "psql is not recognized" / "createdb is not recognized"

PostgreSQL's `bin` folder is not on your `PATH`. Add it permanently:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\15\bin", "User")
```

Then **close and reopen PowerShell**.

### PostGIS extension fails to create

If `CREATE EXTENSION postgis;` fails, PostGIS is not installed or not in the PostgreSQL `lib/share` path.

- Re-run Stack Builder and confirm PostGIS is installed for the exact PostgreSQL version.
- If you used OSGeo4W, make sure the PostGIS binaries are copied/symlinked into the PostgreSQL install directory, or use the OSGeo4W shell.
- **Workaround:** use the Docker Compose path (`docker compose up --build`) which includes PostGIS automatically.

### "connection refused" when the backend starts

PostgreSQL is not running. Start the service:

```powershell
# Find the service name
Get-Service | Where-Object { $_.Name -like "*postgres*" }

# Start it (replace the name if different)
Start-Service -Name "postgresql-x64-15"
```

### Python dependencies fail to install

- Confirm Python version: `python --version` should be 3.10–3.13.
- If you see Rust/toolchain errors, you are likely on Python 3.14 — downgrade.
- If `psycopg2-binary` fails, install the full Microsoft C++ Build Tools and try again, or switch to a Python version with a wheel.

### Node / npm not found

- Reinstall Node.js LTS and check **"Add to PATH"** during install.
- If using `nvm-windows` or `Nodist`, make sure the shim resolves correctly:
  ```powershell
  node --version
  npm --version
  ```

### Frontend build fails with MapLibre / worker errors

The Vite config already excludes `maplibre-gl` from dependency pre-bundling. If you still see worker errors:

```powershell
rm -Recurse -Force node_modules, .vite, dist
npm install
npm run dev
```

### CORS errors in the browser console

- Make sure `ALLOWED_ORIGINS` in `.env` includes `http://localhost:5173` exactly (no trailing slash).
- Restart the backend after changing `.env`.

### `TWILIO_AUTH_TOKEN` is not configured error on webhook test

This is expected behaviour: without a token the webhook fails closed. For local testing of the signature path, set a dummy token in the test environment. For a real demo, paste the Auth Token from the Twilio console into `.env`.

### Demo fields do not appear

- Confirm migrations ran successfully.
- Confirm you ran `seed_demo_fields.py`.
- Check the backend logs for database connection errors.

### Field drawing produces "Field coordinates must be within South Africa"

The app restricts fields to South Africa (longitude 16°E–33°E, latitude 22°S–35°S). Zoom to the Eastern Cape demo area and draw there.

### Line-ending issues (files show `^M` or scripts fail)

If you cloned with `autocrlf` issues, run:

```powershell
cd C:\Users\%USERNAME%\code\ubuntu-terra
git config core.autocrlf false
git rm --cached -r . 2>$null; git reset --hard
```

---

## .env Template

```env
# --- Database ---
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/ubuntu_terra

# --- Copernicus Data Space Ecosystem / Sentinel Hub (optional for live NDVI) ---
SENTINEL_HUB_CLIENT_ID=
SENTINEL_HUB_CLIENT_SECRET=

# --- Twilio Sandbox (WhatsApp) (optional for live alerts) ---
TWILIO_AUTH_TOKEN=
TWILIO_ACCOUNT_SID=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
RECIPIENT_WHATSAPP_NUMBER=

# --- CORS ---
ALLOWED_ORIGINS=http://localhost:5173

# --- App Security (demo placeholders, not currently enforced by the API) ---
DEMO_LOGIN_USERNAME=demo
DEMO_LOGIN_PASSWORD=change-me
```

---

## Quick Reference: Run Everything

Once set up, the daily development commands are:

```powershell
# Docker path (recommended if PostGIS is not installed natively)
cd C:\Users\%USERNAME%\code\ubuntu-terra
docker compose up --build

# Native path — Terminal 1: Backend
cd C:\Users\%USERNAME%\code\ubuntu-terra\backend
..\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# Native path — Terminal 2: Frontend
cd C:\Users\%USERNAME%\code\ubuntu-terra\frontend
npm run dev

# Browser
start http://localhost:5173
```

---

## Next Steps After Local Setup

1. Add the real Twilio Auth Token if you want live WhatsApp.
2. Optionally add GitHub Actions for reproducibility.
