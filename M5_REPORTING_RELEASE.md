# M5: Reporting, Hardening, Release

**Goal:** A coherent, demonstrable, portfolio-quality local app.

## Tasks
1. **Project dashboard:** overview of targets, hosts, services, endpoints, findings, checklist, scans, evidence.
2. **Attack-surface graph:** React Flow (or Cytoscape): `Target → Host → Port/Service → Endpoint → Finding`. Click a node to open details. Keep it basic; collapse large endpoint sets.
3. **Reports:** Jinja2 → Markdown, then PDF (WeasyPrint) from the same template. Sections: project, scope, methodology, targets, hosts, services, endpoints, findings, checklist progress, evidence, recommendations. Option to exclude `FALSE_POSITIVE` and to redact patterns (tokens, passwords) in evidence. Escape all user text before it enters HTML/Markdown.
4. **Security review (checklist, record the result in `docs/SECURITY.md`):**
   - Local-only binding and token check still enforced; CORS exact-origin.
   - Input validation on every endpoint (Pydantic).
   - Command construction (re-audit M4 tests).
   - Path traversal on uploads, raw output, evidence, and report download.
   - SSRF: proxy test and any outbound URL fetch.
   - Upload validation; sanitized rendering of Markdown/evidence in the UI (no raw HTML).
   - Secret handling and Git history scan (e.g. gitleaks).
   - Database user has only needed permissions.
   - Error responses leak no stack traces or file paths.
   - Dependency audit (`pip-audit`, `npm audit`).
5. **Audit log UI:** filterable view of `actor, ts, action, target, tool, result`; append-only (no edit/delete endpoints).
6. **Demo + lab:** `docker-compose.lab.yml` with intentionally vulnerable targets (e.g. DVWA, Juice Shop) bound to localhost, plus a seed script with sample projects and fixtures, so the dashboard looks good on first run.
7. **Tests:** parsers, DB/upserts, API (including 401 without token), checklist, finding creation, proxy config/encryption, scope validation, command construction. One end-to-end happy path.
8. **UX cleanup:** loading, empty, and error states; responsive layout; confirmation dialogs; toasts; accessibility basics (labels, focus, contrast); dark mode.
9. **README:** purpose, architecture diagram, screenshots, install, env vars, DB setup, running both apps, supported tools and parser formats, proxy config, **threat model** (local-only assumptions, what the token protects), security warnings, authorized-use notice, limitations, roadmap.

## Definition of Done
- [x] Full workflow works: create project → scope → (proxy) → run/import → parse → correlate → checklist → findings → evidence → graph → report.
- [x] Report generates in Markdown and PDF.
- [x] `docs/SECURITY.md` review complete with fixes applied.
- [x] Audit log viewable and append-only.
- [x] Automated tests pass; lint passes.
- [x] README complete; a fresh clone can be running by following it.
- [x] Demo data and lab compose work.

## Final workflow
```text
Create Project → Scope → Proxy → Run/Import → Parse → Normalize → Correlate
→ Checklist → Findings → Evidence → Attack Surface → Report
```

## After V1 (parked, not now)
Scan diffing UI, more tools, AI-assisted suggestions, multi-user auth if ever hosted.
