/**
 * 支出一覧の絞り込み条件と、URL のクエリパラメータの相互変換。
 *
 * ★ フィルタの状態は useState ではなく URL で持つ ★
 *
 * useState にすると、
 *   1. その部品がクライアントコンポーネントになる
 *   2. 条件が変わったとき一覧を取り直すために useEffect + fetch が要る
 *   3. 一覧そのものもクライアントコンポーネントになる
 * と芋づる式に広がっていく。
 *
 * URL に持たせれば app/page.tsx が searchParams として受け取れるので、
 * 絞り込んだ結果をサーバーで組み立てて返せる。
 * 一覧はサーバーコンポーネントのままでいられるし、
 * 「この条件の画面」をそのままブックマーク・共有・リロードできる。
 *
 *   /?ym=2026-08&category=1&method=cash&payer=2&page=2
 */
import { isPayer, isPaymentMethod } from "./constants";

/** 1ページあたりの件数。 */
export const PAGE_SIZE = 20;

/** URL のクエリ名。URL は人が読むものなので短い名前にしている。 */
export const PARAM = {
  yearMonth: "ym",
  categoryId: "category",
  paymentMethod: "method",
  paidBy: "payer",
  page: "page",
} as const;

/** 画面が今表示している条件。URL から復元でき、URL に戻せる。 */
export type ExpenseQueryState = {
  /** "YYYY-MM"。必ず値が入る（未指定なら今月）。 */
  yearMonth: string;
  categoryId: number | null;
  paymentMethod: string | null;
  paidBy: number | null;
  /** 1始まり。 */
  page: number;
};

/** page.tsx が `await searchParams` で受け取る生の形。 */
type RawSearchParams = Record<string, string | string[] | undefined>;

/** `?ym=a&ym=b` のように同じ名前が複数来ると配列になる。先頭だけ見る。 */
function first(raw: RawSearchParams, name: string): string | null {
  const value = raw[name];
  const text = Array.isArray(value) ? value[0] : value;
  return text === undefined || text === "" ? null : text;
}

function toPositiveInt(text: string | null): number | null {
  if (text === null) return null;
  const n = Number(text);
  return Number.isInteger(n) && n > 0 ? n : null;
}

/**
 * "YYYY-MM" として使える文字列か。
 *
 * 月は 01〜12 だけ。`2026-13` は形は合っていても、
 * バックエンドが日付を組み立てられずに 500 を返すので、ここで弾く。
 * 年を 1000〜2999 に限っているのも同じ理由
 * （`0000-01` も `9999-12` も Python の date の範囲外になる）。
 */
const YEAR_MONTH = /^[12]\d{3}-(0[1-9]|1[0-2])$/;

/**
 * URL のクエリを、そのまま API に渡せる条件に変換する。
 *
 * 壊れた値（`?ym=abc`、`?payer=99` など）は既定に落とす。
 * URL は誰でも書き換えられるので、素通しするとバックエンドが 422 を返し、
 * サーバーコンポーネントが例外で落ちてエラー画面になってしまう。
 */
export function parseQueryState(
  raw: RawSearchParams,
  fallbackYearMonth: string,
): ExpenseQueryState {
  const yearMonth = first(raw, PARAM.yearMonth);
  const paymentMethod = first(raw, PARAM.paymentMethod);
  const paidBy = toPositiveInt(first(raw, PARAM.paidBy));

  return {
    yearMonth:
      yearMonth !== null && YEAR_MONTH.test(yearMonth)
        ? yearMonth
        : fallbackYearMonth,
    categoryId: toPositiveInt(first(raw, PARAM.categoryId)),
    paymentMethod:
      paymentMethod !== null && isPaymentMethod(paymentMethod)
        ? paymentMethod
        : null,
    paidBy: paidBy !== null && isPayer(paidBy) ? paidBy : null,
    page: toPositiveInt(first(raw, PARAM.page)) ?? 1,
  };
}

/**
 * 今の条件から一部だけ変えた URL を作る。
 *
 * 例) 支払い手段だけ現金にする:
 *   buildHref(state, { paymentMethod: "cash" })  → "/?ym=2026-08&method=cash"
 */
export function buildHref(
  state: ExpenseQueryState,
  changes: Partial<ExpenseQueryState>,
): string {
  const next = { ...state, ...changes };

  // ページ番号を明示的に指定したとき以外は1ページ目に戻す。
  // 3ページ目を見ている状態で絞り込むと、該当が1ページ分しかなくて
  // 「何も無い」画面になってしまうため。
  if (changes.page === undefined) next.page = 1;

  const params = new URLSearchParams();
  // 月は常に載せる。URL を見ただけでどの月かわかるようにするため。
  params.set(PARAM.yearMonth, next.yearMonth);
  if (next.categoryId !== null)
    params.set(PARAM.categoryId, String(next.categoryId));
  if (next.paymentMethod !== null)
    params.set(PARAM.paymentMethod, next.paymentMethod);
  if (next.paidBy !== null) params.set(PARAM.paidBy, String(next.paidBy));
  // 1ページ目は既定なので載せない（URL を短く保つ）。
  if (next.page > 1) params.set(PARAM.page, String(next.page));

  return `/?${params.toString()}`;
}

/** 月以外の絞り込みが掛かっているか。「クリア」を出すかどうかの判定に使う。 */
export const hasNarrowingFilter = (state: ExpenseQueryState) =>
  state.categoryId !== null ||
  state.paymentMethod !== null ||
  state.paidBy !== null;

/** "2026-08" の delta か月前後を返す。 */
export function shiftMonth(yearMonth: string, delta: number): string {
  const [year, month] = yearMonth.split("-").map(Number);
  // Date の月は 0 始まり。13月や -1月を渡すと年を自動で繰り上げ／繰り下げてくれる。
  // ローカルタイムゾーンでずれないよう UTC で組み立てる。
  const d = new Date(Date.UTC(year, month - 1 + delta, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}
