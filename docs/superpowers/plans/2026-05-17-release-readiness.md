# Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the AI Test Platform production-ready with Docker Compose deployment, clean security posture, and documentation.

**Architecture:** One-shot full fix — security cleanup + Docker Compose (postgres + backend + frontend + nginx) + README + end-to-end verification.

**Tech Stack:** FastAPI, Vue 3, PostgreSQL 16, Nginx, Docker Compose

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `ai-project-back-end/.env.example` | Replace real secrets with placeholders |
| Modify | `ai-project-back-end/.env` | `git rm --cached` only |
| Create | `ai-project-back-end/.gitignore` | Exclude .env, .venv, __pycache__, logs, reports |
| Modify | `.gitignore` | Add .env, logs, docker-data, worktrees |
| Modify | `ai-project-back-end/app/core/config.py:21` | Remove hardcoded DB password default |
| Modify | `ai-project-back-end/app/scripts/seed_user.py` | Read password from env var |
| Modify | `ai-project_front_end/src/views/Register.vue:14` | Remove console.log |
| Create | `Dockerfile.backend` | Python 3.11 + pip install + uvicorn |
| Create | `Dockerfile.frontend` | Node 20 + npm build stage |
| Create | `docker-compose.yml` | 4 services: postgres, backend, frontend, nginx |
| Create | `nginx/default.conf` | Static files + /api reverse proxy |
| Create | `.env.docker` | Docker-specific env template |
| Create | `README.md` | Project documentation |

---

### Task 1: Security Cleanup — .env and .gitignore

**Files:**
- Modify: `ai-project-back-end/.env.example`
- Modify: `.gitignore`
- Create: `ai-project-back-end/.gitignore`

- [ ] **Step 1: Replace .env.example with placeholder values**

Write to `ai-project-back-end/.env.example`:

```
APP_NAME=ai-test-platform
ENV=local
DEBUG=false

API_PREFIX=/api

DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/ai_test_platform

CORS_ORIGINS=http://localhost:5173,http://localhost
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*

JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_chars_long
RUNNER_WORKSPACE_ROOT=./var/runners
RUNNER_PYTHON_EXECUTABLE=python
RUNNER_ALLURE_COMMAND=allure

LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_API_KEY=your_llm_api_key_here
```

- [ ] **Step 2: Create backend .gitignore**

Write to `ai-project-back-end/.gitignore`:

```
.env
.venv/
__pycache__/
*.pyc
*.pyo
*.log
var/
reports/
testcase/
backend-*.log
dist/
build/
*.egg-info/
```

- [ ] **Step 3: Update root .gitignore**

Write to `.gitignore`:

```
.worktrees/
docker-data/
.env
*.log
backend-*.log
node_modules/
dist/
.DS_Store
Thumbs.db
```

- [ ] **Step 4: Remove .env from git tracking**

Run:
```bash
cd D:/OtherProject/ai-project
git rm --cached ai-project-back-end/.env
```

Expected: `rm 'ai-project-back-end/.env'`

- [ ] **Step 5: Commit**

```bash
git add .gitignore ai-project-back-end/.gitignore ai-project-back-end/.env.example
git commit -m "security: remove .env from tracking, add .gitignore, clean .env.example"
```

---

### Task 2: Security Cleanup — Hardcoded Passwords

**Files:**
- Modify: `ai-project-back-end/app/core/config.py:21`
- Modify: `ai-project-back-end/app/scripts/seed_user.py`
- Modify: `ai-project_front_end/src/views/Register.vue:14`

- [ ] **Step 1: Fix config.py hardcoded database URL**

In `ai-project-back-end/app/core/config.py`, change line 21 from:

```python
    database_url: str = "postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_platform"
```

to:

```python
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform"
```

This removes the hardcoded password. The default uses `postgres:postgres` which is the standard PostgreSQL default. Real deployments override via `DATABASE_URL` env var.

- [ ] **Step 2: Fix seed_user.py hardcoded password**

Read `ai-project-back-end/app/scripts/seed_user.py` and find the line with `password="123456"`. Change it to read from env var:

```python
import os
# ...
password = os.getenv("SEED_USER_PASSWORD", "ChangeMe123!")
```

- [ ] **Step 3: Remove console.log from Register.vue**

In `ai-project_front_end/src/views/Register.vue`, find and delete the line:

```typescript
console.log('Register successful')
```

- [ ] **Step 4: Verify backend still starts**

Run:
```bash
cd D:/OtherProject/ai-project/ai-project-back-end
DEBUG=false python -c "from app.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Verify frontend builds**

Run:
```bash
cd D:/OtherProject/ai-project/ai-project_front_end
npm run build 2>&1 | tail -3
```

Expected: `built in Xs`

- [ ] **Step 6: Commit**

```bash
git add ai-project-back-end/app/core/config.py ai-project-back-end/app/scripts/seed_user.py ai-project_front_end/src/views/Register.vue
git commit -m "security: remove hardcoded passwords from config and seed script"
```

---

### Task 3: Docker — Dockerfile.backend

**Files:**
- Create: `Dockerfile.backend`

- [ ] **Step 1: Create backend Dockerfile**

Write to `Dockerfile.backend` (at project root `D:\OtherProject\ai-project\Dockerfile.backend`):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ai-project-back-end/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai-project-back-end/ .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 2: Test build**

Run:
```bash
cd D:/OtherProject/ai-project
docker build -f Dockerfile.backend -t ai-test-backend . 2>&1 | tail -5
```

Expected: `Successfully tagged ai-test-backend:latest`

- [ ] **Step 3: Commit**

```bash
git add Dockerfile.backend
git commit -m "feat: add backend Dockerfile"
```

---

### Task 4: Docker — Dockerfile.frontend

**Files:**
- Create: `Dockerfile.frontend`

- [ ] **Step 1: Create frontend Dockerfile**

Write to `Dockerfile.frontend` (at project root):

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app

COPY ai-project_front_end/package.json ai-project_front_end/package-lock.json* ./
RUN npm ci

COPY ai-project_front_end/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
```

