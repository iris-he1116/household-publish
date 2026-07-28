# Phase 3 実行計画：レストランを開店して注文を受け付ける

作成: 2026-07-22
参照: `DESIGN.md` §3（採用アーキテクチャ）／§4（データモデル）／§5.1（backend ディレクトリ）／`/Users/sibei.he/Downloads/CURRICULUM.md` Phase 3

---

## 0. Phase 3 のゴール

Phase 3 の終わりで達成される状態：

```
✓ FastAPI サーバが立ち上がっていて、
✓ /docs（Swagger UI）から支出/清算/カテゴリ/PayPay取り込み の API を試せて、
✓ 支出を1件 POST すると DB に保存され、events テーブルに履歴が入り、
✓ 月次集計・清算状態遷移が API 経由でできて、
✓ PayPay CSV をアップロードしてステージング→共有判定→昇格までできる

まだ:
✗ ブラウザで見える画面はない（Phase 4）
✗ 認証は最小限（current_user はハードコード or 簡易切替。本格実装は Phase 5）
✗ 月末の自動締めジョブ（Phase 5 想定）
```

つまり Phase 3 は「**厨房が動き、ウェイターが注文を受けられる状態**」。まだ客席（フロント）はないが、Swagger UI が仮の客席として API を叩ける。

---

## 1. アーキテクチャの再確認（DESIGN.md §3.1 と §5.1）

**依存の向き（一方通行）**：
```
   ┌──────────────────────┐
   │  api/                │  ← FastAPI ルーター + Pydantic スキーマ
   │  （リクエスト受付）  │     クライアントに見える境界
   └──────┬───────────────┘
          │ 呼ぶ
          ▼
   ┌──────────────────────┐
   │  services/           │  ← ビジネスロジック
   │  （業務ルール）      │     集計・状態遷移・折半計算・events 追記
   └──────┬───────────────┘
          │ 呼ぶ
          ▼
   ┌──────────────────────┐
   │  db/                 │  ← SQLAlchemy モデル + クエリ
   │  （データ操作）      │     Phase 2 で完成済み
   └──────────────────────┘
```

上から下は一方通行。`db/` は `api/` や `services/` を **絶対に import しない**。

---

## 2. 実装ステップ（大枠）

### 準備フェーズ
- **A. 依存追加**：`fastapi`, `uvicorn`, `structlog`（構造化ログ）を pyproject.toml に追加
- **B. 骨組み作り**：
  - `app/main.py`（FastAPI エントリ）
  - `app/db/session.py`（SQLAlchemy セッション管理）
  - `app/config.py`（環境変数を pydantic-settings で型付き管理）
  - `app/logging_config.py`（structlog 設定）
  - `app/services/events.py`（events 追記の唯一の窓口）
  - `app/api/deps.py`（DB session と current_user の Dependency）

### 機能フェーズ（api → services → db を機能単位で縦断）
- **C. categories**（CRUD 最小、動作確認しやすい）
- **D. expenses**（メイン機能、events 追記込み）
- **E. monthly_settlements**（集計 + 状態遷移 + 折半計算）
- **F. paypay_import**（CSV アップロード + ステージング + 昇格）

### 任意フェーズ
- **G. Vertex AI 連携**（PayPay 明細からカテゴリ自動推定など。時間があれば）

---

## 3. 認証の扱い（Phase 3 中の暫定運用）

DESIGN.md §4.2 では JWT + HttpOnly Cookie + スライディング期限を採用しているが、**本格実装は Phase 5**。Phase 3 は「認証なしで API を叩ける状態」で進める。

暫定実装：
- `app/api/deps.py` に `get_current_user()` を置く
- 中身は「常に users.id=1（ありす）を返す」ハードコード
- Phase 5 で JWT 検証に差し替えるが、`api/` と `services/` の呼び出し方は変えない

これで Phase 3 の実装量を減らしつつ、Phase 5 で正しく差し替えできる形にしておく。

---

## 4. events テーブルの扱い（プレゼン Topic ③ の思想）

events は「追記専用ログ」。書き込みは `services/events.py` の `write_event()` **1本だけ**を経由する（DRY + 単一責任）。

例：
```python
# services/expense.py の中
def create_expense(session, user, data) -> Expense:
    expense = Expense(...)
    session.add(expense)
    session.flush()  # id を確定させる
    write_event(
        session, "expense.created",
        actor=user, entity=expense,
        payload={"amount": expense.amount, "payment_method": expense.payment_method},
    )
    session.commit()
    return expense
```

