# ReconForge Security Review

**Review Date:** 2026-10-13  
**Reviewer:** Engineering (M5 release audit)  
**Scope:** All backend API routes, middleware, frontend rendering, data handling, and deployment defaults.

---

## 1. Local-Only Binding & Token Enforcement ✅

| Check | Result |
|---|---|
| Backend bound to `127.0.0.1` (not `0.0.0.0`) | **PASS** — uvicorn launched with `--host 127.0.0.1` |
| `BearerTokenMiddleware` requires `Authorization: Bearer <token>` on all `/api/*` routes | **PASS** — enforced in `app/core/security.py` |
| Token auto-generated with `secrets.token_hex(32)` (256-bit entropy) | **PASS** |
| Token file created with `chmod 0o600` where supported | **PASS** (no-op on Windows, which uses ACLs instead) |
| `/api/health` bypasses token check (intentional) | **PASS** — health check is public, reveals no sensitive data |
| OPTIONS preflight bypasses token check (CORS requirement) | **PASS** — browser must receive CORS headers before sending credentials |
| Token never logged or included in error responses | **PASS** — logs only HTTP status; token is not echoed |

**Threat model:** The token protects against other local processes or browser tabs on the same machine making API calls. It does **not** protect against an attacker with user-level OS access (they can read `backend/.local/token` directly). ReconForge is single-user, local-only by design.

---

## 2. CORS Configuration ✅

| Check | Result |
|---|---|
| `allow_origins` set to exact `settings.frontend_origin` (default `http://localhost:5173`) | **PASS** — no wildcard `*` |
| `allow_credentials=True` with explicit origin (not wildcard) | **PASS** — compliant |
| CORS middleware added before `BearerTokenMiddleware` so preflight OPTIONS gets CORS headers | **PASS** |

---

## 3. Input Validation (Pydantic) ✅

All API request bodies are validated via Pydantic v2 schemas. Fields are typed (str, int, bool, UUID-format strings). No `dict`-typed catch-all bodies accepted.

| Route Group | Schema | Notes |
|---|---|---|
| `/api/projects` | `ProjectCreate` — `name: str`, `authorized_ack: bool` | Requires explicit authorization acknowledgement |
| `/api/projects/{id}/targets` | `TargetCreate` — `value: str`, `kind: str` | |
| `/api/findings` | `FindingCreate` — typed severity, status enums | |
| `/api/engine/jobs` | `JobRequest` — `project_id, target_id, tool, extra_args: list[str]` | Args validated as list, not free-form string |
| `/api/proxy-profiles` | `ProxyProfileCreate` — typed fields | Secret encrypted at rest via Fernet |

**No endpoint accepts raw SQL, shell commands, or untyped `Any` bodies.**

---

## 4. Command Construction & Injection Prevention ✅

**Re-audit of M4 tool engine:**

- All tool commands are built as Python **lists** (never f-string interpolation into a shell string).
- `subprocess.run(..., shell=False)` is enforced — no shell expansion.
- `extra_args` are passed as a list and appended directly; each element is a separate `argv` entry.
- Shell metacharacters (`;`, `|`, `$()`, backtick, `&&`, `>`) are **not interpreted** when `shell=False`.
- Scope validation runs before command construction — out-of-scope targets raise `ValueError` and do not run.
- Evidence from M4 tests: `test_hostile_input_semicolon`, `test_hostile_input_command_substitution`, `test_hostile_input_unicode` — all **PASS**.

---

## 5. Path Traversal ✅

| Attack Surface | Mitigation |
|---|---|
| Evidence file uploads (`/api/evidence`) | `uuid4()` is used as the on-disk filename; original filename is stored only as metadata, never used in `open()` |
| Raw scan output stored by job runner | Stored under `backend/scan_output/<job_id>/` — job_id is a uuid4, no user-controlled path segment |
| Report PDF download | Generated in-memory by reportlab; never written to disk; no path parameter |
| Markdown report | Generated in-memory; served as `PlainTextResponse` |
| Evidence download | If `path` is stored, it must be inside the `EVIDENCE_DIR` — currently evidence `path` is never used for filesystem reads in the API (only stored as metadata) |

---

## 6. SSRF Prevention ✅

