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
 *   - Phase 5 で JWT を Cookie に入れるとき、Cookie の扱いがサーバー側で完結する
 */
import "server-only";

const BASE = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
const USER_ID = process.env.API_USER_ID ?? "1";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      // Phase 3 の暫定認証。Phase 5 で Cookie 由来の JWT に差し替える。
      "X-User-Id": USER_ID,
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
    throw new ApiError(res.status, detail, requestId);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const apiGet = <T>(path: string) => request<T>(path);

export const apiPost = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const apiPatch = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body) });

// DELETE は 204（本文なし）が返るので、返り値は無い。
export const apiDelete = (path: string) =>
  request<void>(path, { method: "DELETE" });

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
 * `only_mine=true`（既定）だと、サーバーが X-User-Id を見て
 * 自分がアップロードした分だけを返す。相手の履歴は見えない。
 */
export const getStagingRows = (status?: StagingRow["status"]) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  return apiGet<StagingRow[]>(`/api/paypay-import/staging?${params}`);
};
