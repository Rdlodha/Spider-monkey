# Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Stack: React+Vite+JS, Tailwind, shadcn/ui, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL | Modern, well-supported, fits single-dev workbench |
| 2 | Local-only deployment: backend on 127.0.0.1, CORS to http://localhost:5173 only, random bearer token | Single-user tool; prevents DNS-rebinding and cross-site API abuse |
| 3 | One implicit user "local"; actor stored in AuditLog | Allows multi-user extension later without reshaping data |
| 4 | Raw files stored on disk by SHA-256 hash; path+hash in DB | Avoids text-column bloat; enables integrity verification |
| 5 | All parsers return normalized objects; DB layer is tool-agnostic | Decouples parsing from persistence; easy to add new tools |
| 6 | Parser registry with automatic content sniffing & tool override | Enables seamless drag-and-drop imports with explicit manual fallback |
| 7 | Common Endpoint schema with URL normalization (scheme/host lowercase, default ports stripped) | Eliminates duplicate URL variations from directory brute-forcing tools |