`api/` や `db/` から events テーブルを直接触ることは禁止。

---

## 5. 構造化ログ（Phase 3 の学習項目の一つ）

**目的**：後から grep して「あるユーザーの操作」「エラーの傾向」を追える形で残す。

- ライブラリ：`structlog`（JSON 出力ができ、context を積み重ねられる）
- 出力先：標準出力（stdout）。将来 Cloud Logging に流す前提
- 出す内容：
  - リクエスト受付：method, path, current_user_id, request_id
  - サービス層の重要イベント：処理名、対象 id、結果
  - エラー：例外種別、スタックトレース

events テーブル（ビジネスイベントの永続ログ）と、structlog（システムログ、揮発してよい）は**別物**として扱う（DESIGN.md §0.1 の座学資料でも強調されていた）。

---

## 6. 各機能の API 想定

DESIGN.md §5.2 のフロント側 features/ とほぼ1対1で対応。

### C. categories
| メソッド | パス | 用途 |
| :---- | :---- | :---- |
| GET | `/api/categories/` | 一覧（アーカイブ済みを含めるか？のクエリパラメタ） |
| POST | `/api/categories/` | 新規追加 |
| PATCH | `/api/categories/{id}` | 名前・並び順・色の変更 |
| POST | `/api/categories/{id}/archive` | アーカイブ（is_archived=true） |

### D. expenses
| メソッド | パス | 用途 |
| :---- | :---- | :---- |
| GET | `/api/expenses/` | 一覧（フィルタ：year_month, category_id, paid_by, payment_method） |
| POST | `/api/expenses/` | 新規登録（クイック入力フォーム、モック①） |
| GET | `/api/expenses/{id}` | 詳細 |
| PATCH | `/api/expenses/{id}` | 編集 |
| DELETE | `/api/expenses/{id}` | 論理削除 |

### E. monthly_settlements
| メソッド | パス | 用途 |
| :---- | :---- | :---- |
| GET | `/api/settlements/` | 過去月の一覧 |
| GET | `/api/settlements/{year_month}` | ある月のサマリ（合計・カテゴリ内訳・送金額） |
| POST | `/api/settlements/{year_month}/close` | 手動で締める（自動締めができるまでの暫定） |
| POST | `/api/settlements/{year_month}/confirm` | 現在ユーザーが「確認」ボタン押下 |

### F. paypay_import
| メソッド | パス | 用途 |
| :---- | :---- | :---- |
| POST | `/api/paypay-import/csv` | CSV アップロード → ステージングに INSERT |
| GET | `/api/paypay-import/staging?status=pending` | 未判定行の一覧 |
| POST | `/api/paypay-import/staging/{id}/adopt` | 共有として採用（Expense へ昇格） |
| POST | `/api/paypay-import/staging/{id}/exclude` | 個人として除外 |

---

## 7. 完了の目安（DESIGN.md + カリキュラム Phase 3）

以下がすべて Swagger UI で試せる状態：
- ありすで支出を1件 POST → DB に保存されて events に `expense.created`
- 同じ月に複数の支出を入れて GET すると合計と内訳が正しい
- 月次サマリで送金額（折半差額）が計算される
- カテゴリを追加してアーカイブできる
- PayPay CSV をアップロードし、共有判定して Expense へ昇格できる

---

## 8. 見直しの前提（Phase 3 で決めきらないもの）

- **月末自動締めジョブ**：Phase 5（cron or APScheduler）で追加
- **認証**：Phase 5 で JWT に差し替え
- **エラーメッセージの日本語化・詳細化**：Phase 4 のフロント実装時に必要に応じて
- **N+1 対策**：まずナイーブに書く。パフォーマンス問題が見えたら selectinload や joinedload を入れる
- **ページング**：expenses 一覧のみ最初から入れる。他は Phase 4 で必要に応じて

---

## 6-a. ステップA（依存追加）実行ログ（2026-07-28 完了）

`backend/pyproject.toml` の `dependencies` に Phase 3 で必要なものを追加：

```toml
# Phase 3 追加: バックエンド API + 構造化ログ
"fastapi>=0.115",
"uvicorn[standard]>=0.32",
"structlog>=24.4",
"python-multipart>=0.0.20",  # ファイルアップロード（PayPay CSV）用
```

