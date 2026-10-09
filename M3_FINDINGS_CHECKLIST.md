# M3: Findings, Checklists, Correlation

**Goal:** Turn imported data into something a tester can work from.

## Tasks
1. **Findings:** migration for `Finding`, `FindingLink`, `Evidence` (schemas in `00_CONTEXT.md`). CRUD API and UI: create, edit, change severity/status, notes, tags, `is_interesting` toggle on hosts/services/endpoints. "Create finding from this endpoint/service" pre-fills the title, source, and links.
2. **Evidence (done properly once, here):** upload a file or paste text. Validate type (png/jpg/txt/json/log; reject HTML/SVG), size limit, rename to a random name, store under `data/evidence/` (not served statically), save SHA-256 and size. Serve through an authenticated endpoint with a safe `Content-Type` and `Content-Disposition: attachment`.
3. **Checklists:** migration for template, template items, and per-target `ChecklistProgress`. Seed templates (Web, Network, Database) via a seed script. Progress rows are created per target from the template; editing a template later does not rewrite old progress. States and per-item notes persist.
   - Web: technologies, web server, directories, files, APIs, auth pages, interesting status codes, exposed config, robots.txt, sitemap.xml.
   - Network: live hosts, open ports, services, versions, unusual ports, remote administration, database services.
4. **Correlation (deterministic only):**
   - Endpoint URL → `(scheme, host, port)`; default ports 80/443 applied. Match to a `Service` on the same host/port; match by IP, then by hostname.
   - Rule table in code, e.g. open `3306/mysql` → suggest finding "MySQL service exposed (INFO)"; remote-admin ports → suggest a review item.
   - Output is a **suggestion** the user accepts or dismisses; nothing is auto-created as truth. Show the tree `Host → Service → Endpoints`.
5. **Dashboard:** counts for hosts, open ports, endpoints, findings, critical findings, checklist progress per target. Optional: "new since last scan" using `first_seen`.

## Definition of Done
- [ ] Findings can be created, edited, linked to multiple entities, and filtered by severity/status/tag.
- [ ] Evidence upload works and rejects unsafe types.
- [ ] Checklist progress persists and survives reload.
- [ ] Sample Nmap + Ferox import shows `Host → HTTP → /admin, /api, /backup`.
- [ ] A finding created from an endpoint can be tied to a checklist item marked complete.
- [ ] Suggested correlations can be accepted/dismissed.
- [ ] Dashboard numbers match the database (tested).

## STOP
No auto-exploitation, no auto-verification of vulnerabilities, no AI-based correlation.
