# レクチャー第1回：リクエストの一生

対象: `POST /api/expenses/`（支出を1件登録する）
狙い: **全レイヤーを1本だけ縦断する。** 個々のファイルの詳細より「どこで何が起きるか」の地図を作る。

> なぜここから始めるか：面接で最も聞かれる形が「リクエストが来てから返るまでを説明してください」だから。
> 逆に言うと、この1本を説明できれば、アプリの構造を説明できたことになる。

---

## 0. 今日辿るもの

Swagger UI（`http://localhost:8000/docs`）から、こう送る。

```json
POST /api/expenses/
{"amount": 1234, "occurred_on": "2026-09-01", "category_id": 1,
 "payment_method": "cash", "paid_by": 1}
```

返ってくるもの。

```json
201 Created
{"id": 43, "amount": 1234, "created_at": "2026-09-01T09:17:37Z", ...}
```

この間に**8つのファイル**を通る。1つずつ見ていく。

---

## 1. 全体の地図

```
  ブラウザ / Swagger UI
        │  POST /api/expenses/
        ▼
  ┌─────────────────────────────────────────┐
  │ ① main.py          アプリの入口・ミドルウェア  │
  │      │             request_id を採番        │
  │      ▼                                    │
  │ ② api/expenses.py  どの URL がどの関数か      │
  │      │                                    │
  │      ├─→ ③ api/deps.py      DB接続・ユーザー特定 │
  │      ├─→ ④ api/schemas/     入力の検証        │
  │      ▼                                    │
  │ ⑤ services/expense.py   業務ルール・手順      │
  │      │                                    │
  │      ├─→ ⑥ db/queries/expense.py  SQL を組む  │
  │      │        └─→ ⑦ db/models.py  テーブル定義 │
  │      └─→ ⑧ services/events.py    履歴を残す    │
  │                     ▼                      │
  └─────────────────────────────────────────┘
                  PostgreSQL
```

**依存の向きは一方通行**（`api/ → services/ → db/`）。
下の層は上の層を知らない。`db/queries/` は「誰が呼んだか」を知らないし、知る必要もない。

---

## 2. 各ファイルで何が起きるか

### ① `app/main.py` — 入口

```python
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    ...  # request_id を採番して、以降のログに紐づける
```

**ミドルウェア**は「全リクエストが必ず通る関所」。ここで各リクエストに固有の ID を振る。

なぜ要るか：エラーが出たとき、ログの中から**そのリクエストだけ**を追えるようにするため。
フロントで 500 が出たとき `X-Request-Id` を画面に出しているのは、この ID を指している。

```python
app.include_router(expenses.router)   # /api/expenses/* を expenses.py に任せる
```

### ② `app/api/expenses.py` — どの URL がどの関数か

```python
@router.post("/", response_model=ExpenseRead, status_code=201)
def create(session: SessionDep, user: CurrentUserDep, data: ExpenseCreate):
    return svc.create_expense(
        session, user,
        amount=data.amount,
        occurred_on=data.occurred_on,
        ...
    )
```

**ここが11行しかないのが重要。** API 層の仕事は3つだけ。

1. URL とメソッドを関数に結びつける（`@router.post("/")`）
2. 入力を受け取る（`data: ExpenseCreate`）
3. サービスに渡して、結果を返す

**業務ルールを1行も書いていない。** 「金額が0以下ならエラー」も「イベントを記録する」もここにはない。
理由：API 層が厚くなると、同じルールを別の入口（PayPay 取り込みなど）から呼べなくなるから。

### ③ `app/api/deps.py` — 材料を用意する

`session: SessionDep` と `user: CurrentUserDep` は、**自分で書いていないのに値が入っている。**
これが FastAPI の**依存性注入（Dependency Injection）**。

```python
SessionDep     = Annotated[Session, Depends(get_db_session)]
CurrentUserDep = Annotated[User,    Depends(get_current_user)]
```

「この関数を呼ぶ前に、`get_db_session()` を実行して結果を渡しておいて」という宣言。

なぜ嬉しいか：
- 全ハンドラで `session = SessionLocal()` と書かなくて済む（DRY）
- テストのとき、偽物の session に差し替えられる
- Phase 5 で認証を JWT にするとき、**`get_current_user` の中身だけ**変えればいい。ハンドラは無傷

### ④ `app/api/schemas/expense.py` — 入力の検証

```python
class ExpenseCreate(BaseModel):
    amount: int = Field(gt=0)          # 0 より大きい
    occurred_on: date
    category_id: int
    payment_method: str
```

Pydantic が**ハンドラに入る前に**検証する。`amount: 0` を送ると、`create()` は呼ばれずに 422 が返る。

フロントで「金額を入力してください」を該当欄の下に出せるのは、この 422 のレスポンスに
「どのフィールドが、なぜ駄目か」が入っているから。

### ⑤ `app/services/expense.py` — 業務ルールと手順

ここが**アプリの本体**。関数が2つに分かれているのがポイント。

```python
def create_expense_core(...):        # commit しない
    expense = q.create_expense(...)  # ⑥ を呼ぶ
    _mark_stale_if_settled(session, expense.occurred_on)
    write_event(session, event_type="expense.created", ...)   # ⑧ を呼ぶ
    return expense

def create_expense(...):             # commit する
    expense = create_expense_core(...)
    session.commit()
    return expense
```