The only outbound HTTP call is the **proxy test endpoint** (`POST /api/proxy-profiles/{id}/test`), which:

- Accepts `test_url` from the request body.
- Uses `httpx.Client(proxy=proxy_url)` — the connection goes through the proxy, not directly to an internal address.
- **Limitation:** No blocklist for `169.254.0.0/16` (link-local), `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`. Since ReconForge is a local pen-test tool and intentionally reaches internal hosts, blocking RFC-1918 addresses would break core functionality. **Accepted risk** — documented here.
- No other endpoint makes outbound HTTP calls.

---

## 7. Upload Validation ✅

| Check | Result |
|---|---|
| File uploads (scan imports, evidence) use `UploadFile` via FastAPI multipart | **PASS** |
| File size is limited by OS/uvicorn defaults | **NOTE:** No explicit `max_size` guard. Large uploads could cause memory pressure. For a local single-user tool, this is an **accepted risk**. |
| File content is parsed, not executed | **PASS** — XML/text parsers only |
| Filenames are never used for filesystem paths | **PASS** — uuid4 used as disk path |

---

## 8. Markdown/Evidence Rendering in Frontend ✅

- Report preview is rendered as **plain monospace text** (`<pre>` / `whitespace-pre-wrap`) — no `dangerouslySetInnerHTML`, no Markdown-to-HTML rendering in browser.
- Findings and evidence text is displayed via React JSX text nodes — auto-escaped by React.
- No `innerHTML` anywhere in the frontend source.
- `escape_md()` in `report_service.py` HTML-escapes user data before inserting into the Markdown report string.

---

## 9. Secret Handling ✅

| Check | Result |
|---|---|
| `frontend/.env.local` is in `.gitignore` | **PASS** |
| `backend/.local/token` is in `.gitignore` | **PASS** |
| `backend/reconforge.db` (SQLite) is in `.gitignore` | **PASS** |
| Proxy credentials encrypted at rest using Fernet symmetric encryption | **PASS** — `app/core/crypto.py` |
| Encryption key derived from token file + machine-specific salt | **PASS** |
| Secrets not logged | **PASS** |

**Git history note:** No secrets have been committed to the repository in any milestone. The `.gitignore` was set up in M1 before first commit.

---

## 10. Error Responses ✅

- FastAPI exception handlers return `{"detail": "..."}` with a descriptive but safe message.
- **No stack traces** are included in production responses — FastAPI does not include tracebacks in HTTP responses by default.
- File paths, internal class names, and database details do not appear in error responses (verified by inspecting all `raise HTTPException` calls).
- `500 Internal Server Error` returns only `"Internal Server Error"` (Starlette default).

---

## 11. Database Permissions ✅

- SQLite is used for development. SQLite has no user/permission model; the file is protected by OS file permissions (`rw-------` where supported).
- No raw SQL strings — all queries go through SQLAlchemy ORM.
- Alembic manages all schema changes; no `CREATE TABLE` in application code.

---

## 12. Dependency Audit

### Python (`pip-audit`)

Run: `pip-audit` (from `backend/` with venv active)

```
No known vulnerabilities found  (result as of 2026-10-13)
```

### JavaScript (`npm audit`)

Run: `npm audit` (from `frontend/`)

```
found 0 vulnerabilities  (result as of 2026-10-13)
```

> [!NOTE] Run `pip-audit` and `npm audit` before each release to catch newly disclosed CVEs.

---

## 13. Remaining Known Limitations / Accepted Risks

| Item | Risk Level | Decision |
|---|---|---|
| No file-size limit on uploads | Low — local single-user | Accepted |
| No SSRF block for RFC-1918 ranges | N/A — intentional (pen-test tool) | Accepted by design |
| SQLite file not encrypted at rest | Low — protected by OS file perms | Accepted for v1 |
| Token does not expire | Low — local only; user can delete `backend/.local/token` to rotate | Accepted |
| Windows `chmod 0o600` is a no-op | Low — Windows uses ACLs; standard user accounts are isolated | Accepted |

---

## Sign-Off

All items above have been reviewed and either **PASS** or carry an explicitly **accepted risk** with documented rationale. ReconForge M5 is cleared for release as a local-only, single-user tool.
