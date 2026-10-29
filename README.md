# ReconForge

> **A local, single-user recon workbench for authorized penetration testing assessments.**

ReconForge is a portfolio-quality web application that helps a security professional manage the full lifecycle of a penetration test engagement — from scope definition and tool execution through findings, evidence, checklists, and report generation.

---

## ⚠️ Authorized Use Only

ReconForge is designed exclusively for use against systems you own or have **explicit written permission** to test. Unauthorized access to computer systems is illegal. By using this tool, you agree to comply with all applicable local, national, and international laws.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Browser (Vite + React)              │
│  Dashboard · Scans · Findings · Checklist · Reports  │
│  Attack Surface Graph · Audit Logs · Proxy Manager   │
└──────────────────┬───────────────────────────────────┘
                   │  HTTP (Bearer token, localhost only)
┌──────────────────▼───────────────────────────────────┐
│        FastAPI backend  (127.0.0.1:8000)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Projects │  │  Scans   │  │  Report Service  │   │
│  │ Targets  │  │ Parsers  │  │  (MD + PDF)      │   │
│  │ Findings │  │ Tool Eng.│  │  Graph Builder   │   │
│  │ Evidence │  │ Job Run. │  │  Audit Log       │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
│                   SQLAlchemy ORM                      │
└──────────────────┬───────────────────────────────────┘
                   │
         ┌─────────▼────────┐
         │  SQLite database │
         │ (reconforge.db)  │
         └──────────────────┘
```

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS 3, React Router 6, React Flow, Lucide icons |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | SQLite (dev/default) — path configurable |
| Auth | Static Bearer token (256-bit entropy, local file) |
| Parsers | Nmap XML, Feroxbuster JSON-lines, Gobuster text |
| Reports | Markdown (in-memory), PDF (reportlab) |
| Crypto | Fernet symmetric encryption (cryptography library) |

---

## Features

### M1 – Foundation
- Project management with explicit authorized-use acknowledgement
- Target scope definition (IP, CIDR, URL, domain)
- SQLite database with Alembic migrations
- Bearer-token middleware (local token file, auto-generated)
- CORS locked to `localhost:5173`

### M2 – Import Pipeline
- Import scan output files: **Nmap XML**, **Feroxbuster JSON-lines**, **Gobuster text**
- Automatic host/service/endpoint upsert (no duplicates on re-import)
- Scan history with SHA-256 file fingerprinting
- Full host/service detail views

### M3 – Findings & Checklists
- Finding management: severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), status (OPEN/CONFIRMED/FALSE_POSITIVE/RESOLVED/INVESTIGATING)
- File evidence uploads (screenshots, request/response, tool output, notes)
- Checklist templates (OWASP-style methodology items)
- Checklist progress tracking per target

### M4 – Tool Engine
- Proxy profile management with Fernet-encrypted credentials
- Job runner: executes nmap/feroxbuster/gobuster as subprocesses
- Scope enforcement before every job — refuses out-of-scope targets
- Command injection prevention: `shell=False`, list-based argv
- Job audit logging: success, error, cancel

### M5 – Reporting & Release
- **Assessment Reports**: Markdown and PDF (with false-positive exclusion + secret redaction)
- **Attack Surface Graph**: React Flow interactive node graph (Project→Target→Host→Service→Endpoint→Finding)
- **Audit Log viewer**: filterable, append-only
- **Security review**: `docs/SECURITY.md` with sign-off
- Toast notifications, loading/empty states, accessibility basics

---

## Installation

### Prerequisites

- Python 3.11 or later
- Node.js 18 or later
- Docker (optional, for lab targets)

### 1. Clone

```bash
git clone <repo-url>
cd "Spider Monkey"
```

### 2. Backend

```bash
cd backend

# Create a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the API server (always bind to 127.0.0.1)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The first run auto-generates a local bearer token at `backend/.local/token`.

### 3. Frontend

