"""FastAPI アプリのエントリポイント。

起動:
    cd backend
    uv run uvicorn app.main:app --reload
Swagger UI:
    http://localhost:8000/docs
"""
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from app.logging_config import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時と終了時のフック。"""
    setup_logging()
    log = get_logger("app.main")
    log.info("app.starting")
    yield
    log.info("app.shutting_down")


app = FastAPI(
    title="家計清算アプリ API",
    description="ありす／ひつじ 専用",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """全リクエストに request_id を付与して構造化ログに残す。"""
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    log = get_logger("app.http")
    log.info("http.request.received")
    try:
        response = await call_next(request)
    except Exception:
        log.exception("http.request.failed")
        raise
    log.info("http.request.finished", status_code=response.status_code)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/healthz", tags=["_ops"])
def healthz() -> dict:
    """ヘルスチェック。DB 接続まで見るのは Phase 5 で。"""
    return {"status": "ok"}


# --- 各機能のルーター登録（後で埋める） ---
from app.api import auth, categories, expenses, settlements, paypay_import  # noqa: E402

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(settlements.router)
app.include_router(paypay_import.router)
