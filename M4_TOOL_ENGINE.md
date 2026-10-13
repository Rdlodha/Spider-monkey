# M4: Tool Engine & Proxy Profiles

**Goal:** Controlled, auditable tool execution against authorized targets, plus reusable proxy profiles. Only use labs or systems you own or have written permission to test.

Split into two parts. Finish 4A before 4B.

## Part A: Tool engine
1. **Scope:** `ScopeEntry` rules per project (IP, CIDR, domain). A scan request requires target, tool, scan profile, and scope confirmation (stored on the scan). Reject out-of-scope targets in the API, not just the UI. At execution time, **resolve the hostname and re-check every resolved IP against scope** (blocks DNS tricks).
2. **ToolAdapter** (`tools/`): `validate(request)`, `build_command(request) -> list[str]`, `execute()`, `parse()`, `metadata()`. Adapters: Nmap, Feroxbuster, Gobuster. SQLMap stays import/parser only.
   - Commands are argv lists built centrally. No `shell=True`.
   - Users choose from **scan profiles** (e.g. `nmap-top-1000`, `ferox-common`), not raw flags. Reject targets starting with `-`. Wordlists come from an allowlisted directory.
   - Prefer machine-readable output (Nmap `-oX`, Ferox `--json`).
3. **Jobs:** run in a background worker using `asyncio` subprocess or a thread pool. Local single-user needs no Redis/Celery. States: `queued|running|completed|failed|cancelled`. Capture command metadata, start/end time, exit code, stdout, stderr (never hidden). Per-job timeout. Cancel = terminate the process group (SIGTERM, then SIGKILL after a grace period). Limit concurrent jobs (default 2). Mark orphaned `running` jobs as `failed` on startup.
4. **Audit:** write an audit row on job queued, started, cancelled, completed, failed.
5. After completion, feed output through the M2 parsers and the same upsert path.

## Part B: Proxy manager
1. `ProxyProfile` with types DIRECT/HTTP/HTTPS/SOCKS5/BURP/CUSTOM. Encrypt the password with Fernet; the key comes from an env var and is never committed. The API never returns the secret (only `has_secret: true`).
2. **Test Proxy** returns `Connected | Failed | Timeout | Authentication failed`. The test request goes to a fixed, configurable check URL, not a user-supplied one. Short timeout.
3. Per-scan proxy selection; the scan stores `proxy_profile_id`. Adapters translate the profile into tool flags (only for tools that support it; otherwise reject clearly).
4. UI: Tools, Proxy Manager, Scan Jobs (live status, stdout/stderr view, cancel with confirmation).

## Definition of Done
- [x] Adapters generate commands only via argv lists; unit-tested including hostile inputs (`;`, `$()`, leading `-`, spaces, unicode).
- [x] Out-of-scope and DNS-rebinding targets are rejected (tested).
- [x] Jobs show state, exit code, stdout, stderr; timeout and cancel work.
- [x] Scan and its scope confirmation, tool, profile, and proxy are stored and shown in history.
- [x] Proxy secrets are encrypted at rest and never returned by the API.
- [x] Proxy test reports all four outcomes.
- [x] Every job lifecycle event is in the audit log.
- [x] End-to-end against a local lab target: configure → run → raw output → parse → hosts/endpoints.

## STOP
No IP/proxy rotation, no stealth or anti-detection, no credential attacks, no exploitation, no free-form command input.
