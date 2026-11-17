# 论文智能体

基于 RAG 与多 Skill（S1～S10）协同的学术论文研究与生成系统。  
面向单一研究领域：公用知识库检索与引用约束下的选题、大纲、写作、润色、核查与导出。

## 账号（本地联调）

| 角色 | 用户名 | 密码 | 说明 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `Admin1234` | 可进「管理后台」：模型/API Key、提示词、项目删除 |
| 普通测试用户 | `demo_tester` | `Demo1234` | 走完整成稿主路径；不能删除他人/预置论文，不能进管理后台 |

也可在登录页自行注册普通用户。密码连续失败 5 次会锁定 10 分钟。

> 以上账号仅用于本地开发与演示，上线前请改密或停用。不要把生产密钥写进仓库。

## 访问地址

| 服务 | 地址 |
| --- | --- |
| Web 前端 | http://127.0.0.1:5173 |
| API | http://127.0.0.1:8000 |
| 健康检查 | http://127.0.0.1:8000/api/v1/health |
| API 文档 | http://127.0.0.1:8000/docs |
| 管理后台 | 管理员登录后打开 http://127.0.0.1:5173/admin |

## 快速启动

```bash
cd 论文智能体
cp .env.example .env   # 按需修改；对话模型 Key 建议在管理后台配置

source /opt/anaconda3/etc/profile.d/conda.sh
conda activate paperAgent   # Python 3.12；勿用 guopeiNeu

# 数据库（本机 Postgres 默认 5433）
bash scripts/pg_local.sh start
export DATABASE_URL=postgresql+psycopg://paper_agent@localhost:5433/paper_agent
export JWT_SECRET=dev-change-me
python -c "from backend.app.db import init_db; init_db()"

# API
export EMBEDDING_BACKEND=local EMBEDDING_LOCAL_MODEL=BAAI/bge-m3 EMBEDDING_LOCAL_FILES_ONLY=1
export RERANKER_BACKEND=local RERANKER_LOCAL_MODEL=BAAI/bge-reranker-base RERANKER_LOCAL_FILES_ONLY=1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 另开终端：前端
cd frontend/web && npm install && npm run dev
```

更完整的部署、入库与向量化步骤见 [`deploy/README.md`](deploy/README.md)。  
预置论文增量更新见 [`docs/预置论文更新流程.md`](docs/预置论文更新流程.md)。

## 主路径（普通用户）

```text
登录 → 创建项目 → 知识库检索/上传
  → 生成并确认大纲 → 按节写作（可重写本节 / 重写全文）
  → 润色确认 → 引用核查（L1/L2）→ 草稿或定稿导出
```

独立工具（对比 / 研究空白）：顶栏「研究工具」，或 `/tools/analysis`。  
研究方向筛选在「公用知识库」页。

## 管理员能力

使用 `admin` 登录后进入 **/admin**：

1. **对话模型**：Endpoint、模型名、API Key（脱敏展示）、启用、连通测试  
2. **提示词**：S7 大纲 / S8 写作 / polish 润色的 system 提示词（保存为新版本）  
3. **项目运维**：查看全部项目并删除（仅删项目文稿，公用库论文保留）

运行时以库内配置为准；`.env` 中的 `LLM_*` 仅在库空时作首次种子。  
正式引用仍强制限定公用知识库已索引论文，定稿前须通过 L1/L2 核查。

## 技术栈（默认）

| 层 | 选择 |
| --- | --- |
| Web | React + TypeScript + Vite + Ant Design |
| 后端 | Python 3.12、FastAPI、SQLAlchemy 2.x |
| 数据库 | PostgreSQL + pgvector + FTS（本机默认端口 5433） |
| 检索 | 关键词 + bge-m3 向量 + Reranker |
| 对话 | OpenAI 兼容接口（如 DeepSeek），管理端可配 |
| 导出 | DOCX / PDF 等 |

开发约定与任务清单见 [`AGENTS.md`](AGENTS.md)。需求以 [`docs/需求规格说明书_V1.0.docx`](docs/需求规格说明书_V1.0.docx) 为准。文档索引见 [`docs/README.md`](docs/README.md)。

## Skill 独立测试

```bash
conda activate paperAgent
export DATABASE_URL=postgresql+psycopg://paper_agent@localhost:5433/paper_agent
python -m pytest backend/tests/skills/ -q
```

## 目录速览

```text
backend/              API、Skill、工作流、适配器、测试
frontend/web/         Web 客户端
deploy/               Docker Compose 与样例配置
scripts/              语料同步、向量化、本地 PG、SRS 生成
docs/                 需求 / 设计说明书与操作说明
论文/                 预置 PDF（经脚本入库，勿手拷进库；本地保留不推仓库）
samples/              本地样例 PDF（如英文论文，不走预置入库）
data/                 运行时数据（本地，不推仓库）
```

## 安全提示

- 不要把真实 `LLM_API_KEY`、数据库口令、JWT 密钥提交进 Git（`.env` 已忽略）  
- 管理端返回的 API Key 仅为脱敏形式；改 Key 请在管理后台粘贴新值  
- 演示账号请勿用于公网环境
