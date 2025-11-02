# Repository Guidelines

## Project Structure & Module Organization
The repository is split between `backend/` (FastAPI) and `frontend/` (Next.js). Backend modules live under `backend/app`, with `api/` for routers, `services/` and `rag/` for domain logic, and `tasks/` for async jobs. Database configuration and migrations are handled in `backend/alembic/`. The Next.js app keeps pages and server actions in `frontend/app`, reusable UI in `frontend/components`, hooks in `frontend/hooks`, and shared utilities in `frontend/lib`. Support scripts live in `scripts/`, and architectural notes stay in `docs/`.

## Build, Test, and Development Commands
- `./scripts/dev.sh`: boots PostgreSQL, Qdrant, and Redis via Docker with health checks.
- `cd backend && uvicorn app.main:app --reload`: launches FastAPI with live reload.
- `cd backend && ruff check app`: runs the Python linter; apply `ruff format` if needed.
- `cd backend && pytest`: executes backend unit and integration tests (ensure the `dev` extras are installed).
- `cd frontend && npm run dev`: starts the Next.js dev server on port 3000; use `npm run build` before containerizing.
- `cd frontend && npm run lint`: enforces the ESLint ruleset before opening a PR.

## Coding Style & Naming Conventions
Python code follows Ruff’s configuration: 4-space indentation, 100-character lines, double quotes, and import sorting. Use snake_case for modules and functions, CamelCase for Pydantic models, and PascalCase for class-based services. Frontend files are TypeScript-first; prefer functional React components, colocated CSS via Tailwind, and kebab-case filenames inside `app/` route segments. Keep shared UI under `components/` with PascalCase directories, and colocate component-specific hooks in matching `hooks/` files.

## Testing Guidelines
Place backend tests under `backend/tests`, mirroring the package layout (`tests/api`, `tests/services`, etc.). Name files `test_<target>.py` and rely on Pytest fixtures for database or Redis setup. When checking vector-search behavior, seed minimal datasets via factories instead of hitting live services. Frontend component or integration tests should sit beside source files as `<Component>.test.tsx`; use React Testing Library patterns and stub network calls with MSW. Aim to cover new request handlers and UI flows before merging.

## Commit & Pull Request Guidelines
Follow the concise message style in history: lowercase, present tense summaries prefixed by scope when useful (e.g., `backend: add upload validation`). Each PR should explain the change, list verification steps (`pytest`, `npm run lint`, screenshots for UI updates), and link related issues. Rebase before review, ensure CI-equivalent commands pass locally, and call out follow-up work in the description.
