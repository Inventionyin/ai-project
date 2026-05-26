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
| SEED_USER_PASSWORD | Seed user password (default: ChangeMe123!) |

## 运行测试

```bash
# 后端测试
cd ai-project-back-end
python -m pytest tests/ -v

# 前端构建验证
cd ai-project_front_end
npm run build
```

## 验收与生产检查

```powershell
# 统一运营入口：查看所有可用动作
.\scripts\operate.ps1 -Action help

# 本地一键门禁：测试库迁移 + 后端 pytest + 前端构建 + generated Playwright E2E
.\scripts\operate.ps1 -Action local-gate

# 只跑真实后端 E2E
.\scripts\operate.ps1 -Action backend-e2e

# 生产公开可达性检查
.\scripts\operate.ps1 -Action production

# 验收交付材料与非侵入式 dry-run 检查
.\scripts\operate.ps1 -Action delivery-check
```

生产备份与恢复演练脚本见 `scripts/backup-production-postgres.sh` 和
`scripts/verify-production-backup.sh`，完整交付清单见
`docs/PRODUCTION_ACCEPTANCE_CHECKLIST.md`。

当前验收版本交付包见 `docs/final-delivery-package-20260526.md`，现场演示路线见
`docs/demo-script-20260526.md`，外部系统与生产复跑证据见
`docs/operations-rerun-20260526.md`。

## 开发规范

- 项目开发规范：`docs/development-standards.md`
- 测试规范：`docs/testing-standards.md`
- AI 协作开发规则：`docs/ai-coding-rules.md`
- 最终验收推进表：`docs/final-acceptance-roadmap.md`

后续人工或 AI 继续开发时，默认先按上述规范检查目录、接口、页面入口、测试和验收证据。
