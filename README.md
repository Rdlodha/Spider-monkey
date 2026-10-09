# ReconForge

Local, single-user recon workbench.

## Quickstart

1. `cp .env.example .env` (and edit if needed)
2. `docker compose up -d`
3. Backend: `cd backend && pip install -r requirements.txt && alembic upgrade head && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
4. Frontend: `cd frontend && npm install && npm run dev`
5. Read token: `cat backend/.local/token` (Windows: `Get-Content backend/.local/token`)
6. Add to `.env`: `VITE_API_TOKEN=<token>`
