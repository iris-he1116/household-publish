"""ユーザーのパスワードを変更する。

    uv run python scripts/set_password.py alice
    uv run python scripts/set_password.py hitsuji

パスワードは対話的に（画面に表示されない形で）入力する。
コマンドライン引数では受け取らない。シェルの履歴に残ってしまうため。

## 何をするか

1. 新しいパスワードを2回聞いて、一致を確認
2. bcrypt でハッシュ化して users.password_hash を更新
3. tokens_valid_after を今の時刻にする
   → **そのユーザーの既存ログインは全て無効になる**（全端末でログアウト）

## .env との関係

`.env` の ALICE_PASSWORD / HITSUJI_PASSWORD は、初回の seed マイグレーションが
DB に投入するときにだけ使われる。このスクリプトで変更しても .env は書き換えない
（DB が正）。混乱を避けたい場合は .env 側の値も手で直すか、消しておく。
"""
import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.auth import hash_password  # noqa: E402

MIN_LENGTH = 8


def main() -> int:
    if len(sys.argv) != 2:
        print(f"使い方: uv run python {Path(__file__).name} <username>")
        print("  例: uv run python scripts/set_password.py alice")
        return 1

    username = sys.argv[1]
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).one_or_none()
        if user is None:
            names = [u.username for u in session.query(User).all()]
            print(f"ユーザー '{username}' が見つかりません。存在するのは: {', '.join(names)}")
            return 1

        print(f"{user.name}（{user.username}）のパスワードを変更します。")
        first = getpass.getpass("新しいパスワード: ")
        if len(first) < MIN_LENGTH:
            print(f"短すぎます（{MIN_LENGTH} 文字以上にしてください）")
            return 1
        second = getpass.getpass("もう一度入力: ")
        if first != second:
            print("2回の入力が一致しません")
            return 1

        user.password_hash = hash_password(first)
        # 既存のログインを全て無効にする（変更前のトークンで入られないように）
        user.tokens_valid_after = datetime.now(timezone.utc)
        session.commit()

        print(f"✓ {user.name} のパスワードを変更しました。")
        print("  この人の既存のログインは全て切れたので、次回はログインし直しになります。")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