- `optional-dependencies` にあった `api` グループは**削除**（本体依存に昇格したので二重管理をやめた）
- `dev` グループ（pytest / mypy / ruff）はそのまま残す（Phase 5 で使う）

実際に踏んだコマンド：
```bash
cd backend
uv sync                       # 11 パッケージ追加インストール
```

入ったもの（主要）：starlette 1.3.1 / uvicorn 0.51.0 / structlog 26.1.0 / python-multipart 0.0.32、
uvicorn[standard] の付属で h11 / httptools / uvloop / watchfiles / websockets、その他 idna / pyyaml。

**ハマりどころ**：
- `uv sync` は `pyproject.toml` があるディレクトリ（= `backend/`）で実行する必要がある。`alice_work/` 直下で叩くと `No pyproject.toml found` で失敗する（Phase 2 の 6-b と同じ罠を再度踏んだ）

達成状態：
- FastAPI / uvicorn / structlog が `backend/.venv` に入り、`uv run uvicorn --version` が応答する

---

## 6-b. ステップB（骨組み作り）実行ログ（2026-07-28 完了）

作ったファイル（6個）とその役割：

| ファイル | 役割 |
| :---- | :---- |
| `backend/app/config.py` | 環境変数を pydantic-settings で型付き管理 |
| `backend/app/logging_config.py` | structlog（JSON 構造化ログ）の設定 |
| `backend/app/db/session.py` | エンジン・セッションファクトリ・DB Dependency |
| `backend/app/services/events.py` | events 追記の唯一の窓口 |
| `backend/app/api/deps.py` | DB session と current_user の Dependency |
| `backend/app/main.py` | FastAPI エントリ（ミドルウェア・ルーター登録） |

各ファイルの中身の決めごと：

- **`config.py`** — `BaseSettings` を継承した `Settings` クラス。`env_file` は `backend/` の1つ上（= `alice_work/.env`）を指す（Phase 2 で作った `.env` をそのまま使い回す）。`extra="ignore"` にして `.env` の `POSTGRES_PASSWORD` などアプリが読まない変数を無視する。末尾で `settings` シングルトンをエクスポートし、他モジュールは `from app.config import settings` だけで済む形にした。値が不正なら**起動時に落ちる**（実行時に気付くより早い）。

- **`logging_config.py`** — JSON で標準出力に吐く。`setup_logging()` を起動時に1回呼ぶだけ。`merge_contextvars` プロセッサを入れて、`request_id` などの ContextVars を全ログ行に自動でマージする。コメントで **events テーブル（ビジネスイベントの永続ログ、分析目的）と structlog（システムログ、運用目的で揮発してよい）は別物**という座学資料の思想を明記しておいた（後で読む自分が混同しないため）。

- **`db/session.py`** — `create_engine(..., pool_pre_ping=True)` でプールから取り出した接続が切れていたら検出させる（コンテナ再起動対策）。`sessionmaker(..., expire_on_commit=False)` で commit 後もオブジェクトの属性にアクセスできるようにした（API のレスポンス組み立てで必要）。`get_db_session()` は「1リクエスト = 1セッション」で、`finally` で必ず close する generator Dependency。

- **`services/events.py`** — `write_event(session, *, event_type, actor, entity_type, entity_id, payload)` の1本だけ。DESIGN.md §4.3 の思想（追記専用・書き込みロジックを1箇所に閉じる = DRY）に従い、他のサービスから events を直接触らない。`session.flush()` で id を確定させるが **commit はしない**（呼び出し元のトランザクションに委ねる = 支出登録とイベント追記が同一トランザクションで原子的になる）。

- **`api/deps.py`** — `SessionDep = Annotated[Session, Depends(get_db_session)]` と `CurrentUserDep = Annotated[User, Depends(get_current_user)]` を定義。`get_current_user()` は Phase 3 の暫定実装で、`X-User-Id` ヘッダ（デフォルト `1` = ありす）でユーザーを切り替える。Phase 5 で JWT 検証に差し替える想定だが、**`api/` 側の呼び出し方（`user: CurrentUserDep`）は変えない**設計にした。

- **`main.py`** — `lifespan` で `setup_logging()` を実行。HTTP ミドルウェアで全リクエストに `request_id` を付与し、structlog の contextvars にバインド（レスポンスヘッダにも `X-Request-Id` を返すのでブラウザ側から追跡できる）。`/healthz` を1本置き、末尾で4つのルーターを `include_router` する。

