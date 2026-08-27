# Smart Women Security Application

This repository contains the foundation for the Smart Women Security Application using React + TypeScript frontend and FastAPI + SQLAlchemy backend.

## Local Setup

### MySQL

1. Install MySQL locally.
2. Create the application database:

```powershell
mysql -u root -p -e "CREATE DATABASE women_security_db;"
```

If you prefer the MySQL shell:

```powershell
mysql -u root -p
CREATE DATABASE women_security_db;
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` and set the MySQL connection string using the existing database name:

```powershell
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/women_security_db
```

Start the backend server in development:

```powershell
uvicorn app.main:app --reload --port 8000
```

Apply database migrations (required - the schema comes exclusively from Alembic):

```powershell
alembic upgrade head
```

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env.development
npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env.development` for local development (template default points at `http://localhost:8000/api`). It is baked into the bundle at build time: production builds read it from the deployment platform's environment (e.g. the Render dashboard), never from a local file — this prevents `localhost`/`127.0.0.1` URLs from leaking into production bundles.

Open the frontend at `http://localhost:5173` and the backend at `http://localhost:8000`.

## Project Structure

- `backend/` – FastAPI application, database config, Alembic migrations, tests
- `frontend/` – Vite React application, Tailwind UI, API client
- `database/` – schema and seed scripts
- `docs/` – architecture, API, database, development plan

## Production Deployment (Render)

Deployment-ready configuration ships with this repository:

- `backend/start.sh` — production entrypoint: runs `alembic upgrade head`, then starts Gunicorn with Uvicorn workers bound to `0.0.0.0:$PORT` (respects the platform-injected `PORT`; no hardcoded production port).
- `render.yaml` — optional Render Blueprint defining the backend web service and frontend static site (all secrets are `sync: false`; nothing sensitive lives in the file). Deploy via **New → Blueprint**, or configure services manually with the commands below.

### Backend service

| Setting | Value |
| --- | --- |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `bash start.sh` |
| Health check path | `/api/health` |

Migrations run automatically inside `start.sh` before the server accepts traffic; do NOT use `Base.metadata.create_all()` in production. To review migration SQL without touching any database:

```powershell
cd backend
alembic upgrade base:head --sql > migration.sql
```

### Frontend service (static site)

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Publish directory | `dist` |

Set `VITE_API_BASE_URL` to the deployed backend API base (e.g. `https://<your-backend>.onrender.com/api`) at build time.

### Required environment variables

Configure in your platform dashboard; never commit them.

Backend: `DATABASE_URL`, `ENVIRONMENT=production`, `JWT_SECRET_KEY` (random, ≥ 32 chars — startup refuses weaker values), `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `DEV_OTP_MODE=false`, `ENABLE_RATE_LIMITING=true` (startup refuses to boot in production without it), `CORS_ORIGINS`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `OSRM_BASE_URL`, optional `WEB_CONCURRENCY`. See `backend/.env.example` for descriptions and safe placeholders.

Frontend: `VITE_API_BASE_URL`.

### CORS configuration

The backend reads `CORS_ORIGINS` (comma-separated exact origin URLs; a JSON array string is also accepted). Localhost Vite ports remain the development default. In production set it to your deployed frontend origin(s) — an explicit list is required because credentialed requests cannot use wildcard origins.

### Routing (OSRM)

`OSRM_BASE_URL` stays configurable. The public demo instance (`https://router.project-osrm.org`) is fine for development but is **not** production-grade (rate limits, no SLA); point the variable at a self-hosted or managed OSRM instance for serious use. No paid routing provider is used or required.

## Notes

- Docker is not used; services run natively on Render (or any platform that supports Python + static sites).
- MySQL is required (local for development, managed for production).
- Never commit `.env` files — each environment keeps its own secrets in the platform dashboard; only `.env.example` templates belong in source control.
