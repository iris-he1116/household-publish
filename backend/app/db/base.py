"""SQLAlchemy の共通基底クラス。

すべてのモデルはこの `Base` を継承する。
Alembic はこの `Base.metadata` を読んで、DB との差分を検出する。
"""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# 制約・インデックス・キーの命名規約
# これがないと、循環 FK を持つスキーマで drop_all/downgrade がコケる。
# 詳細: https://alembic.sqlalchemy.org/en/latest/naming.html
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """すべてのテーブルモデルの親クラス。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
