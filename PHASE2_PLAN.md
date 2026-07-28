# Phase 2 実行計画：DB を開店できる状態にする

作成: 2026-07-20
参照: `DESIGN.md` §4（データモデル）／§5（ディレクトリ構成）／`/Users/sibei.he/Downloads/CURRICULUM.md` Phase 2

---

## 0. Phase 2 のゴール

Phase 2 の終わりで達成される状態：

```
✓ 厨房（PostgreSQL）が動いていて、
✓ メニュー（6つのテーブル）が全部揃っていて、
✓ ウェイター（SQLAlchemy）が Python 側に配属されていて、
✓ 常連客（ありす／ひつじ）が登録されていて、
✓ psql で覗いたら、DESIGN.md §4 と全く同じ形になっている

まだ:
✗ お客さんは注文できない（= API はまだない、Phase 3）
✗ 画面はない（Phase 4）
```

つまり、Phase 2 は「**開店準備**」。まだお客さん（フロントエンド）が来ない状態で、厨房とメニューを完璧に整える。

---

## 1. 大枠：レストランの比喩

| 現実世界 | このアプリでの実体 |
| :---- | :---- |
| 厨房 | **PostgreSQL**（DB そのもの） |
| 厨房を建てる場所 | **Podman コンテナ**（隔離された箱） |
| ウェイター（通訳） | **SQLAlchemy**（ORM = Python と DB の橋渡し） |
| ウェイターへの日本語オーダー | Python コード（`session.add(expense)` など） |
| 厨房用の伝票 | SQL |
| メニューブック | **SQLAlchemy モデル定義**（`models.py`） |
| メニュー更新の手順書 | **Alembic マイグレーション**（`alembic/versions/*.py`） |
| 「今どこまで反映済みか」の記録 | `alembic_version` テーブル（DB 自身の「しおり」） |

---

## 2. 6ステップの実装フロー

### ステップ1：厨房を建てる（Podman で PostgreSQL コンテナ起動）

**やること**：`compose.yaml` を書いて、コマンド1発で DB を立ち上げる

**書くファイル**（1個だけ）：`alice_work/compose.yaml`

