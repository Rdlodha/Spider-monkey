.PHONY: check lint test

check: lint test

lint:
	cd backend && python -m ruff check app tests
	cd frontend && npx eslint src

test:
	cd backend && python -m pytest tests/ -v
	cd frontend && npx vitest run
