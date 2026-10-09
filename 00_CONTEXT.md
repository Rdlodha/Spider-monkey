# ReconForge: Context (read first, every session)

Local, single-user recon workbench. Imports and parses tool output (Nmap, Feroxbuster, Gobuster, SQLMap), normalizes it, correlates it, tracks findings and checklists, and generates reports. Later it can run tools against targets you are authorized to test.

## Deployment model (decided)
- Runs only on the owner's machine. No multi-user, no hosting, no registration/roles.
- Backend binds to `127.0.0.1` only, never `0.0.0.0`.
- CORS allows only the exact frontend origin (`http://localhost:5173`), no wildcard.
- A random API token is generated on first run (stored in `backend/.local/token`, git-ignored). The frontend sends it as `Authorization: Bearer`. This blocks other local web pages and DNS-rebinding from driving the API (it can launch tools).
- One implicit user (`local`). The audit log still records `actor="local"` so multi-user can be added later without reshaping data.

## Stack
React + Vite + JavaScript, Tailwind + shadcn/ui. Python + FastAPI, SQLAlchemy 2.0, Alembic, Pydantic Settings. PostgreSQL via Docker Compose. REST. Git. Tests: pytest, vitest. Lint: ruff, eslint.

## Repo layout
```text
reconforge/
├── docker-compose.yml        # postgres only
├── .env.example
├── README.md
├── docs/DECISIONS.md         # short ADR-style log, one line per decision
├── backend/
│   ├── app/{main.py,api,models,schemas,services,parsers,tools,core}/
│   ├── alembic/
│   ├── tests/fixtures/       # small sample outputs per format
│   └── requirements.txt
└── frontend/src/{components,pages,layouts,services,lib}/
```

## Data model (add entities only in the milestone that needs them)
```text
Project(id, name, authorized_ack_at, created_at)
ScopeEntry(id, project_id, kind[ip|cidr|domain], value)
Target(id, project_id, value)
Scan(id, project_id, target_id, tool, scan_type, status, proxy_profile_id?,
     scope_confirmed_at, started_at, completed_at, exit_code, error,
     raw_path, raw_sha256)
Host(id, project_id, ip, hostname, first_seen, last_seen, scan_id)     UNIQUE(project_id, ip)
Service(id, host_id, protocol, port, state, name, product, version,
        first_seen, last_seen, scan_id)                                UNIQUE(host_id, protocol, port)
Endpoint(id, host_id, service_id?, url, path, status_code, content_length,
         source_tool, first_seen, last_seen, scan_id, is_interesting)  UNIQUE(project_id, url)
Finding(id, project_id, title, description, severity, status, source_tool,
        source_scan_id?, notes, tags, created_at, updated_at)
FindingLink(finding_id, entity_type[host|service|endpoint], entity_id)
Evidence(id, finding_id, kind[screenshot|request_response|tool_output|note],
         path, sha256, size, created_at)
ChecklistTemplate / ChecklistTemplateItem          # global, versioned
ChecklistProgress(target_id, template_item_id, state, note)
ProxyProfile(id, name, type, host, port, username, secret_encrypted, enabled)
AuditLog(id, ts, actor, action, target, tool, result)   # append-only
```
Enums: Scan status `queued|running|completed|failed|cancelled`. Severity `INFO|LOW|MEDIUM|HIGH|CRITICAL`. Finding status `OPEN|INVESTIGATING|CONFIRMED|FALSE_POSITIVE|RESOLVED`. Checklist state `NOT_STARTED|IN_PROGRESS|COMPLETED|NOT_APPLICABLE`. Proxy type `DIRECT|HTTP|HTTPS|SOCKS5|BURP|CUSTOM`.

## Non-negotiable rules
1. No secrets in Git. All config via env vars; `.env.example` has placeholders only.
2. Every import is an upsert: re-importing the same output must not create duplicates. Update `last_seen` and keep `first_seen`.
3. Every derived record stores the `scan_id` it came from.
4. Raw output is preserved on disk (`data/raw/<sha256>`), referenced by path and hash. Not stored in a text column.
5. All parsers return the same normalized objects. The DB layer never knows which tool produced them.
6. Subprocesses: argument arrays only, never `shell=True`, never string-concatenated commands. Users pick scan *profiles*, not free-form flags.
7. XML via `defusedxml`. Uploads have size limits. Uploaded filenames are never used as paths.
8. Parse errors are shown to the user, never swallowed. stderr is never hidden.
9. Correlation is deterministic and produces *suggested* links the user can accept or reject.
10. Out of scope forever: exploitation, credential attacks, IP rotation, stealth/anti-detection, AI correlation (until after V1).

## Working agreement (saves tokens)
- Do only the current milestone. Honor its STOP list.
- Read this file plus the current milestone file only; do not re-read finished milestones unless needed.
- Tick the Definition of Done boxes and add one line to `docs/DECISIONS.md` for any new decision.
- Commit per milestone using conventional commits (`feat:`, `fix:`, `test:`, `docs:`).

## Milestone order
M1 Foundation → M2 Import pipeline → M3 Findings and checklists → M4 Tool engine and proxies → M5 Reports, hardening, release.
