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
| フロントエンド | Next.js 16（App Router）/ React 19 / TypeScript / Tailwind CSS v4 |

---

## 進捗

| Phase | 内容 | 状態 |
| :---- | :---- | :---- |
| Phase 1 | 設計（ドメイン / アーキテクチャ / データモデル / UI モック） | 完了 |
| Phase 2 | DB 基盤（PostgreSQL コンテナ / SQLAlchemy モデル / Alembic） | 完了 |
| Phase 3 | バックエンド API（FastAPI 20 パス / 24 オペレーション + 構造化ログ） | 完了 |
| Phase 4 | フロントエンド（Next.js 3画面 / API 接続 / Server Actions） | 完了（PayPay 一括判定を含む） |
| Phase 5 | 認証（JWT）・月末自動締めジョブ・テスト拡充・mypy | 進行中（認証・自動締め・テスト基盤・mypyは完了。ユーザー設定は未着手） |
| Phase 6 | ログ分析（events → BigQuery） | 未着手 |
| Phase 7 | デプロイ | 未着手（カリキュラム上スコープ外） |
| v2 | MCP 経由の PayPay カテゴリ分類提案 | 構想中（確定操作は人間が行う） |

ブラウザで **`http://localhost:3000`** を開くと3画面（ホーム／支出／PayPay 取り込み）が使える。
ホームはカテゴリの追加・名称変更ができるクイック入力と月次清算、支出タブは明細の検索・編集だけに絞っている。
API 単体を試したいときは Swagger UI（`http://localhost:8000/docs`）。

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
- `JWT_SECRET` — JWT の署名鍵（32文字以上）
- `COOKIE_SECURE` — localhost の HTTP で試すときは `false`、Tailscale の HTTPS 公開時は `true`

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

### 8. フロントエンドを起動（別ターミナル）

前提：Node.js 20 以上

```bash
cd frontend
npm install                  # 初回のみ
npm run dev
```

`frontend/.env.local` を作って接続先を指定する（`.gitignore` 済み）。

```
API_BASE_URL=http://127.0.0.1:8000
```

### 9. ブラウザで開く

<http://localhost:3000/login>

3画面（ホーム／支出／PayPay 取り込み）が使える。

API 単体を試したいときは Swagger UI（<http://localhost:8000/docs>）。最初に
`POST /api/auth/login` でログインすると、以降の認証必須 API を試せる。

### 10. 自動起動・バックアップ・月末自動締め（任意）

```bash
./ops/install-services.sh
```

バックエンドとフロントエンドの自動起動、毎日 3:00 の DB バックアップ、毎日 23:59 の
月末自動締め判定を macOS の launchd に登録する。Mac が月末にスリープしていた場合も、
次回の補完実行で前月を締める。解除は `./ops/install-services.sh uninstall`。

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
uv run mypy app              # バックエンドの型検査
```

- **`tests/unit/`** — DB を触らない純関数のテスト。**コンテナが停止していても走る**（実測 0.01 秒）
- **`tests/integration/`** — DB に接続するテスト。`household_test` という**別 DB** を自動作成して使うため、開発用データ（`household`）は汚れない

業務ルールを「DB も request も触らない純関数」として切り出しておくと、`tests/unit/` に置けて実行が速くなる。
例：`services/settlement.py` の `split_equally()` / `next_status_on_confirm()`、
`services/paypay_import.py` の `ensure_judgeable()`。

テスト用 DB を作り直したいときは `DROP DATABASE household_test;` すれば次回の実行で再作成される。

---

## ドキュメント

| ファイル | 内容 |
| :---- | :---- |
| [`DESIGN.md`](DESIGN.md) | **設計方針書**。設計の大前提／ドメイン／採用アーキテクチャ／データモデル／ディレクトリ構成／Phase 3 実装ステータス（§7） |
| [`PHASE2_PLAN.md`](PHASE2_PLAN.md) | **Phase 2（DB）の構築手順と実行ログ**。Podman / Alembic のハマりどころ付き |
| [`PHASE3_PLAN.md`](PHASE3_PLAN.md) | **Phase 3（API）の実装手順と実行ログ**。E2E 検証結果とハマりどころ付き |
| [`PHASE4_PLAN.md`](PHASE4_PLAN.md) | **Phase 4（フロント）の実行計画**。Next.js 16 の作法（Server Actions / キャッシュ）と画面ごとのサーバー・クライアント振り分け |
| [`mockups/`](mockups/) | Phase 4 時点のUIモック（ワイヤーフレーム）。現在は情報設計をホーム／支出／PayPay 取り込みへ更新済み。加えて Phase 5 用のログイン画面 |
| [`slides/`](slides/) | 勉強会（Phase 4 前半）の発表資料。`phase4_frontend.pptx` と全文テキスト版 `phase4_frontend_text.md` |

---

## 主要な設計方針

- **全支出＝共有支出**。個人支出はアプリの管理対象外（PayPay 取り込みで「個人」判定した行は記録だけ残す）。
- **負担割合は常に折半（50:50 固定）**。端数は支払者が多く負担する。支出ごとの割合上書きは持たない。
- **清算サイクルは月次（暦月）**。`in_progress → closed → partially_confirmed → settled` の状態機械で管理し、清算済月の支出を編集しても状態は巻き戻さず「更新あり」フラグを立てるだけにする。
- **`events` テーブルは追記専用のビジネスイベントログ**。書き込みは `services/events.py` の `write_event()` 1本のみを経由する。運用目的のシステムログ（structlog）とは明確に分ける。
- **依存の向きは一方通行**。バックエンドは `api/ → services/ → db/`、フロントは `app/ → features/ → lib/`。
- **フロントは `'use client'` を葉にだけ付ける**。ページと layout はサーバーコンポーネントのまま保つ（実測：サーバー17 / クライアント8）。
- **フロントの状態は URL に持たせる**。絞り込み・ページ送り・対象月はクエリ/パスに置き、`useState` を使わない。
- **表示と更新で経路を分ける**。表示はサーバーコンポーネントから直接 `await`、更新は Server Actions 経由。API の URL をブラウザに露出させない。

---

## 注意

- `.env` は **git 管理外**（`.gitignore` で除外済み）。パスワードは各自のローカルにのみ置く。テンプレートは `.env.example`。
- 2人で使う**学習用プロジェクト**であり、本番運用・サービス化・多人数対応は想定していない。
