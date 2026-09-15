# Phase 4 実行計画：客席を作って、お客さんに料理を出す

作成: 2026-08-18　最終更新: 2026-08-25（前半の実装完了に合わせて実績を反映）
参照: `DESIGN.md` §0.3（フロントの3階層）／§1.7（UIモック 3画面）／§3.2（Feature-based）／§5.2（ディレクトリ構成）／`/Users/sibei.he/Downloads/CURRICULUM.md` Phase 4

**状態：Phase 4 完了。** 3画面がブラウザで動き、§5 の完了条件を満たしている。

**⚠️ バージョン注意**：本計画は **Next.js 16.3.1 系**を前提に書き、現在の実装は **16.3.5 / React 19.2.8**。
ネット上の記事は Next.js 13〜15 時代のものが多く、**キャッシュとデータ更新の作法が大きく変わっている**（§3.4 参照）。
公式ドキュメント（<https://nextjs.org/docs>）を一次情報とすること。

---

## 0. Phase 4 のゴール

```
✓ ブラウザで http://localhost:3000 を開くと家計簿として使える
✓ ホームの入力フォームから支出を登録すると DB に保存され、一覧に反映される
✓ 月次清算画面で集計と送金額が見え、「確認」ボタンで状態が進む
✓ PayPay CSV をアップロードして共有判定 → 支出に昇格できる
✓ カテゴリを追加・編集・アーカイブできる

まだ:
✗ ログイン画面は作らない（認証は Phase 5。モック⑥⑦は Phase 5 で実装）
✗ 別端末（パートナーのスマホ）からは使えない（Phase 7 デプロイが必要）
```

Phase 2 が「厨房を建てた」、Phase 3 が「ウェイターが注文を受けられるようになった」なら、
Phase 4 は **客席を作って、お客さんが実際に注文して料理を食べられるようにする** 段階。

---

## 1. 技術スタックとバージョン

| 項目 | 採用 | 備考 |
| :---- | :---- | :---- |
| フレームワーク | **Next.js 16.3.1**（App Router） | Pages Router は使わない |
| React | 19 系 | Next.js が同梱 |
| 言語 | TypeScript | `/openapi.json` から型を自動生成して活かす |
| CSS | Tailwind CSS | `create-next-app` に同梱 |
| UI 部品 | **shadcn/ui** | コピーして使う方式（node_modules に入らない） |
| パッケージ管理 | npm | バックエンドは uv、フロントは npm |
| 型生成 | `openapi-typescript` | バックエンドの OpenAPI から TS 型を生成 |

---

## 2. 実装ステップ（実績 / 2026-08-25 完了）

> この計画は当初7画面前提で書いた。実装の直前に DESIGN.md §1.7 で**3画面に絞る**判断をしたため、
> ステップも実際にやった順に書き直してある。

### 準備フェーズ
- **A. プロジェクト作成**：`create-next-app` で `frontend/` を作った
- **B. API クライアント基盤**：`lib/api.ts`（`server-only` 付き）。`ApiError` で 400/422/500 を型で区別する
- **C. 共通レイアウト**：`app/layout.tsx`。3画面のナビを置く

### 画面フェーズ（依存の少ない順）
- **D. ホーム**（`/`）— 支出入力・集計・カテゴリ別グラフ・支出一覧（絞り込み/行内編集/削除/ページ送り）。**アプリの主役**
- **E. 月次清算**（`/settlement/[ym]`）— 集計・送金額・状態遷移・月移動・過去履歴
- **F. PayPay 取り込み**（`/paypay-import`）— CSV アップロード・共有/個人の判定・判定済み履歴

### 仕上げ
- **G. エラーハンドリングの統一**：422 の日本語変換を `lib/apiErrors.ts` に共通化
- **H. ローディング状態**：`<Suspense>` + スケルトン
- **I. 3画面のナビ**：PC はトップタブ、スマホはボトムタブ。未判定件数のバッジ付き

### 当初計画から変えたところ

