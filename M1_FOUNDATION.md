# M1: Foundation

**Goal:** Working skeleton: frontend → backend → database, with local-only protection in place. No recon logic.

## Tasks
1. **Repo + tooling:** layout from `00_CONTEXT.md`, `.gitignore` (include `.env`, `.local/`, `data/`), `docker-compose.yml` (Postgres), `.env.example`, ruff/eslint/pytest/vitest configs, `docs/DECISIONS.md` seeded with the stack and the local-only decision.
2. **Backend:**
   - FastAPI app, Pydantic Settings reading env vars, bind `127.0.0.1`.
   - CORS limited to the frontend origin from config.
   - First-run token generation to `backend/.local/token`; middleware requires `Authorization: Bearer <token>` on all `/api/*` except `/api/health`.
   - `GET /api/health` → `{"status":"ok","application":"ReconForge"}`.
   - SQLAlchemy 2.0 engine/session, Alembic initialized, first migration creates `Project`, `Target`, `AuditLog`.
   - Helper `audit(action, target=None, tool=None, result=None)`. Use it on project/target create.
3. **Frontend:**
   - Vite + Tailwind + shadcn/ui, sidebar + top bar, dark mode toggle.
   - Pages (placeholders): Dashboard, Projects, Web Recon, Network Recon, Database Recon, Findings, Checklist, Settings.
   - One API client in `services/` that attaches the token (read from a dev env var for now) and surfaces errors.
   - Dashboard calls `/api/health` and shows status.
4. **Projects:** create/list project and target (name/value only). On project creation require the "I am authorized to test these targets" checkbox; store `authorized_ack_at`.
5. **Git:** `git init`, first commit `feat: initialize ReconForge foundation`.

## Definition of Done
- [ ] `docker compose up -d` starts Postgres; `alembic upgrade head` works.
- [ ] Backend and frontend start separately; README has exact commands.
- [ ] Dashboard shows health from the backend.
- [ ] Request without a token gets 401; wrong-origin CORS request is rejected.
- [ ] Project + target can be created; audit rows are written.
- [ ] Sidebar navigation works on all 8 pages.
- [ ] No hardcoded secrets; `.env` and `.local/` are git-ignored.
- [ ] CI-equivalent local command (`make check` or script) runs lint + tests.

## STOP
No Nmap, Feroxbuster, Gobuster, SQLMap, proxies, or scanning. No user accounts, passwords, or roles.