達成状態：
- `uv run uvicorn app.main:app` でサーバが起動し、`/healthz` が JSON を返す
- リクエストごとに `request_id` 付きの JSON ログが標準出力に出る

---

## 6-c. ステップC（categories）実行ログ（2026-07-28 完了）

**3層（api → services → db）を最初に縦断する最小機能**として categories を選んだ。ここで層のパターンを固めて、以降の機能は同じ形をなぞる。

作ったファイル：
- `backend/app/api/schemas/category.py` — `CategoryCreate` / `CategoryUpdate` / `CategoryRead`。`CategoryRead` は `ConfigDict(from_attributes=True)` で ORM オブジェクトからそのまま変換できるようにした。色は `pattern=r"^#[0-9a-fA-F]{6}$"` でバリデーション
- `backend/app/db/queries/category.py` — `list_categories`（`include_archived` フラグ、`display_order` → `id` の順でソート）/ `get_category` / `create_category` / `update_category` / `archive_category`
- `backend/app/services/category.py` — 各 CRUD で `write_event()` を呼んでから `session.commit()`。update では変更前後を `{"before": {...}, "after": {...}}` の形で payload に記録
- `backend/app/api/categories.py` — 4 endpoints

| メソッド | パス |
| :---- | :---- |
| GET | `/api/categories/` |
| POST | `/api/categories/` |
| PATCH | `/api/categories/{category_id}` |
| POST | `/api/categories/{category_id}/archive` |

設計判断：
- **物理削除は提供しない**。アーカイブ（`is_archived=true`）のみ。`expenses.category_id` が `ON DELETE RESTRICT` なので、そもそも使用中カテゴリは消せない（DESIGN.md §4.4）
- すでにアーカイブ済みのカテゴリを再度アーカイブしようとしたら **400** を返す

達成状態：
- 3層の書き方のテンプレートが確定（`api/` は薄く、業務判断は `services/`、SQL は `db/queries/`）

---

## 6-d. ステップD（expenses）実行ログ（2026-07-28 完了）

作ったファイル：
- `backend/app/api/schemas/expense.py` — `PaymentMethod` を `Literal["cash","credit_card","paypay","wechatpay"]` で型定義（DB 側の CHECK 制約と対応）。`ExpenseCreate.paid_by` は省略可で、省略時は current_user を使う（モック①のクイック入力で「自分の支出」を最短手数で登録するため）。`ExpenseListResponse` は `items` / `total`（件数）/ `total_amount`（合計額）を返す
- `backend/app/db/queries/expense.py` — `_year_month_range("2026-07")` で `(2026-07-01, 2026-08-01)` を計算して半開区間で範囲検索（`occurred_on` のインデックスが効く形）。`_apply_filters()` にフィルタ条件（year_month / category_id / paid_by / payment_method / include_deleted）を集約し、`list_expenses` と `count_and_sum` の両方で使い回す（DRY）
- `backend/app/services/expense.py` — 後述の `_mark_stale_if_settled()` が要点
- `backend/app/api/expenses.py` — 5 endpoints（list / create / get / patch / delete）。delete は論理削除（`is_deleted=true`）で **204** を返す

**Phase 3 の設計上の要点：`_mark_stale_if_settled()`**

DESIGN.md §2.3 の「済月の支出を編集しても状態は settled のまま、UI に『更新あり』バッジを出す」を実現する関数。支出の作成／編集／削除のたびに、対象月の `MonthlySettlement.status == "settled"` なら `has_stale_updates=True` をセットする。

日付を跨いだ編集（例：2026-07-14 → 2026-06-30）では **旧月・新月の両方**をチェックする必要がある。片方だけ見ていると「済月から支出が抜けたのにバッジが出ない」という取りこぼしが起きる。

| メソッド | パス | 備考 |
| :---- | :---- | :---- |
| GET | `/api/expenses/` | year_month / category_id / paid_by / payment_method / limit / offset |
| POST | `/api/expenses/` | 201 |
| GET | `/api/expenses/{expense_id}` | |
| PATCH | `/api/expenses/{expense_id}` | |
| DELETE | `/api/expenses/{expense_id}` | 論理削除、204 |

---

## 6-e. ステップE（monthly_settlements）実行ログ（2026-07-28 完了）