```yaml
services:
  db:
    image: postgres:16
    container_name: household_db
    environment:
      POSTGRES_DB: household
      POSTGRES_USER: household_user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U household_user -d household"]
      interval: 5s
      timeout: 3s
      retries: 5
    secrets:
      - db_password
volumes:
  db_data:
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

**打つコマンド**：
```bash
mkdir -p secrets
echo "<好きなパスワード>" > secrets/db_password.txt
chmod 600 secrets/db_password.txt
echo "secrets/" >> .gitignore
podman compose up -d
```

**出るもの（検証）**：
```
$ podman ps
CONTAINER ID   IMAGE          STATUS                    NAMES
xxxxxxxxxxxx   postgres:16    Up 30 seconds (healthy)   household_db
```

**所要時間の目安**：初回は30分〜1時間（Podman の初期セットアップでハマる可能性）

---

### ステップ2：Python プロジェクトの初期化

**やること**：`backend/` ディレクトリを作って依存を入れる

**書くファイル**：
- `backend/pyproject.toml`（依存宣言）
- `backend/.env`（DB接続情報、`.gitignore` 対象）
- `backend/app/__init__.py`（空でOK）
- `backend/app/db/__init__.py`（空でOK）

依存の目安（pyproject.toml の抜粋）：
```toml
[project]
dependencies = [
  "fastapi",
  "sqlalchemy>=2.0",
  "alembic",
  "psycopg[binary]",
  "pydantic-settings",  # .env 読み込み用
]
```

**打つコマンド**：`cd backend && uv sync`（uv 使わないなら `pip install -e .`）

**出るもの**：`.venv/` ができて、依存パッケージがインストール済み

**所要時間**：15〜30分

---

### ステップ3：メニューを書く（SQLAlchemy モデル定義）

**やること**：DESIGN.md §4.2 の6テーブルを Python クラスとして書く

**書くファイル**：`backend/app/db/base.py`（Base クラス）、`backend/app/db/models.py`（6モデル）

**models.py のパターン例**（`expenses`）：
```python
from datetime import date, datetime
from sqlalchemy import ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    paid_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[int] = mapped_column(
        CheckConstraint("amount > 0"), nullable=False
    )
    occurred_on: Mapped[date] = mapped_column(nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    payment_method: Mapped[str] = mapped_column(
        CheckConstraint(
            "payment_method IN ('cash','credit_card','paypay','wechatpay')"
        ),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(nullable=True)
    source_staging_id: Mapped[int | None] = mapped_column(
        ForeignKey("paypay_import_staging.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
```

これを users / categories / expenses / monthly_settlements / paypay_import_staging / events の**6クラス書く**。DESIGN.md §4.2 の各カラム定義から機械的に写せる。

**この段階では DB には何もない**（Python にメニューを書いただけ）。次の Alembic が「これを実物にする」役割。

**所要時間**：1〜2時間（DESIGN.md §4.2 から機械的に写経できる）

---

### ステップ4：Alembic で「メニューを厨房に教える」

**やること**：Alembic 初期化 → 差分自動生成 → DB に適用

**打つコマンド**（順番に）：
```bash
alembic init alembic                                         # ①初期化
# alembic/env.py を編集して target_metadata = Base.metadata を設定
alembic revision --autogenerate -m "initial schema"          # ②差分生成
# alembic/versions/xxxx_initial_schema.py が出来る → 目視で内容確認
alembic upgrade head                                         # ③適用
```

**出るもの**：
- `alembic/versions/xxxx_initial_schema.py`（変更手順書。git 管理する）
- 実際の DB にテーブルが出来る

**注意点**：`env.py` の `target_metadata` の設定が最大のハマりポイント。`from app.db.models import *` してから `Base.metadata` を代入する必要がある。

**所要時間**：初回は1〜2時間

---

### ステップ5：常連客をシード（ありす／ひつじの初期投入）

**やること**：追加のマイグレーションで `users` に2件 INSERT

**打つコマンド**：
```bash
alembic revision -m "seed users"    # 空のマイグレーションを作る
```

生成されたファイルを開いて `upgrade()` に書く：
```python
def upgrade():
    op.bulk_insert(
        sa.table("users",
            sa.column("id", sa.Integer),
            sa.column("username", sa.Text),
            sa.column("name", sa.Text),
            sa.column("password_hash", sa.Text),
            sa.column("theme_preference", sa.Text),
        ),
        [
            {"id": 1, "username": "alice", "name": "ありす",
             "password_hash": "<環境変数から取得＆bcrypt>", "theme_preference": "light"},
            {"id": 2, "username": "hitsuji", "name": "ひつじ",
             "password_hash": "<環境変数から取得＆bcrypt>", "theme_preference": "light"},
        ],
    )
```

その後：`alembic upgrade head`

**所要時間**：30分

---

### ステップ6：目で見て確認（psql で `\d`）

**やること**：PostgreSQL に入って、テーブルが本当にできているか確認

**打つコマンド**：
```bash
podman exec -it household_db psql -U household_user -d household
```

中に入ったら：
```sql
\dt                    -- テーブル一覧
\d expenses            -- expenses の詳細（カラム・PK・FK・インデックス）
\d events              -- events の詳細
SELECT * FROM users;   -- ありす／ひつじが入っているか
\q                     -- 終了
```

**出るもの**（プレゼン Topic ② の実行結果と同じ体験）：
```
household=# \d expenses
   Column    |           Type           | Nullable
 id          | integer                  | not null
 paid_by     | integer                  | not null
 amount      | integer                  | not null
 ...
Indexes:
  expenses_pkey PRIMARY KEY, btree (id)
  ix_expenses_occurred_on btree (occurred_on)
Foreign-key constraints:
  ... FOREIGN KEY (paid_by) REFERENCES users(id) ON DELETE RESTRICT
```

**この瞬間が Phase 2 の完成**。DESIGN.md §4 に書いた通りのものが DB に本当に存在している、と目で見て確認できる。

---

## 3. 全体フロー

```
【1】compose.yaml        →  Podman が PostgreSQL を起動（厨房オープン）
                            │
【2】pyproject.toml       →  Python 側のツールが揃う
                            │
【3】models.py            →  レシピ集を書く（まだ厨房には未伝達）
                            │
【4】alembic autogen      →  レシピ集 → 変更手順書 → 厨房に反映
                            │
【5】seed マイグレーション →  常連客リストを厨房のノートに追加
                            │
【6】psql で \d           →  厨房を覗いて、全部揃っているのを目視
                            ▼
                      Phase 2 完了
                      （まだ注文はできない = API 未実装 = Phase 3 へ）
```

---

## 4. 総所要時間の目安

- **初めて DB / Podman / Alembic をやる人**：**10〜20時間**（詰まりどころが多い）
- **慣れている人**：3〜5時間

---

## 5. よくある詰まりどころ（macOS 前提）

| 場所 | 症状 | 対処 |
| :---- | :---- | :---- |
| Podman の初期セットアップ | `podman compose` が動かない | `podman machine init && podman machine start` が必要 |
| **`podman compose` 実行時** | **`looking up compose provider failed` / `docker-compose not found`** | **`podman-compose` を pip でインストール：`pip3 install --user podman-compose`。以降は `podman-compose up -d` を直接叩く（`podman compose` は使わない）** |
| **`podman-compose` の PATH** | **`podman-compose: command not found`** | **`~/Library/Python/3.13/bin` が PATH に入っていない。`.zshrc` に `export PATH="$HOME/Library/Python/3.13/bin:$PATH"` を追記** |
| **postgres コンテナが起動しない** | **`initdb: error: invalid locale settings; check LANG and LC_* environment variables`** | **`compose.yaml` の `LANG: ja_JP.UTF-8` を `LANG: C.UTF-8` に変更。postgres:16 の Debian イメージには ja_JP ロケールが未インストール。`podman-compose down -v` でボリューム消してから再起動** |
| コンテナが `unhealthy` のまま | `pg_isready` が失敗 | environment 変数の綴りミス、または起動待ちが足りない |
| Alembic の `env.py` | `autogenerate` しても空のマイグレーションしか出ない | `target_metadata = Base.metadata` の前に models を全部 import する必要あり |
| Docker と Podman のコマンド差 | ネット上の記事通りに動かない | 大体そのままいけるが、`docker-compose` は `podman-compose` に置換 |
| PostgreSQL 接続 | `password authentication failed` | `.env` のパスワードとコンテナ環境変数がズレてる。再確認 |

---

## 6-a. ステップ1 実行ログ（2026-07-21 完了）

実際に踏んだコマンド：
```bash
podman machine init           # VM イメージ DL、~10分
podman machine start          # VM 起動
pip3 install --user podman-compose  # compose ツール

# 準備: compose.yaml / .env.example / .gitignore を配置
# .env を作成（POSTGRES_PASSWORD をランダム生成）
export PATH="$HOME/Library/Python/3.13/bin:$PATH"

podman-compose up -d          # ★1回目失敗（LANG: ja_JP.UTF-8 が原因）
podman-compose down -v        # コンテナとボリューム削除
# compose.yaml を LANG: C.UTF-8 に修正
podman-compose up -d          # 成功

podman ps                     # (healthy) を確認
podman exec household_db psql -U household_user -d household -c "\dt"
                              # → Did not find any relations（空 DB を確認）
```

達成状態：
- `household_db` コンテナが `(healthy)` で稼働
- PostgreSQL 16.14 が `localhost:5432` で接続可能
- `household` DB は空（テーブルはまだない）

---

## 6-b. ステップ2 実行ログ（2026-07-21 完了）

実際に踏んだコマンド：
```bash
# ディレクトリ構造を作成
mkdir -p backend/app/{api,services,db}
touch backend/app/__init__.py backend/app/api/__init__.py \
      backend/app/services/__init__.py backend/app/db/__init__.py

# pyproject.toml を作成（sqlalchemy / alembic / psycopg[binary] / pydantic-settings / bcrypt）
# uv で依存インストール
cd backend
uv sync                       # .venv/ が自動生成、15パッケージ入る

# 動作確認
uv run python -c "import sqlalchemy, alembic, psycopg, pydantic_settings"
uv run python -c "<load_dotenv + engine.connect() + SELECT version()>"
                              # → ✓ DB接続成功、PostgreSQL 16.14 が応答
```

達成状態：
- `backend/pyproject.toml` に Phase 2 で必要な依存を宣言
- `.venv/` が backend/ 直下に生成、15パッケージ（sqlalchemy 2.0.51 / alembic 1.18.5 / psycopg 3.3.4 等）
- Python から `../.env` の `DATABASE_URL` でコンテナ内 PostgreSQL に接続成功
- **ステップ1（DB）とステップ2（Python環境）が疎通確認済み**

**ハマりどころ**（追加）:
- `uv sync` は `pyproject.toml` のあるディレクトリ以下で実行する必要あり
- Python 3.11 以上を要求（`requires-python = ">=3.11"` 指定）

---

## 6-c. ステップ3 実行ログ（2026-07-21 完了）

作ったファイル：
- `backend/app/db/base.py`（`Base` クラス + naming_convention）
- `backend/app/db/models.py`（6モデル）

実際に踏んだこと：
```bash
# 1) models.py を書いてから、まず読み込みテスト
uv run python -c "from app.db.models import *"
# → 6モデル読込 OK、Base.metadata が 6 テーブルを把握

# 2) ORM の動作デモ（Base.metadata.create_all で一時的に本物のテーブルを作る）
#    - User / Category / Expense を1件ずつ INSERT
#    - SELECT / UPDATE で自動で updated_at が更新されるのを確認
#    - CheckConstraint が不正値（payment_method="paypal"）を拒否するのを確認

# 3) drop_all で後片付け ★ここでハマった★
```

**ハマりどころ**（追加）：**循環 FK があると drop_all がコケる**
- 症状: `sqlalchemy.exc.CircularDependencyError: Can't sort tables for DROP; an unresolvable foreign key dependency exists between tables: expenses, paypay_import_staging`
- 原因: `Expense.source_staging_id → paypay_import_staging.id` と `PayPayImportStaging.linked_expense_id → expenses.id` の相互参照
- 対策: `base.py` の `MetaData` に **naming_convention** を設定して、全制約に自動命名を付ける。Alembic 使用時のベストプラクティスでもある

対策後：
- クリーンアップは `podman exec household_db psql -c "DROP TABLE ... CASCADE"` で行った
- naming_convention 追加後は `Base.metadata.drop_all(engine)` も正しく動くようになった

達成状態：
- 6モデル定義完了、Python から create_all / INSERT / SELECT / UPDATE / drop_all の全部が動作確認済み
- `base.py` に命名規約入り。次の Alembic マイグレーションでも問題ない形

---

## 6-d. ステップ4 実行ログ（2026-07-22 完了）

作ったもの：
- `backend/alembic/` ディレクトリ一式（`alembic init alembic` で自動生成）
- `backend/alembic.ini`（デフォルトのまま）
- `backend/alembic/env.py`（自作、下記の3変更を加えた）
- `backend/alembic/versions/ec1d112d18e8_initial_schema.py`（autogenerate 生成、手動修正あり）

env.py に加えた変更：
1. `python-dotenv` で `../.env` を読み込み、`DATABASE_URL` を環境変数から取得
2. `from app.db import models` で全モデルを import させて Base.metadata に登録
3. `compare_type=True`, `compare_server_default=True` で差分検出を強化

**踏んだハマりどころ**：

- **①CheckConstraint 名の重複プレフィックス**
  - 症状: `ck_expenses_ck_expenses_payment_method` のように "ck_" が2重
  - 原因: モデル側で `name="ck_expenses_payment_method"` と書き、naming_convention で更に `ck_expenses_` が付加された
  - 対策: モデル側は短い名前（例：`name="payment_method"`）にする

- **②循環 FK でテーブル作成順が破綻**
  - 症状: `expenses` が `users` より先に作成され、FK 作成で失敗する
  - 原因: `Expense` と `PayPayImportStaging` の相互 FK で、Alembic のトポロジカルソートが破綻
  - 対策: 片方の FK に `use_alter=True, name="..."` を指定。「テーブル作成後に ALTER TABLE で追加する」動作に切り替える

- **③use_alter=True の FK が実 DB に反映されない**
  - 症状: autogenerate 生成の migration に `use_alter=True` は入っているが、実 DB に FK が作られない
  - 原因: Alembic autogenerate は `use_alter=True` FK の場合、末尾の `op.create_foreign_key()` を追加し忘れることがある（既知の限界）
  - 対策: migration ファイルの `upgrade()` 末尾に `op.create_foreign_key(...)` を手動追加、`downgrade()` 冒頭に `op.drop_constraint(...)` を追加

**プレゼン Topic ④の実物確認**：
- `alembic_version` テーブルが自動作成され、`version_num='ec1d112d18e8'` を保持 → 「しおり」の実物
- `alembic downgrade base` で全 6 テーブルが drop され、`alembic_version` のみ残る → ロールバックの実物

達成状態：
- 7 テーブル（app 6 + alembic_version 1）が本番想定通りに存在
- `\d expenses` で全 3 つの FK と CheckConstraint と Index が確認できた
- DESIGN.md §4.2 と §4.4（ON DELETE ポリシー）の設計判断が実 DB に反映されている

---

## 6-e. ステップ5 実行ログ（2026-07-22 完了）

作ったもの：
- `.env` に `ALICE_PASSWORD` / `HITSUJI_PASSWORD`（openssl でランダム生成）
- `backend/alembic/versions/3f24dcc8bdbf_seed_users.py`（seed マイグレーション）

seed マイグレーションの設計：
- 環境変数からパスワードを読み、bcrypt でハッシュ化して INSERT
- 環境変数が未設定なら `raise RuntimeError` で失敗（本番でのセキュリティ担保）
- `op.execute("SELECT setval('users_id_seq', 2)")` で自動採番カウンタも同期
- `downgrade` で seed 分を DELETE + シーケンスも巻き戻し

実行結果：
```bash
uv run alembic upgrade head
# → Running upgrade ec1d112d18e8 -> 3f24dcc8bdbf, seed users
```

```sql
SELECT id, username, name, theme_preference, LEFT(password_hash, 20) FROM users;
-- 1 | alice   | ありす | light | $2b$12$ctuAMhvs/DIts...
-- 2 | hitsuji | ひつじ | light | $2b$12$tR8c0GVlzdooi...
```

---

## 6-f. ステップ6 実行ログ（2026-07-22 完了）

psql で目視の最終確認（プレゼン ⑤の `\d tasks` と同じ体験）：

```bash
podman exec -i household_db psql -U household_user -d household
```

確認したこと：
- `alembic_version` = `3f24dcc8bdbf`（seed users まで進んでいる）
- テーブル7個（app 6 + alembic_version 1）
- users のみ 2 件、他は空
- expenses の `\d` で PK 1 + Index 3 + CheckConstraint 2 + FK 3（RESTRICT/RESTRICT/SET NULL）を確認
- `paypay_import_staging.linked_expense_id → expenses.id ON DELETE SET NULL` の循環 FK も正しく作成されている

**Phase 2 完了。次は Phase 3（バックエンド API + ログ設計）へ。**

Phase 3 で使う下地：
- `backend/app/db/models.py` — そのまま services/ から import できる
- `backend/app/db/base.py` — `Base.metadata` 経由でエンジン作成に使う
- Alembic フロー（`alembic revision --autogenerate` → 確認 → `upgrade head`）はモデル追加時にも同じ手順を踏む

---

## 6. 次に何をするか（このドキュメントの読者に）

このドキュメントは **Phase 2 を通しでやるときの手引き**。実際に手を動かすときは：

1. まずステップ1（compose.yaml + Podman 起動）から
2. 各ステップの「出るもの（検証）」で動作確認しながら進む
3. 詰まったら「よくある詰まりどころ」を確認
4. それでも解決しなければ、Claude に「ステップXでこのエラーが出た」と聞く

Phase 2 が終わったら Phase 3（バックエンド API + 構造化ログ）へ。
