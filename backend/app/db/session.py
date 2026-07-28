"""SQLAlchemy のエンジン・セッション管理。

api/deps.py の `get_db_session` から使う。
"""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


engine = create_engine(
    settings.database_url,
    # pool_pre_ping: 接続が生きているか毎回チェック（コンテナ再起動で切れた接続を検出）
    pool_pre_ping=True,
    # echo: True にすると SQL を全部ログ出力（デバッグ用、普段は False）
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,  # commit 後もオブジェクトの属性にアクセスできるように
)


def get_db_session() -> Iterator[Session]:
    """1リクエスト = 1セッション の Dependency。

    使い方:
        @router.get(...)
        def handler(session: Session = Depends(get_db_session)):
            ...

    リクエスト終了時に自動で close される。
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
