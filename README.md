# 家計清算アプリ（household app）

パートナー2人（ありす／ひつじ）で使う**家計簿 + 月次清算 Web アプリ**。
全支出をカテゴリ分けして記録し、月末に「どちらがいくら送金すればいいか」を自動計算する。
フルスタック開発（コンテナ / DB / API / フロント）を通しで学ぶための**学習用プロジェクト**。

---

## 技術スタック

| 領域 | 採用技術 |
| :---- | :---- |
| コンテナ | Podman（+ podman-compose） |
| DB | PostgreSQL 16 |
| バックエンド | FastAPI / SQLAlchemy 2.0 / Alembic |
| 設定・バリデーション | Pydantic 2 / pydantic-settings |
| ログ | structlog（JSON 構造化ログ） |
| パッケージ管理 | uv |
| フロントエンド | Next.js（App Router）＋ shadcn/ui ／ Tailwind CSS（**Phase 4 で実装予定**） |

---

## 進捗

| Phase | 内容 | 状態 |
| :---- | :---- | :---- |
| Phase 1 | 設計（ドメイン / アーキテクチャ / データモデル / UI モック） | 完了 |
| Phase 2 | DB 基盤（PostgreSQL コンテナ / SQLAlchemy モデル / Alembic） | 完了 |
| Phase 3 | バックエンド API（FastAPI 14 パス / 18 オペレーション + 構造化ログ） | 完了（AI 連携は不要と判断して見送り → [DESIGN.md §1.8](DESIGN.md)） |
| Phase 4 | フロントエンド（Next.js） | **次はここ** |
| Phase 5 | 認証（JWT）・月末自動締めジョブ・テスト拡充・mypy | 一部着手（テスト基盤のみ） |
| Phase 6 | ログ分析（events → BigQuery） | 未着手 |
| Phase 7 | デプロイ | 未着手（カリキュラム上スコープ外） |

現時点で操作できるのは **Swagger UI（`http://localhost:8000/docs`）のみ**。ブラウザ向けの画面は Phase 4 で作る。

---

## セットアップ

前提：macOS / Podman / Python 3.11 以上 / [uv](https://docs.astral.sh/uv/)

### 1. 環境変数を用意

```bash
cp .env.example .env
```

`.env` を開いて以下を書き換える。

- `POSTGRES_PASSWORD` — DB のパスワード（好きな文字列）
- `DATABASE_URL` — 上と同じパスワードを埋める
- `ALICE_PASSWORD` / `HITSUJI_PASSWORD` — 初期ユーザー2人のログインパスワード（seed マイグレーションで bcrypt ハッシュ化して投入される）

ランダム生成する場合：

```bash
openssl rand -base64 24
```

### 2. Podman を起動（macOS は初回のみ VM が必要）

```bash
podman machine init      # 初回のみ。VM イメージのダウンロードで約10分
podman machine start
```

### 3. podman-compose を入れる（初回のみ）

```bash
pip3 install --user podman-compose
export PATH="$HOME/Library/Python/3.13/bin:$PATH"   # .zshrc にも追記しておく
```

`podman compose`（サブコマンド版）ではなく `podman-compose`（別コマンド）を使う。理由は `PHASE2_PLAN.md` §5 参照。

### 4. PostgreSQL コンテナを起動

```bash
podman-compose up -d
podman ps                # STATUS が (healthy) になるまで待つ
```

### 5. Python の依存をインストール

```bash
cd backend
uv sync
```

### 6. DB スキーマを作成 + 初期ユーザーを投入

```bash
uv run alembic upgrade head
```

### 7. API サーバを起動

```bash
uv run uvicorn app.main:app --reload
```

### 8. ブラウザで開く

<http://localhost:8000/docs>

Swagger UI から全 API を試せる。認証は Phase 5 実装予定のため、Phase 3 時点では
リクエストヘッダ `X-User-Id`（`1` = ありす／`2` = ひつじ／省略時は `1`）でユーザーを切り替える。

---

## 開発用サンプルデータ

画面や API を試すとき、見栄えのするデータを入れられる。

```bash
cd backend
uv run python scripts/seed_dev_data.py           # 既存データを消して投入
uv run python scripts/seed_dev_data.py --keep    # 消さずに追加
```

投入されるもの：カテゴリ5件、2026-06（`settled`）／2026-07（`closed`）／2026-08（`in_progress`）の
支出39件、PayPay ステージング5件。清算の3状態が揃うので月次清算画面の各状態を確認できる。

---

## テスト

```bash
cd backend
uv sync --extra dev          # 初回のみ（pytest 等を入れる）
uv run pytest                # 全テスト
uv run pytest tests/unit/    # 純関数のみ（DB 不要・高速）
uv run pytest -v             # 各テスト名を表示
```

- **`tests/unit/`** — DB を触らない純関数のテスト。コンテナが停止していても走る
- **`tests/integration/`** — DB に接続するテスト。`household_test` という**別 DB** を自動作成して使うため、開発用データ（`household`）は汚れない

テスト用 DB を作り直したいときは `DROP DATABASE household_test;` すれば次回の実行で再作成される。

---

## ドキュメント

| ファイル | 内容 |
| :---- | :---- |
| [`DESIGN.md`](DESIGN.md) | **設計方針書**。設計の大前提／ドメイン／採用アーキテクチャ／データモデル／ディレクトリ構成／Phase 3 実装ステータス（§7） |
| [`PHASE2_PLAN.md`](PHASE2_PLAN.md) | **Phase 2（DB）の構築手順と実行ログ**。Podman / Alembic のハマりどころ付き |
| [`PHASE3_PLAN.md`](PHASE3_PLAN.md) | **Phase 3（API）の実装手順と実行ログ**。E2E 検証結果とハマりどころ付き |
| [`mockups/`](mockups/) | UI モック（ワイヤーフレーム）7枚：ダッシュボード／支出一覧／月次清算／PayPay 取り込み／カテゴリ管理／ログイン／アカウントメニュー |

---

## 主要な設計方針

- **全支出＝共有支出**。個人支出はアプリの管理対象外（PayPay 取り込みで「個人」判定した行は記録だけ残す）。
- **負担割合は常に折半（50:50 固定）**。端数は支払者が多く負担する。支出ごとの割合上書きは持たない。
- **清算サイクルは月次（暦月）**。`in_progress → closed → partially_confirmed → settled` の状態機械で管理し、清算済月の支出を編集しても状態は巻き戻さず「更新あり」フラグを立てるだけにする。
- **`events` テーブルは追記専用のビジネスイベントログ**。書き込みは `services/events.py` の `write_event()` 1本のみを経由する。運用目的のシステムログ（structlog）とは明確に分ける。
- **依存の向きは一方通行**。バックエンドは `api/ → services/ → db/`、フロントは `app/ → features/ → components/ui/`。

---

## 注意

- `.env` は **git 管理外**（`.gitignore` で除外済み）。パスワードは各自のローカルにのみ置く。テンプレートは `.env.example`。
- 2人で使う**学習用プロジェクト**であり、本番運用・サービス化・多人数対応は想定していない。