| 当初 | 実際 | 理由 |
| :---- | :---- | :---- |
| shadcn/ui を導入 | **入れなかった**。Tailwind を直接書いた | 3画面・部品も少なく、依存を1つ増やす価値が出なかった（KISS） |
| OpenAPI から型生成 | **手書きした**（`lib/api.ts` 内） | §3.7 参照。型は10個程度で、生成の仕組みを足すほどではない |
| カテゴリ管理画面を作る | **廃止**。入力欄の「+ 新規」に統合 | DESIGN.md §1.7。年に数回しか使わない |
| 支出一覧を別画面にする | **ホームに統合** | 同上 |
| サイドナビ + トップナビ | **タブ3つ**（PC は上、スマホは下） | 3画面ならタブで足りる |

**Phase 5 に送るもの**：ログイン画面 / アカウント設定（認証が必要なため）

---

## 3. 設計方針

### 3.1 ディレクトリ構成（DESIGN.md §3.2 / §5.2 に準拠）

実装後の実物。`★` がクライアントコンポーネント（`'use client'`）。

```
frontend/
├── app/                              # 層③：ページ本体（全てサーバー）
│   ├── layout.tsx                    # 共通レイアウト。ナビを置く
│   ├── globals.css
│   ├── page.tsx                      # ① ホーム
│   ├── settlement/
│   │   ├── page.tsx                  #   /settlement → 今月にリダイレクト
│   │   └── [ym]/page.tsx             # ② 月次清算
│   └── paypay-import/
│       └── page.tsx                  # ③ PayPay 取り込み
├── features/                         # 層②：ビジネス概念（API 接続を担う）
│   ├── navigation/
│   │   ├── AppNavSection.tsx         #   未判定件数を取得（サーバー）
│   │   └── AppNav.tsx                # ★ 現在地の判定（usePathname）
│   ├── expenses/
│   │   ├── actions.ts                #   Server Actions（作成・更新・削除）
│   │   ├── constants.ts              #   支払い手段のラベル等
│   │   ├── query.ts                  #   URL クエリ ⇄ API パラメータの変換
│   │   ├── RecentExpenses.tsx        #   一覧テーブル（サーバー）
│   │   ├── QuickExpenseForm.tsx      # ★ 入力フォーム
│   │   ├── ExpenseFilters.tsx        # ★ 絞り込み
│   │   └── ExpenseRow.tsx            # ★ 行内編集・削除
│   ├── settlement/
│   │   ├── actions.ts                #   close / confirm
│   │   ├── MonthSummary.tsx          #   今月の集計（サーバー）
│   │   ├── SettlementDetail.tsx      #   送金額・内訳（サーバー）
│   │   ├── SettlementHistory.tsx     #   過去の清算（サーバー）
│   │   ├── MonthNav.tsx              #   月移動（サーバー。<Link> だけ）
│   │   └── SettlementActionButton.tsx # ★ 「締める」「確認する」
│   ├── categories/
│   │   ├── actions.ts
│   │   └── NewCategoryButton.tsx     # ★ 「+ 新規」
│   └── paypay-import/
│       ├── actions.ts                #   import / adopt / exclude
│       ├── StagingList.tsx           #   未判定の一覧（サーバー）
│       ├── ProcessedHistory.tsx      #   判定済み履歴（サーバー）
│       ├── UploadForm.tsx            # ★ CSV 選択
│       └── StagingCard.tsx           # ★ 1行ごとの判定
├── lib/
│   ├── api.ts                        #   fetch ラッパ + 型。`server-only` 付き
│   └── apiErrors.ts                  #   422 → 日本語メッセージの変換
├── .env.local                        # git 管理外
├── package.json
└── tsconfig.json
```

**依存の向き**：`app/ → features/ → lib/` の一方向のみ。

**当初計画との違い：`components/ui/` を作らなかった。**
shadcn/ui を入れず Tailwind を直接書いたため、層①に置くべき汎用部品が出てこなかった。
3画面・部品も少ない今の規模では、層を1つ空で用意するより持たない方が素直だと判断した（KISS / YAGNI）。
共通化したくなったら、そのときに `components/ui/` を作って移す。