作ったファイル：
- `backend/app/db/queries/settlement.py` — `get_or_create_settlement()`（該当月の行がなければ `in_progress` で作る）、`compute_totals()` で月次集計を SQL 側で計算（合計・件数・ユーザー別立替・カテゴリ内訳・支払い手段内訳を5クエリで取得）。Python 側でループして足す実装は避けた
- `backend/app/services/settlement.py` — **純関数を意識的に切り出した**のがポイント（下記）
- `backend/app/api/settlements.py` — 4 endpoints（list / get summary / close / confirm）。`services` が投げた `ValueError` を 400 に変換する

**純関数の切り出し**：
- `split_equally(total, user_a_paid)` — 折半額と送金額を計算する純関数（端数は支払者に多く負担、DESIGN.md §4 冒頭のルール）
- `next_status_on_close(current)` — 締め時の状態遷移
- `next_status_on_confirm(current, both_confirmed)` — 確認時の状態遷移

いずれも DB を触らないので、Phase 5 で pytest の単体テストがそのまま書ける。DESIGN.md §3.3 の「Phase 5 でテストに支障が出たら純関数への切り出しにリファクタ」を先取りした形。

**状態遷移の実装**：
```
in_progress ──close──> closed ──片方 confirm──> partially_confirmed ──両者 confirm──> settled
```
`settled` に到達した時点で `monthly_settlement.settled` イベントも追記する（`confirmed` イベントとは別に）。

暫定：
- **月末自動締めジョブは未実装**。`POST /api/settlements/{ym}/close` を手動で叩く運用（Phase 5 で cron / APScheduler 化）

---

## 6-f. ステップF（paypay_import）実行ログ（2026-07-28 完了）

作ったファイル：
- `backend/app/api/schemas/paypay_import.py` — `StagingRowRead` / `CsvImportResult`（`total_rows` / `new_rows` / `duplicate_rows`）/ `AdoptRequest`（`category_id` 必須）/ `ExcludeRequest`
- `backend/app/db/queries/paypay_import.py` — `bulk_insert_ignore_duplicates()` で PostgreSQL の `INSERT ... ON CONFLICT DO NOTHING` を使い、`uq_paypay_import_staging_txn`（`imported_by` + `paypay_txn_id` の UNIQUE 制約）にぶつかった行を DB 側で自動スキップさせる。`.returning(id)` で実際に挿入された件数を取り、重複件数を逆算する（アプリ側で「既にあるか」を都度 SELECT しない）
- `backend/app/services/paypay_import.py` — CSV パース（期待ヘッダ: `取引日, 金額, 店舗名, 取引ID`）、`adopt()` で Expense へ昇格（`payment_method="paypay"` 固定、`source_staging_id` でリンク、staging 側にも `linked_expense_id` を記録して双方向に辿れる形）、`exclude()` で個人判定
- `backend/app/api/paypay_import.py` — 4 endpoints。CSV アップロードは `UploadFile` で受ける

**他人のステージング行は判定できないガード**：
`staging.imported_by != user.id` なら `ValueError`（→ 400）。DESIGN.md §1.4 の「各自が自分の履歴をアップロードして自分で判定する」という運用前提をコード側で守る。

**ハマりどころ**：
- 実際の PayPay 履歴 CSV は **BOM 付き UTF-8** または **CP932** の可能性がある。`utf-8-sig` でデコードを試み、`UnicodeDecodeError` なら `cp932` にフォールバックする実装にした

| メソッド | パス |
| :---- | :---- |
| POST | `/api/paypay-import/csv` |
| GET | `/api/paypay-import/staging` |
| POST | `/api/paypay-import/staging/{staging_id}/adopt` |
| POST | `/api/paypay-import/staging/{staging_id}/exclude` |

---

## 6-g. E2E 検証結果（2026-07-28）

サーバを起動して curl で通しで叩いた。

