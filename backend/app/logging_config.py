"""structlog による構造化ログ設定。

出力は JSON。標準出力に流す。
将来 Cloud Logging に流す前提（Phase 6/7）。

events テーブル（ビジネスイベントの永続ログ）とは別物。
- events テーブル: 「タスクが完了した」等のビジネス上の出来事。分析目的で追記専用。
- structlog: HTTP アクセス・処理経過・エラー等のシステムログ。運用目的、揮発OK。
"""
import logging
import sys

import structlog

from app.config import settings


def setup_logging() -> None:
    """アプリ起動時に1回だけ呼ぶ。"""
    # 標準 logging のレベルを揃える（uvicorn などのログも同じレベルに）
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # ContextVars（例：request_id）
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """モジュール内での logger 取得ヘルパ。"""
    return structlog.get_logger(name)