**`lib/api.ts` の先頭に `import "server-only"` を書いている。**
これを付けると、クライアントコンポーネントから誤って import した瞬間に**ビルドが落ちる**。
API の URL と `API_USER_ID` がブラウザ側のバンドルに混入するのを、コンパイル時に防ぐため。

### 3.2 サーバーコンポーネント / クライアントコンポーネントの判断

**判断基準は1つだけ**：

```
「ブラウザでしか出来ないこと」を使うか？
  ├─ 使う   → クライアント（'use client' を書く）
  └─ 使わない → サーバー（デフォルト。何も書かない）
```

「ブラウザでしか出来ないこと」＝ `onClick` / `onChange` / `useState` / `useEffect` / `localStorage` / `window`

**重要**：サーバーコンポーネントは「サーバーでしか動かない」のではなく、**ブラウザに JavaScript を送らない**のが本質。

**`'use client'` は「葉」に付ける。「根」に付けない。**
ページ（`app/*/page.tsx`）に付けると配下の全コンポーネントがクライアントになり、
サーバーコンポーネントの利点が消える。

### 3.3 画面ごとの振り分け

| 画面 | サーバー | クライアント |
| :---- | :---- | :---- |
| ① ホーム | ページ本体・集計・**カテゴリ別グラフ**・支出一覧・ページ送り | 入力フォーム・絞り込み・行内編集 |
| ② 月次清算 | ページ本体・集計・送金額・内訳・**月ナビ**・過去履歴 | 「確認する」ボタン |
| ③ PayPay 取り込み | ページ本体・未判定の一覧・判定済み履歴 | CSV 選択・1行ごとの判定 |
| （共通）ナビ | 未判定件数の取得 | 現在地の判定（`usePathname`） |

**実装後の実測：サーバー 17 ファイル / クライアント 8 ファイル / Server Action 4 ファイル。**

計画時から変わった点が2つある。

1. **カテゴリ別グラフはサーバーのままにできた。** 当初クライアント想定だったが、
   グラフライブラリを使わず CSS の `width: %` で棒を描いたので JS が要らなくなった。
2. **月セレクタ・フィルタもサーバーのままにできた。** 状態を `useState` ではなく
   **URL**（`/settlement/2026-08`、`/?category=1`）に持たせたため、`<Link>` 遷移で済む。
   実測：`curl "/?category=1"` が返す HTML の時点で既に3件に絞られている。

つまり**「操作がある = クライアント」ではなく、「ブラウザの API が要る = クライアント」**が正しい基準だった。

### 3.4 データ取得と更新（⚠️ Next.js 16 の作法）

**ネットの古い記事と違う点**。ここを間違えると「登録したのに画面が変わらない」で詰まる。

| 項目 | Next.js 13〜14（古い情報） | **Next.js 16（現在）** |
| :---- | :---- | :---- |
| `fetch` のキャッシュ | **デフォルトでキャッシュされる** | **キャッシュされない**。キャッシュしたいときだけ `use cache` を書く |
| キャッシュ回避 | `{ cache: "no-store" }` を明示 | 不要（デフォルトがその挙動） |
| 更新後の画面反映 | `router.refresh()` をクライアントで呼ぶ | Server Action 内で **`refresh()` from `next/cache`** |
| 変更処理の書き方 | クライアントから `fetch(..., {method:"POST"})` | **Server Actions**（`'use server'`） |

#### 表示（GET）：サーバーコンポーネントで直接 await

```tsx
// app/expenses/page.tsx（'use client' なし）
export default async function ExpensesPage() {
  const data = await apiGet("/api/expenses/?year_month=2026-08")
  return <ExpenseList items={data.items} />
}
```

- コンポーネント関数を `async` にできるのがサーバーコンポーネントの特権
- `useState` / `useEffect` / ローディング管理が**一切不要**
- API のレスポンスがブラウザの Network タブに**出ない**（サーバー内で完結）

#### 変更（POST / PATCH / DELETE）：Server Actions

