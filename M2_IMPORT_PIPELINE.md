# M2: Import Pipeline

**Goal:** `Tool output file → Parser → Normalized objects → Postgres → UI`. Import only. Nothing executes tools.

Split into two vertical slices. Ship slice A fully (including UI) before starting B.

## Slice A: Nmap
1. Migration: `Scan`, `Host`, `Service` (schemas in `00_CONTEXT.md`, with unique keys).
2. Parser interface in `parsers/`:
   ```text
   Parser: name, can_parse(content: bytes) -> bool, parse(content: bytes) -> ParseResult
   ParseResult: hosts[], services[], endpoints[], errors[]
   ```
   Add a registry that picks a parser by sniffing content, with a manual override.
3. `NmapParser` for Nmap XML only, using `defusedxml`. Extract host, IP, hostname, port, protocol, state, service, product, version. Never parse human-formatted output.
4. Import service: save raw file to `data/raw/<sha256>`, create `Scan(status=running)`, parse, **upsert** results (set `first_seen` once, update `last_seen`), then set `completed` or `failed` with `error`. Enforce an upload size limit.
5. API: `POST /api/scans/import` (multipart: project, target, tool, file), `GET /api/scans`, `GET /api/scans/{id}`, `GET /api/hosts`, `GET /api/hosts/{id}`.
6. UI: Scans page with Import Scan, Scan History, Scan Details (tool, target, status, hosts, ports, services, parse errors shown clearly, link to raw output).
7. Tests with committed fixtures: normal scan, scan with no open ports, malformed XML, XXE attempt, duplicate re-import (must not duplicate rows).

## Slice B: Web directory results
1. Migration: `Endpoint`.
2. `FeroxParser` for Feroxbuster **JSON lines** (preferred) and `GobusterParser` for the simple text format. Each yields `Endpoint(url, status_code, content_length, source_tool, discovered_at)`.
3. Normalize the URL: lowercase scheme/host, strip default ports, strip fragments. Keep path and query.
4. Same import path and upsert rules as Slice A; endpoints appear in Scan Details.
5. Tests with fixtures for each format plus malformed lines (skip the line, record an error, continue).

## Definition of Done
- [ ] Postgres stores scans, hosts, services, endpoints.
- [ ] Nmap XML, Feroxbuster JSON, and Gobuster text import end to end.
- [ ] Hosts, ports, services, and endpoints appear in the UI.
- [ ] Raw output is preserved with SHA-256; re-importing identical output is detected.
- [ ] Re-import creates no duplicates and updates `last_seen`.
- [ ] Parse errors are visible in the UI.
- [ ] All parsers produce the same normalized schema.
- [ ] Parser tests run against fixtures and pass.

## STOP
No tool execution, no auto scanning, no job system. Import and analyze existing files only.