```bash
cd frontend
npm install

# Read the token
cat ../backend/.local/token     # macOS/Linux
Get-Content ../backend/.local/token  # Windows PowerShell

# Create .env.local (gitignored — never commit this)
echo VITE_API_BASE_URL=http://localhost:8000 > .env.local
echo VITE_API_TOKEN=<paste-token-here> >> .env.local

npm run dev
```

Open **http://localhost:5173**.

### 4. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL |
| `VITE_API_TOKEN` | _(required)_ | Bearer token from `backend/.local/token` |
| `DATABASE_URL` | `sqlite:///./reconforge.db` | SQLAlchemy connection string |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS allowed origin |
| `LOCAL_TOKEN_PATH` | `backend/.local/token` | Path to token file |

Backend env vars can be set in `backend/.env` (see `.env.example`).

---

## Seed Demo Data

After starting the backend and running migrations:

```bash
# From project root:
python scripts/seed_demo.py
```

This populates a sample "DVWA Lab Assessment" project with realistic hosts, services, endpoints, findings (CRITICAL → INFO), and evidence.

---

## Lab Environment (Intentionally Vulnerable Targets)

```bash
# Start DVWA + Juice Shop + phpMyAdmin (all on 127.0.0.1 only)
docker compose -f docker-compose.lab.yml up -d

# Stop and remove all data
docker compose -f docker-compose.lab.yml down -v
```

| Service | URL | Credentials |
|---|---|---|
| DVWA | http://localhost:8080/dvwa/ | admin / password (after setup) |
| Juice Shop | http://localhost:3000 | admin@juice-sh.op / admin123 |
| phpMyAdmin | http://localhost:8081 | root / rootpassword |

**First-time DVWA:** navigate to `/dvwa/setup.php` → click **Create / Reset Database** → set Security Level to Low.

---

## Supported Tools & Parser Formats

### Nmap (XML)
```bash
nmap -sV -oX output.xml 192.168.100.0/24
```
Import format: XML (standard nmap `-oX` output).  
Parsed: hosts, open ports, service name/product/version.

### Feroxbuster (JSON-lines)
```bash
feroxbuster -u http://target -o output.txt --output-format json
```
Import format: one JSON object per line.  
Parsed: URLs, status codes, content length.

### Gobuster (text)
```bash
gobuster dir -u http://target -w wordlist.txt -o output.txt
```
Import format: plain text output (one result per line).  
Parsed: paths and status codes.

### Subfinder (JSON-lines)
```bash
subfinder -d example.com -oJ -silent -o subfinder.json
```
Import format: JSON lines (`-oJ`).  
Parsed: subdomains and resolved IPs into host records.

### Amass (JSON-lines)
```bash
amass enum -passive -d example.com -json amass.json
```
Import format: JSON lines (`-json`).  
Parsed: domain names, resolved IP addresses, and CIDR relationships into hosts.

### Httpx (JSON-lines)
```bash
httpx -u http://target -json -silent -title -tech-detect -status-code -web-server -o httpx.json
```
Import format: JSON lines (`-json`).  
Parsed: hosts, open services (ports + detected server product/version), and endpoints with detected technologies.

### WhatWeb (JSON)
```bash
whatweb -a 3 http://target --log-json=whatweb.json
```
Import format: JSON (`--log-json`).  
Parsed: web hosts, services (server product and version), endpoints, and detected tech stack.

### Wappalyzer (JSON)
```bash
wappalyzer https://target --output=json > wappalyzer.json
```
Import format: JSON (`--output=json`).  
Parsed: web hosts, services, and endpoints with detected JavaScript libraries, frameworks, CMSs, and versions.

---

## Proxy Configuration

1. Navigate to **Proxy Manager** in the sidebar.
2. Create a proxy profile: type (HTTP/HTTPS/SOCKS5), host, port, optional credentials.
3. Credentials are encrypted at rest using Fernet symmetric encryption.
4. Use **Test** to verify connectivity.
5. When creating a Scan Job, select the proxy profile to route tool traffic.

