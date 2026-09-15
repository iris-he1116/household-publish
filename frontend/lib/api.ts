/**
 * バックエンド（FastAPI）を呼ぶための共通クライアント。
 *
 * ## サーバー専用
 *
 * このファイルは **サーバーコンポーネントと Server Actions からのみ** 使う。
 * `API_BASE_URL` に NEXT_PUBLIC_ が付いていないため、
 * クライアントコンポーネントから import すると値が undefined になる。
 *
 * これは意図的な設計:
 *   - API の URL がブラウザに露出しない
 *   - CORS 設定が不要（ブラウザは Next.js しか叩かない）
 *   - JWT を Cookie に入れたとき、Cookie の扱いがサーバー側で完結する
 *
 * ## 認証（Phase 5）
 *
 * ブラウザ → Next.js の Cookie を、そのまま Next.js → FastAPI に転送する。
 * ブラウザ側で JWT を扱うコードは1行も無い（HttpOnly なので読めない）。
 *
 *     ブラウザ  --Cookie-->  Next.js(サーバー)  --Cookie-->  FastAPI
 *
 * FastAPI はリクエストごとに新しい JWT を Set-Cookie で返す（スライディング期限）。
 * ただし **Next.js はサーバーコンポーネントから Cookie を書けない**
 * （node_modules/next/dist/docs/01-app/03-api-reference/04-functions/cookies.md:74
 *   「HTTP does not allow setting cookies after streaming starts」）。
 * そのため期限の延長は Server Actions 経由の更新操作のときだけ反映される。
 * 閲覧だけで30日放置した場合は再ログインになるが、実運用では支出を入力するので問題ない。
 */
import "server-only";

import { cookies } from "next/headers";

const BASE = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

/** バックエンドと合わせる Cookie 名（backend/app/api/deps.py の SESSION_COOKIE）。 */
export const SESSION_COOKIE = "household_session";

/** API が 2xx を返さなかったときに投げる。 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: unknown,
    readonly requestId: string | null,
  ) {
    super(`API ${status}`);
    this.name = "ApiError";
  }
}

/** 未ログイン（401）。呼び出し側でログイン画面に飛ばすために型で区別する。 */
export class UnauthorizedError extends ApiError {
  constructor(detail: unknown, requestId: string | null) {
    super(401, detail, requestId);
    this.name = "UnauthorizedError";
  }
}

/**
 * FastAPI が返した Set-Cookie をそのまま持ち回るための型。
 * Server Actions 側で cookies().set() に反映する。
 */
export type ApiResult<T> = { data: T; setCookie: string | null };

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  // ブラウザから来た Cookie を FastAPI に転送する
  const jar = await cookies();
  const session = jar.get(SESSION_COOKIE)?.value;

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(session ? { Cookie: `${SESSION_COOKIE}=${session}` } : {}),
      ...init?.headers,
    },
    // Next.js 16 では fetch は既定でキャッシュされないが、
    // 「毎回最新を取る」意図をコード上で明示しておく。
    cache: "no-store",
  });

  if (!res.ok) {
    // 500 のときサーバーログと突き合わせられるよう request_id を拾う
    const requestId = res.headers.get("X-Request-Id");
    let detail: unknown = null;
    try {
      detail = (await res.json())?.detail ?? null;
    } catch {
      detail = await res.text().catch(() => null);
    }
    if (res.status === 401) throw new UnauthorizedError(detail, requestId);
    throw new ApiError(res.status, detail, requestId);
  }

  const setCookie = res.headers.get("set-cookie");
  if (res.status === 204) return { data: undefined as T, setCookie };
  return { data: (await res.json()) as T, setCookie };
}

// --- 表示用（サーバーコンポーネントから使う。Cookie は更新できないので捨てる）---

export const apiGet = async <T>(path: string): Promise<T> =>
  (await request<T>(path)).data;

// --- 更新用（Server Actions から使う。setCookie を呼び出し側で反映する）---

export const apiPostRaw = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const apiPost = async <T>(path: string, body: unknown): Promise<T> =>
  (await apiPostRaw<T>(path, body)).data;

export const apiPatch = async <T>(path: string, body: unknown): Promise<T> =>
  (await request<T>(path, { method: "PATCH", body: JSON.stringify(body) })).data;

// DELETE は 204（本文なし）が返るので、返り値は無い。
export const apiDelete = async (path: string): Promise<void> => {
  await request<void>(path, { method: "DELETE" });
};

// ============================================================
// 型（バックエンドの Pydantic スキーマに対応）
//
// 本来は `npx openapi-typescript http://localhost:8000/openapi.json` で
// 自動生成する（PHASE4_PLAN.md §3.7）。今は必要な分だけ手で定義している。
// ============================================================

