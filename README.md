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

Start the backend server:

```powershell
uvicorn app.main:app --reload --port 8000
```

> Note: Alembic migrations are not required in Phase 2A. Database schema models and migrations will be added in a later phase.

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open the frontend at `http://localhost:5173` and the backend at `http://localhost:8000`.

## Project Structure

- `backend/` – FastAPI application, database config, Alembic migrations, tests
- `frontend/` – Vite React application, Tailwind UI, API client
- `database/` – schema and seed scripts
- `docs/` – architecture, API, database, development plan

## Notes

- No Docker is used in this phase.
- Local PostgreSQL is required.
- Phase 1 only includes the project foundation and health-check API.
