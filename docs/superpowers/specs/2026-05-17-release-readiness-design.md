# Release Readiness Design

## Context

AI Test Platform (based on ai-project fork) has completed Phase 0-8 feature development. All 55 backend tests pass, frontend builds cleanly, 22 database migrations applied. The codebase is structurally sound but has security/configuration hygiene issues blocking production deployment.

**Goal:** Make the project production-ready with Docker Compose deployment, clean security posture, and documentation.

**Approach:** One-shot full fix (approach A) — security cleanup + Docker Compose + README + end-to-end verification in a single workflow.

## Section 1: Security Cleanup

### Problem

- `.env` file with real secrets (DeepSeek API key, DB password, JWT secret) is tracked in git
- `.env.example` contains the same real API keys
- No `.gitignore` in backend directory
- Hardcoded passwords in `config.py` and `seed_user.py`
- `console.log` in production frontend code

### Solution

| File | Action |
|------|--------|
| `.env` | `git rm --cached` — remove from tracking, keep local file |
| `.env.example` | Replace all real values with placeholders (`your-api-key-here`, `your-db-password`) |
| `ai-project-back-end/.gitignore` | Create: exclude `.env`, `.venv/`, `__pycache__/`, `*.log`, `var/`, `reports/`, `testcase/` |
| Root `.gitignore` | Add `.env`, `*.log`, `docker-data/`, `.worktrees/`, `backend-*.log` |
| `ai-project-back-end/app/core/config.py` | Remove hardcoded password from `database_url` default; require env var |
| `ai-project-back-end/app/scripts/seed_user.py` | Read password from `SEED_USER_PASSWORD` env var, default to prompting |
| `Register.vue` | Remove `console.log('Register successful')` |

### Not doing

- No git history rewrite (local project, history won't be public)
- No API key rotation (user's responsibility)

## Section 2: Docker Compose Containerization

### Architecture

```
                    ┌─────────────┐
                    │   Nginx     │ :80
                    │  (frontend)  │
                    │  /api → :8000│
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │                         │
      ┌───────▼───────┐      ┌─────────▼─────────┐
      │   PostgreSQL   │      │   FastAPI Backend   │
      │    :5432       │      │    :8000            │
      └───────────────┘      └────────────────────┘
```

### Files to create

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 4 services: postgres, backend, frontend, nginx |
| `Dockerfile.backend` | Python 3.11-slim, pip install, uvicorn entrypoint |
| `Dockerfile.frontend` | Node 20-alpine, npm build, copy to nginx |
| `nginx/default.conf` | Serve frontend static at `/`, proxy `/api` to backend:8000 |
| `.env.docker` | Docker-specific env template (no real secrets) |

### Service details

**postgres:**
- Image: `postgres:16-alpine`
- Volume: `pgdata:/var/lib/postgresql/data` (named volume for persistence)
- Healthcheck: `pg_isready -U postgres`

**backend:**
- Build from `Dockerfile.backend`
- Depends on: postgres (healthy)
- Entrypoint: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Env: loaded from `.env.docker`

**frontend:**
- Build from `Dockerfile.frontend` (multi-stage: build + copy to nginx)
- No runtime container — static files served by nginx

**nginx:**
- Image: `nginx:alpine`
- Ports: `80:80`
- Volume mount: frontend build output from frontend build stage
- Config: `nginx/default.conf`

## Section 3: README Documentation

Create `README.md` at project root covering:

1. Project description (one paragraph)
2. Quick start with Docker Compose (`docker compose up -d`)
3. Local development setup (without Docker)
4. Project structure overview
5. Technology stack
6. Environment variables reference (pointing to `.env.example`)

## Section 4: Verification Plan

| Step | Check | Pass Criteria |
|------|-------|--------------|
| 1 | `docker compose build` | No errors, images built |
| 2 | `docker compose up -d` | All 4 containers running |
| 3 | PostgreSQL health | `pg_isready` returns accepting connections |
| 4 | Backend migrations | `alembic current` shows 0022 |
| 5 | Backend API | `curl localhost/api/v1/health` returns 200 |
| 6 | Frontend page | Browser opens `localhost`, shows login page |
| 7 | Register/Login | Create user and login succeeds |
| 8 | Create project | New project appears in list |
| 9 | API collections | Import OpenAPI, endpoints listed |
| 10 | Run request | Send button executes, response shown |
| 11 | Backend tests | `docker compose exec backend pytest` all pass |

**Acceptance:** All 11 steps pass = production ready.