**なぜ2つに分けたか。** これは第5回で詳しくやるが、要点だけ：

PayPay の取り込みでは「支出を作る」＋「ステージング行を adopted にする」＋「イベントを残す」を
**まとめて1つ**にしたい。途中で失敗したら全部なかったことにしたい。
`create_expense` が中で commit してしまうと、支出だけ確定して残る。

→ **commit する版としない版に分けた。** 呼ぶ側が「どこが1つのまとまりか」を決める。

`_mark_stale_if_settled` は「清算済みの月に後から支出を足したら、更新ありフラグを立てる」という業務ルール。
こういうものが services に集まる。

### ⑥ `app/db/queries/expense.py` — SQL を組み立てる

```python
def create_expense(session, *, paid_by, amount, ...):
    expense = Expense(paid_by=paid_by, amount=amount, ...)
    session.add(expense)
    session.flush()      # ← commit ではない
    return expense
```

**`flush()` と `commit()` の違いが第1回で一番大事な区別。**

| | 何をするか | 取り消せるか |
| :---- | :---- | :---- |
| `flush()` | SQL を DB に送る。**採番された id が取れる** | ✅ まだロールバックできる |
| `commit()` | トランザクションを確定する | ❌ もう戻せない |

`flush()` した直後に `expense.id` が使えるのは、DB が id を採番して返してくれるから。
でもまだ確定していないので、この後エラーが出れば全部消える。

### ⑦ `app/db/models.py` — テーブルの定義

```python
class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[int]
    occurred_on: Mapped[date]
    ...
```

Python のクラスが、そのまま `expenses` テーブルに対応する。これが **ORM**（Object-Relational Mapping）。
第2回で詳しくやる。

### ⑧ `app/services/events.py` — 履歴を残す

```python
write_event(session, event_type="expense.created", actor=user,
            entity_type="expense", entity_id=expense.id, payload={...})
```

「誰がいつ何をしたか」を `events` テーブルに追記する。**この関数以外から events に書かない**という規約。

実際に確認できる（今日 POST した結果）：

```
events 件数: 59 → 60
最新: expense.created  entity_id=43
payload: {'amount': 1234, 'source': 'manual', 'category_id': 1, 'payment_method': 'cash'}
```

`source: 'manual'` が入っているのは、手入力か PayPay 由来かを後から集計したいから。
Phase 6（BigQuery 分析）で使う。

---

## 3. 実際に動かした記録

```bash
curl -X POST http://localhost:8000/api/expenses/ \
  -H "Content-Type: application/json" -H "X-User-Id: 1" \
  -d '{"amount":1234,"occurred_on":"2026-09-01","category_id":1,
       "payment_method":"cash","paid_by":1}'
```

```
HTTP 201
{"id": 43, "paid_by": 1, "amount": 1234, "occurred_on": "2026-09-01",
 "created_at": "2026-09-01T09:17:37.085723Z", ...}
```

| 確認項目 | 結果 |
| :---- | :---- |
| ステータス | 201 Created |
| `expenses` に追加 | id=43 |
| `events` に追加 | 59 → 60 件 |
| `created_at` | 自分で送っていないのに入っている（DB が入れる） |

---

## 4. 「1つでも欠けたら何が困るか」

第1回の問いへの答え。

| 欠けると | 何が起きるか |
| :---- | :---- |
| ① ミドルウェア | エラーが出ても、ログのどれがそのリクエストか分からない |
| ③ deps | 全ハンドラで DB 接続を自分で書くことになる。認証を変えるとき全部直す |
| ④ schemas | 不正な値がそのまま DB に入る。`amount: -500` が通る |
| ⑤ services | 業務ルールが API 層に散らばる。PayPay 経由と手入力で挙動が変わる |
| ⑥ queries | SQL がサービス層に混ざり、テストで DB が必須になる |
| ⑧ events | 「誰がいつ何をしたか」が残らない。Phase 6 の分析ができない |

**層を分けるのは、きれいにするためではなく「変更したときに壊れる範囲を狭くする」ため。**

---

## 5. 確認問題

答えは第2回の冒頭で扱う。

1. `session.flush()` を `session.commit()` に変えたら、PayPay の取り込みで何が壊れるか
2. `@router.post` のハンドラに業務ルールを直接書いたとして、最初に困るのはどんな場面か
3. `write_event()` を経由せず、`session.add(Event(...))` と直接書ける。それでも関数を1本に絞っているのはなぜか

---

## 6. 用語（面接で使うもの）

| 用語 | 意味 |
| :---- | :---- |
| **ミドルウェア** | 全リクエストが通る共通処理。ログ・認証・CORS など |
| **依存性注入（DI）** | 関数が必要とするものを、外から渡す仕組み |
| **ORM** | テーブルをクラスとして扱う仕組み |
| **トランザクション** | 「全部成功か、全部失敗か」の単位 |
| **flush / commit** | SQL を送る / 確定する |
| **レイヤードアーキテクチャ** | 層を分けて、依存の向きを一方通行にする設計 |