Proxy flags are injected per tool:
- **nmap**: `--proxies socks4://host:port`
- **feroxbuster**: `--proxy http://host:port`
- **gobuster**: `--proxy http://host:port`

---

## Threat Model

ReconForge is designed as a **local-only, single-user tool** with the following assumptions:

### What the Token Protects Against
- Other browser tabs or web pages on the same machine (CORS + token)
- Other local processes that do not know the token
- Accidental exposure if port is briefly accessible on LAN

### What the Token Does NOT Protect Against
- An attacker with user-level OS access (they can read `backend/.local/token`)
- Malware running as the same OS user

### Security Controls Summary

| Control | Implementation |
|---|---|
| Authentication | 256-bit Bearer token, local file |
| Transport | localhost only (127.0.0.1) |
| CORS | Exact origin (`http://localhost:5173`) |
| Input validation | Pydantic v2 schemas on all endpoints |
| Command injection | `shell=False`, list argv, scope check |
| Path traversal | uuid4 filenames for all disk writes |
| Secret storage | Fernet encryption for proxy credentials |
| Audit trail | Append-only audit log (no edit/delete endpoints) |
| XSS | React JSX auto-escaping + no `dangerouslySetInnerHTML` |
| Error messages | No stack traces or paths in HTTP responses |

Full security review: [`docs/SECURITY.md`](docs/SECURITY.md)

---

## Running Tests

### Backend

```bash
cd backend
python -m pytest tests/ -v
# Expected: 80 passed
```

### Frontend

```bash
cd frontend
npm test
# Expected: 4 passed (vitest)
```

### Build check

```bash
cd frontend
npm run build
# Expected: no errors
```

### Dependency audits

```bash
# Python
cd backend && pip-audit

# JavaScript
cd frontend && npm audit
```

---

## Database Setup & Migrations

```bash
cd backend

# Create all tables (fresh install)
alembic upgrade head

# Show current revision
alembic current

# Generate a new migration
alembic revision --autogenerate -m "description"
```

Migration history:
- `0001` — Projects, Targets
- `0002` — Scans, Hosts, Services
- `0003` — Findings, FindingLink, Evidence, Checklists
- `0004` — ScopeEntry, Job
- `0005` — ProxyProfile
- `0006` — Endpoint

---

## Limitations & Roadmap

### Current Limitations (V1)
- Single-user only (no multi-user auth)
- SQLite by default (no concurrent writes under load)
- No scan diffing (compare scan runs over time)
- PDF output is basic reportlab layout (not WeasyPrint)
- No AI-assisted finding suggestions
- Tool binaries (nmap, feroxbuster, gobuster) must be installed separately on the host OS

### Parked for V2
- Scan diffing UI
- Additional parser support (Nuclei, Nikto, Masscan)
- AI-assisted finding suggestions
- Multi-user authentication (if ever hosted)
- PostgreSQL migration path for concurrent use

---

## Project Structure

```
Spider Monkey/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── core/         # Security, config, crypto, audit
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic (report, jobs, parsers)
│   ├── alembic/          # Database migrations
│   ├── tests/            # pytest test suite (80 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Sidebar, TopBar, Toast
│   │   ├── layouts/      # MainLayout
│   │   ├── pages/        # All page components
│   │   └── services/     # api.js
│   └── package.json
├── docs/
│   ├── SECURITY.md       # Security review & sign-off
│   └── DECISIONS.md      # Architecture decision records
├── scripts/
│   └── seed_demo.py      # Demo data seeder
├── docker-compose.yml        # (PostgreSQL, optional)
├── docker-compose.lab.yml    # Vulnerable lab targets
├── Makefile
└── README.md
```

---

## Contributing

This is a personal portfolio project. Issues and suggestions are welcome via GitHub Issues.

---

## License

MIT — see [LICENSE](LICENSE) (if present). Use responsibly and only for authorized testing.