export type CategoryBreakdown = {
  category_id: number;
  category_name: string;
  amount: number;
  count: number;
};

export type PaymentMethodBreakdown = {
  payment_method: string;
  amount: number;
};

export type SettlementSummary = {
  year_month: string;
  status: "in_progress" | "closed" | "partially_confirmed" | "settled";
  has_stale_updates: boolean;
  total_amount: number;
  per_person_share: number;
  user_a_paid: number;
  user_b_paid: number;
  transfer_from_b_to_a: number;
  expense_count: number;
  categories: CategoryBreakdown[];
  payment_methods: PaymentMethodBreakdown[];
  confirmed_at_user_a: string | null;
  confirmed_at_user_b: string | null;
};

export type Expense = {
  id: number;
  paid_by: number;
  amount: number;
  occurred_on: string;
  category_id: number;
  payment_method: string;
  note: string | null;
  source_staging_id: number | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
};

export type ExpenseListResponse = {
  items: Expense[];
  total: number;
  total_amount: number;
};

export type Category = {
  id: number;
  name: string;
  display_order: number;
  color: string | null;
  is_archived: boolean;
};

/**
 * PayPay 履歴の取り込み行（共有判定の前後）。
 *
 * DESIGN.md §2.6: CSV を取り込むと pending で入り、
 * 「共有」と判定すると adopted になって Expense に昇格する。
 */
export type StagingRow = {
  id: number;
  imported_by: number;
  imported_at: string;
  occurred_on: string;
  amount: number;
  merchant_name: string | null;
  paypay_txn_id: string;
  status: "pending" | "adopted" | "excluded";
  linked_expense_id: number | null;
};

/** CSV アップロードの結果。 */
export type CsvImportResult = {
  total_rows: number;
  new_rows: number;
  duplicate_rows: number;
};

/** PayPay の一括判定結果。 */
export type BatchActionResult = {
  processed_count: number;
  total_amount: number;
};

/** 月次清算の状態レコード（一覧用。集計は含まない）。 */
export type Settlement = {
  year_month: string;
  status: "in_progress" | "closed" | "partially_confirmed" | "settled";
  confirmed_at_user_a: string | null;
  confirmed_at_user_b: string | null;
  closed_at: string | null;
  settled_at: string | null;
  has_stale_updates: boolean;
};

// ============================================================
// 呼び出し関数
// ============================================================

export const getSummary = (yearMonth: string) =>
  apiGet<SettlementSummary>(`/api/settlements/${yearMonth}`);

/**
 * 支出一覧の絞り込み条件。すべて省略可。
 *
 * 引数を並べるのではなくオブジェクトにしているのは、
 * 条件が5つ以上あって順番を覚えられないため（`getExpenses(ym, null, null, 1, 20)` は読めない）。
 */
export type ExpenseQuery = {
  /** "YYYY-MM"。省略すると全期間。 */
  yearMonth?: string | null;
  categoryId?: number | null;
  paymentMethod?: string | null;
  paidBy?: number | null;
  limit?: number;
  offset?: number;
};

export const getExpenses = (query: ExpenseQuery = {}) => {
  // null / undefined の条件はクエリに載せない（載せるとバックエンドが 422 を返す）。
  const params = new URLSearchParams();
  if (query.yearMonth) params.set("year_month", query.yearMonth);
  if (query.categoryId != null)
    params.set("category_id", String(query.categoryId));
  if (query.paymentMethod) params.set("payment_method", query.paymentMethod);
  if (query.paidBy != null) params.set("paid_by", String(query.paidBy));
  params.set("limit", String(query.limit ?? 50));
  params.set("offset", String(query.offset ?? 0));

  return apiGet<ExpenseListResponse>(`/api/expenses/?${params}`);
};

export const getCategories = () =>
  apiGet<Category[]>(`/api/categories/`);

/** 清算した月の一覧（新しい順）。過去の清算履歴の表示に使う。 */
export const getSettlements = () =>
  apiGet<Settlement[]>(`/api/settlements/`);

/**
 * PayPay 取り込みのステージング行を取る。
 *
 * `only_mine=true`（既定）だと、サーバーがログイン中のユーザーを見て
 * 自分がアップロードした分だけを返す。相手の履歴は見えない。
 */
export const getStagingRows = (status?: StagingRow["status"]) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  return apiGet<StagingRow[]>(`/api/paypay-import/staging?${params}`);
};

/** ログイン中のユーザー。未ログインなら UnauthorizedError。 */
export type Me = {
  id: number;
  username: string;
  name: string;
  display_color: string | null;
};

export const getMe = () => apiGet<Me>("/api/auth/me");
