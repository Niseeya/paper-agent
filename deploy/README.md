# 本地部署

账号与总览见仓库根目录 [`README.md`](../README.md)（管理员 `admin` / `Admin1234`，测试用户 `demo_tester` / `Demo1234`）。

## 1. 准备环境

```bash
cd 论文智能体
cp .env.example .env
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate paperAgent   # Python 3.12；勿用 guopeiNeu(3.15)
# 缺包时优先清华源；仍卡住再 export all_proxy=socks5://127.0.0.1:7890
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r backend/requirements.txt
```

## 2. 数据库

**推荐（本机 conda Postgres）**：

```bash
bash scripts/pg_local.sh start          # 端口 5433，数据目录 data/pgdata
export DATABASE_URL=postgresql+psycopg://paper_agent@localhost:5433/paper_agent
python -c "from backend.app.db import init_db; init_db()"
```

有 Docker 时：

```bash
docker compose -f deploy/docker-compose.yml up -d db redis
# .env 使用 postgresql+psycopg://paper_agent:paper_agent@localhost:5432/paper_agent
```

未设置 `DATABASE_URL` 时回退 SQLite：`data/paper_agent.db`。

## 3. 同步预置论文

`论文/` 目录新增 PDF 后执行：

```bash
python scripts/sync_corpus.py
python scripts/sync_corpus.py --dry-run
python scripts/import_corpus_to_db.py   # 解析产物写入正式库，供 S2 检索
```

结果写入：

- `data/corpus_state/manifest.json` 已入库清单
- `data/corpus_state/last_sync_report.json` 最近一次报告
- `data/corpus_state/failed.jsonl` 失败记录
- `data/storage/papers/<id>/` 解析产物
- `data/paper_agent.db`（默认）正式表：papers / document_files / knowledge_chunks

## 4. 向量化与混合检索

技术栈默认：**bge-m3 嵌入** + **独立 Reranker** + **Postgres pgvector**（`vector(1024)` + HNSW）。

本机 conda Postgres 若尚无扩展，可对应当前 `pg_config` 源码编译安装 pgvector（已验证 0.8.0），然后：

```bash
export DATABASE_URL=postgresql+psycopg://paper_agent@localhost:5433/paper_agent
psql -h localhost -p 5433 -U paper_agent -d paper_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"
python scripts/embed_corpus.py
# 若早期用 JSON 存过向量，迁移一次：
python scripts/migrate_embeddings_to_pgvector.py
```

## 5. Skill 独立测试

```bash
python -m pytest backend/tests/skills/ -q
```

## 6. 启动 API

```bash
export JWT_SECRET=dev-change-me
export DATABASE_URL=postgresql+psycopg://paper_agent@localhost:5433/paper_agent
export EMBEDDING_BACKEND=local EMBEDDING_LOCAL_MODEL=BAAI/bge-m3 EMBEDDING_LOCAL_FILES_ONLY=1
export RERANKER_BACKEND=local RERANKER_LOCAL_MODEL=BAAI/bge-reranker-base RERANKER_LOCAL_FILES_ONLY=1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 另开终端
cd frontend/web && npm run dev
# Web http://127.0.0.1:5173  ·  API http://127.0.0.1:8000/api/v1/health
```