```ts
// features/expenses/actions.ts
'use server'

import { refresh } from 'next/cache'

export async function createExpense(formData: FormData) {
  const res = await fetch(`${process.env.API_BASE_URL}/api/expenses/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Id': '1' },
    body: JSON.stringify({
      amount: Number(formData.get('amount')),
      occurred_on: String(formData.get('occurred_on')),
      category_id: Number(formData.get('category_id')),
      payment_method: String(formData.get('payment_method')),
      note: formData.get('note') || null,
    }),
  })

  if (!res.ok) {
    // 422 の detail を取り出して返す（§3.6）
    return { error: await parseApiError(res) }
  }

  refresh()   // ← これで一覧などのサーバーコンポーネントが再実行される
}
```

```tsx
// features/expenses/QuickExpenseForm.tsx
'use client'
import { useActionState } from 'react'
import { createExpense } from './actions'

export function QuickExpenseForm() {
  const [state, action, pending] = useActionState(createExpense, null)
  return (
    <form action={action}>
      <input name="amount" type="number" />
      {/* ... */}
      <button disabled={pending}>{pending ? '記録中…' : '記録'}</button>
    </form>
  )
}
```

**Server Actions を採用する理由**：
1. **API の URL がブラウザに露出しない**（Next.js サーバー経由で FastAPI を呼ぶ）
2. **CORS 設定が不要**（ブラウザは Next.js しか叩かない）
3. **Phase 5 で有利** — JWT を HttpOnly Cookie で持つとき、Cookie の読み書きが Next.js サーバー側で完結する
4. `useActionState` で pending 状態が標準で取れる

第五回スライドの「秘密」の思想（鍵をブラウザに渡さない）とも整合する。

### 3.5 API の URL と環境変数

**同じ API でも、呼ぶ場所で URL が変わりうる**（DESIGN.md §0.4 のコンテナ構成に移行したとき）。

```bash
# frontend/.env.local（git 管理外）
API_BASE_URL=http://localhost:8000              # サーバー側で使う（ブラウザに渡らない）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000  # クライアント側で使う（ブラウザに渡る）
```

| 変数 | 誰が使う | ブラウザに渡るか |
| :---- | :---- | :---- |
| `API_BASE_URL` | サーバーコンポーネント・Server Actions | **渡らない** |
| `NEXT_PUBLIC_API_BASE_URL` | クライアントコンポーネント | **渡る** |

**`NEXT_PUBLIC_` に秘密を入れてはいけない**（第五回スライド「秘密」の失敗例そのもの）。
API の URL は秘密ではないので置いてよい。

Server Actions を主に使う方針なので、`NEXT_PUBLIC_` はほぼ不要になる見込み。

### 3.6 エラーハンドリング

バックエンドが返すステータスごとに扱いを変える。

| ステータス | 意味 | フロントの対応 |
| :---- | :---- | :---- |
| **422** | Pydantic のバリデーション違反 | `detail[].loc` で**該当フィールドの下**にメッセージ |
| **400** | 業務ルール違反（済みの行を再 adopt 等） | 画面上部にメッセージ |
| **401** | 未認証 | ログイン画面へ（Phase 5） |
| **404** | 対象が存在しない | 「見つかりません」表示 |
| **500** | サーバー側の不具合 | 「エラーが発生しました。ID: xxx」と **`X-Request-Id` を見せる** |

422 のレスポンス例：

```json
{
  "detail": [{
    "type": "greater_than",
    "loc": ["body", "amount"],
    "msg": "Input should be greater than 0",
    "input": 0
  }]
}
```

`loc: ["body", "amount"]` → 金額の入力欄の下にメッセージを出す。
**画面全体のエラー表示にしてはいけない**（ユーザーがどこを直せばよいか分からない）。

500 のとき `X-Request-Id` を見せる設計は、Phase 3 でミドルウェアに入れた仕組みが効く
（レスポンスヘッダに返している）。ユーザーが「ID: 26052f34」と言えばサーバーログを grep できる。

### 3.7 OpenAPI から型を生成する（カリキュラム推奨）

> **OpenAPI（`/docs` の API 仕様書）を中間言語**として、「API の仕様を先に決める → フロントで使う → 使いにくければ API を直す」（カリキュラム Phase 4）

```bash
cd frontend
npx openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts
```

Pydantic で書いた型が、そのまま TypeScript の型になる：

```typescript
// lib/api-types.ts（自動生成。手で編集しない）
export interface components {
  schemas: {
    ExpenseCreate: {
      amount: number
      occurred_on: string
      category_id: number
      payment_method: "cash" | "credit_card" | "paypay" | "wechatpay"
      note?: string | null
      paid_by?: number | null
    }
  }
}
```

バックエンドで型を変えたら再生成するだけでフロントも追従する。手で書き写さない。

**運用ルール**：API を変更したら必ず再生成する。`package.json` に script を置く。

```json
{ "scripts": { "gen:api": "openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts" } }
```

---

## 4. Phase 3 との往復（カリキュラムが想定している動き）

> Phase 3 と往復することになります。OpenAPI を中間言語として、「API の仕様を先に決める → フロントで使う → 使いにくければ API を直す」というサイクルで進めると迷子になりにくいです。（カリキュラム Phase 4）

**すでに判明している「API を直す必要がある箇所」**（Phase 3 の診断で発見済み）：

| 課題 | 内容 | どの画面で困るか |
| :---- | :---- | :---- |
| `paid_by` のバリデーション | 存在しない user_id を送ると 500 になる（422 であるべき） | ① ホームの支払者切替 |
| カテゴリ一括並び替え API がない | 1件ずつ `PATCH` するしかない | ⑤ ドラッグ並び替え |
| 未取込 PayPay 件数を数える手段 | 一覧を丸ごと取得して数えている | ① 「未取込 PayPay 行: 12」の表示 |
| ログに `actor` / `duration_ms` がない | エラー調査で「誰の操作か」が分からない | 全画面（デバッグ時） |

**方針**：先回りして直さず、**実際に困った時点で直す**。
「使いにくいと分かってから直す」のがカリキュラムの想定する往復サイクル。

---

## 5. 完了の目安

カリキュラム Phase 4 の完了条件：

> ブラウザ操作 → API 呼び出し → DB 保存 → 一覧表示が一気通貫で動く。

具体的には以下がすべてブラウザで完結すること：

- [x] ホームで支出を登録 → 集計・グラフ・一覧が同時に更新される
- [x] 月・カテゴリ・支払い手段で絞り込める（URL クエリ経由）
- [x] 支出を編集・削除できる（行内で直接）
- [x] 月次清算画面で合計・1人あたり・送金額・カテゴリ内訳が見える
- [x] 「確認する」を押すと状態が `closed → partially_confirmed → settled` と進む
- [x] PayPay CSV をアップロード → 未判定行が並ぶ → 共有判定 → 支出に昇格
- [x] カテゴリを追加できる（入力欄の「+ 新規」。編集・アーカイブは作らない ← §2 参照）
- [x] 金額に 0 を入れると**該当フィールドの下**にエラーが出る（422 の扱い）
- [x] 3画面をナビで行き来できる。スマホ幅ではボトムタブに切り替わる

**ビルド検証**：`npx tsc --noEmit` エラーなし／`npm run build` 成功（全ルートが `ƒ (Dynamic)`）／`npm run lint` 警告なし。

---

## 6. 見直しの前提（Phase 4 で決めきらないもの）

- **ログイン画面・アカウント設定**：認証が必要なので Phase 5 で実装
- **グラフライブラリの選定**：**素の CSS（横棒）で作り、ライブラリは入れなかった**。結果としてグラフがサーバーコンポーネントのままでいられた（§3.3 参照）
- **ダークモード**：`users.theme_preference` カラムは用意済みだが、UI 実装は Phase 5（アカウントメニューと同時）
- **監査ログ画面（events 閲覧）**：DESIGN.md に設計がない。必要になったらモック⑧として追加を検討
- **モバイル対応**：モックはデスクトップ前提。スマホで使うなら Phase 7（デプロイ）と併せて検討

---

## 7. 勉強会での発表準備（Phase 4 前半担当）

発表範囲は **「Next.js・API接続」**。カリキュラムの今週のディスカッション3問に答えられる状態を目指す。

### ① クライアントコンポーネントとサーバーコンポーネントの違いは何か？

> **「ブラウザに JavaScript を送るかどうか」の違い**。サーバーコンポーネントは HTML だけ送るので速いが、ユーザー操作に反応できない。だから「表示だけ」はサーバー、「操作がある」はクライアントにする。

実物で語れる材料：§3.3 の画面ごとの振り分け表。

### ② 粒度で分けるか迷った例

**実装しないと語れない。** 先に迷える材料：

> ホームの「今月の合計」と、月次清算画面の「合計」は同じ数字。
> これを共通コンポーネントにするか？
>
> - 共通化する → `features/settlement/SummaryCard.tsx` を両画面で使う
> - 共通化しない → 各ページに書く（座学資料「特定のページでのみ利用する機能は共通化しなくて良い」）
>
> 見た目が違う（KPI カード vs 集計パネル）ので、「データ取得は共通・見た目は別」に分ける案もある。

### ③ API のエラー（422）をフロントでどう扱うべきか

> **422 は「フォームのどこが直せるか」を教えてくれるエラー**なので、`detail[].loc` を見て該当する入力欄の下にメッセージを出す。画面全体のエラー表示にしてはいけない。500 はユーザーが直せないので、`X-Request-Id` を見せて調査できる形にする。

実物で語れる材料：§3.6 の対応表と、Phase 3 で入れた `X-Request-Id` ミドルウェア。

### 発表に向けた推奨アクション（実績）

過去の発表者（第四回・第五回）は**実物のコードを見せていた**。同じ形にした。

結果として**3画面すべて実装した上で発表**することになり、①〜③は全て実体験で語れる。
資料は `slides/`（`phase4_frontend.pptx` と全文テキスト版）。

計測して裏付けを取ったもの：

| 主張 | 裏付け |
| :---- | :---- |
| サーバーコンポーネントはブラウザに JS を送らない | ホームを開いてブラウザが叩いた API が **0 件**。`curl` の HTML に「¥ 16,640」が入っている |
| URL に状態を持たせるとサーバーで絞り込める | `curl "/?category=1"` の時点で **3件 / ¥10,720**（フィルタなしは6件 / ¥16,640） |
| `'use client'` は葉にだけ付ければいい | 実測 **サーバー17 / クライアント8**。ページと layout は1つもクライアントにしていない |
| ネットの情報が古い | Next.js 自身が `AGENTS.md` を自動生成して「訓練データと違う。同梱ドキュメントを読め」と書いていた |

---

## 8. 参考リンク

| 種別 | URL | 用途 |
| :---- | :---- | :---- |
| 公式 | <https://nextjs.org/docs> | Next.js 全般。**一次情報はここ** |
| 公式 | <https://nextjs.org/docs/app/getting-started/fetching-data> | データ取得（サーバー / クライアント） |
| 公式 | <https://nextjs.org/docs/app/getting-started/mutating-data> | Server Actions・`refresh()`・`revalidatePath()` |
| 公式 | <https://nextjs.org/docs/app/getting-started/caching> | キャッシュの考え方（`use cache`） |
| 公式 | <https://ja.react.dev/> | React の基礎（日本語）。`useState` / `useActionState` など |
| 公式 | <https://ui.shadcn.com/> | UI コンポーネント集 |
| 公式 | <https://ui.shadcn.com/docs/installation/next> | Next.js への導入手順 |

**注意**：Next.js は 13 → 16 でデータ取得の作法が大きく変わっている。
検索で出てくる記事の多くは 13〜15 時代のもので、**キャッシュと更新の説明が現在と合わない**。
必ずバージョンを確認すること（§3.4 の対比表を参照）。