```bash
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

確認した内容（実際に返ってきた数値）：

1. `GET /healthz` → `{"status":"ok"}`
2. `GET /openapi.json` の `paths` が **14 件**（= 4ルーター全部が登録済み。オペレーション数は 18：categories 4 / expenses 5 / settlements 4 / paypay-import 4 / healthz 1）
3. カテゴリ「食費」を作成 → `id=1`
4. ありす（ヘッダなし = デフォルト）で支出登録：3,240円 / 2026-07-14 / 食費 / 現金 → `id=1`
5. ひつじ（`X-User-Id: 2`）で支出登録：1,800円 / 2026-07-14 / 食費 / PayPay → `id=2`
6. `GET /api/settlements/2026-07` →
   ```
   total_amount        5,040
   per_person_share    2,520
   user_a_paid         3,240   （ありす）
   user_b_paid         1,800   （ひつじ）
   transfer_from_b_to_a  720   → ひつじ → ありす 720円
   ```
   カテゴリ内訳・支払い手段内訳も正しく集計された
7. PayPay CSV 3行（セブンイレブン 1,500 / ローソン 890 / Amazon 4,200）をアップロード → `{"total_rows":3,"new_rows":3,"duplicate_rows":0}`
8. `GET /api/paypay-import/staging?status=pending` → 3件、`occurred_on` の降順
9. Amazon の行（4,200円）を adopt（`category_id=1`, `note="シェアランチ"`）
   → staging.status が `adopted`、`linked_expense_id=3`
   → Expense `id=3` が `payment_method="paypay"` / `source_staging_id=3` で作成された
10. `POST /api/settlements/2026-07/close` → status `in_progress` → **`closed`**、`closed_at` 記録
11. `POST /api/settlements/2026-07/confirm`（ありす）→ **`partially_confirmed`**、`confirmed_at_user_a` 記録
12. `POST /api/settlements/2026-07/confirm`（`X-User-Id: 2` = ひつじ）→ **`settled`**、`confirmed_at_user_b` と `settled_at` 記録
13. 最終集計 → 合計 9,240 / 1人あたり 4,620 / ありす立替 7,440 / ひつじ立替 1,800 / **送金 ひつじ → ありす 2,820**
14. **済月編集テスト**：settled 済みの 2026-07 の支出 `id=1` を 3,240 → 3,500 に PATCH
    → status は **`settled` のまま**、`has_stale_updates` が **`true`** に
    → 合計 9,500 / 送金 2,950 に再計算
    → DESIGN.md §2.3 の設計通りの挙動
15. events テーブルを psql で確認 → `category.created` / `expense.created`（`actor_user_id` 1 と 2 の両方）/ `paypay.csv_imported` / `paypay.row_adopted` / `expense.updated` / `monthly_settlement.closed` / `monthly_settlement.confirmed` / `monthly_settlement.settled` が追記されていた。`expense.created` の payload には `source: "manual"` と `source: "paypay"` の区別も入っている

---

## 6-h. ハマりどころ（Phase 3 特有）

| 場所 | 症状 | 原因と対処 |
| :---- | :---- | :---- |
| **コンテナ再起動後の初回リクエスト** | **500。`sqlalchemy.exc.OperationalError: the database system is not yet accepting connections` / `InvalidatePoolError`** | **`podman-compose` でコンテナを再起動した直後、PostgreSQL がリカバリ中なのに SQLAlchemy のコネクションプールが接続を試みる。`pool_pre_ping=True` は「切れた接続の検出」なので、DB 自体がリカバリ中のケースは救えない。対処：数秒待って再試行。Phase 5 で `/healthz` に DB 接続チェックを足して起動待ちを判定できるようにする** |
| **登録済みルートの確認** | **`include_router` した後に `app.routes` を回しても `_IncludedRouter` オブジェクトしか出てこず、`APIRoute` は `/healthz` の1件しか見えない** | **FastAPI 0.139 系はルーターの遅延登録方式に変わっており、`app.routes` を列挙しても子ルートが見えない。対処：登録確認は `/openapi.json` の `paths` を見る** |
| **PayPay CSV のエンコーディング** | `UnicodeDecodeError` | 実際の PayPay 履歴 CSV は BOM 付き UTF-8 または CP932 の可能性がある。`utf-8-sig` で試して失敗したら `cp932` にフォールバックする |

---

## 9. Phase 3 の達成状態

- **FastAPI サーバが起動**し、`http://localhost:8000/docs`（Swagger UI）から 14 パス / 18 オペレーションすべてを試せる
- **支出登録 → events 追記 → 月次集計 → 締め → 双方確認 → settled** の一連が API で通る
- **PayPay CSV アップロード → ステージング → 共有判定 → Expense 昇格**が通る
- **済月編集時の `has_stale_updates` フラグ**が DESIGN.md §2.3 通りに動く

未実装（**Phase 5** 送り）：
- JWT 認証（現在は `X-User-Id` ヘッダでの暫定切替）
- 月末自動締めジョブ（現在は `close` API を手動で叩く）
- pytest によるテスト
- mypy による型チェック

未実装（**Phase 4**）：
- ブラウザで見える UI

**Phase 3 完了。次は Phase 4（フロントエンド）へ。**
