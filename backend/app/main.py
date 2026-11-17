"""FastAPI 入口。"""

from fastapi import FastAPI

from backend.app.api.v1 import api_router
from backend.app.db import init_db

app = FastAPI(
    title="学术论文研究与生成 AI 智能体",
    version="0.1.0",
)
app.include_router(api_router)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/health")
def api_health():
    return {"code": "OK", "message": "服务可用", "data": {"status": "ok"}}