- [ ] **Step 2: Test build**

Run:
```bash
cd D:/OtherProject/ai-project
docker build -f Dockerfile.frontend -t ai-test-frontend . 2>&1 | tail -5
```

Expected: `Successfully tagged ai-test-frontend:latest`

- [ ] **Step 3: Commit**

```bash
git add Dockerfile.frontend
git commit -m "feat: add frontend Dockerfile with multi-stage build"
```

---

### Task 5: Docker — Nginx Config

**Files:**
- Create: `nginx/default.conf`

- [ ] **Step 1: Create nginx config**

Create directory `nginx/` and write `nginx/default.conf`:

```nginx
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add nginx/
git commit -m "feat: add nginx reverse proxy config"
```

---

### Task 6: Docker — docker-compose.yml

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.docker`

- [ ] **Step 1: Create .env.docker**

Write to `.env.docker` (at project root):

```
APP_NAME=ai-test-platform
ENV=docker
DEBUG=false
API_PREFIX=/api
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/ai_test_platform
CORS_ORIGINS=http://localhost,http://localhost:80
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*
JWT_SECRET_KEY=change_this_to_a_real_secret_in_production
LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

- [ ] **Step 2: Create docker-compose.yml**

Write to `docker-compose.yml` (at project root):

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_test_platform
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    ports:
      - "5432:5432"

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env.docker
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"
    restart: unless-stopped

  nginx:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  pgdata:
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.docker
git commit -m "feat: add Docker Compose with postgres, backend, nginx"
```

---

### Task 7: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Write to `README.md` (at project root):

```markdown
# AI Test Platform

智能测试平台 — 需求分析、用例生成、接口自动化、缺陷管理

## 快速开始

### 前置条件

- Docker Desktop
- Git

### 一键启动

```bash
git clone <your-repo-url>
cd ai-test-platform
cp ai-project-back-end/.env.example ai-project-back-end/.env
# 编辑 .env 填入你的配置（数据库密码、JWT密钥、LLM API Key）
docker compose up -d
```

访问 http://localhost

### 本地开发（不用 Docker）

```bash
# 后端
cd ai-project-back-end
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp .env.example .env  # 编辑配置
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --reload

# 前端
cd ai-project_front_end
npm install
npm run dev
```

访问 http://localhost:5173

## 项目结构

```
ai-project-back-end/   FastAPI 后端
ai-project_front_end/  Vue 3 前端
nginx/                 Nginx 配置
docs/                  设计文档和 API 文档
docker-compose.yml     Docker Compose 配置
```

## 技术栈

- 后端: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- 前端: Vue 3 + Vite + TypeScript + Tailwind CSS
- 执行: pytest + Allure + k6
- AI: LLM 需求分析 + 用例生成
- 部署: Docker Compose + Nginx

## 环境变量

见 `ai-project-back-end/.env.example`，必填项：

| 变量 | 说明 |
|------|------|
| DATABASE_URL | PostgreSQL 连接串 |
| JWT_SECRET_KEY | JWT 签名密钥（>=32字符） |
| LLM_API_KEY | LLM API 密钥 |

## 运行测试

```bash
# 后端测试
cd ai-project-back-end
python -m pytest tests/ -v

# 前端构建验证
cd ai-project_front_end
npm run build
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add project README"
```

---

### Task 8: End-to-End Verification

- [ ] **Step 1: Docker Compose build**

Run:
```bash
cd D:/OtherProject/ai-project
docker compose build 2>&1 | tail -10
```

Expected: All images built successfully, no errors.

- [ ] **Step 2: Docker Compose up**

Run:
```bash
docker compose up -d
sleep 15
docker compose ps
```

Expected: All 3 services (postgres, backend, nginx) showing "Up" status.

- [ ] **Step 3: PostgreSQL health check**

Run:
```bash
docker compose exec postgres pg_isready -U postgres
```

Expected: `accepting connections`

- [ ] **Step 4: Backend migrations**

Run:
```bash
docker compose exec backend python -m alembic current
```

Expected: `0022_add_project_ci_token_policy (head)`

- [ ] **Step 5: Backend API health**

Run:
```bash
curl -s http://localhost/api/v1/health 2>&1 || curl -s http://localhost:8000/api/v1/health 2>&1
```

Expected: HTTP 200 response.

- [ ] **Step 6: Frontend page loads**

Open browser to `http://localhost`. Verify login page renders.

- [ ] **Step 7: Register and login**

In browser: register a new user, then login. Verify redirect to dashboard.

- [ ] **Step 8: Create project**

Create a new project from the dashboard. Verify it appears in the project list.

- [ ] **Step 9: Import API collection**

Go to API Collections, import an OpenAPI JSON file. Verify endpoints listed.

- [ ] **Step 10: Run API request**

Select an endpoint, click Send. Verify response panel shows result.

- [ ] **Step 11: Backend tests in container**

Run:
```bash
docker compose exec backend python -m pytest tests/ -q
```

Expected: All tests pass.

- [ ] **Step 12: Cleanup**

Run:
```bash
docker compose down
```

Expected: All containers stopped and removed.
