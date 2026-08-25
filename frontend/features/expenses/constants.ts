/**
 * 支出まわりの選択肢と表示ラベル。
 *
 * ★ 'use client' も 'use server' も付けない ★
 *
 * 入力フォーム（クライアント）・フィルタ（クライアント）・一覧（サーバー）の
 * 3か所が同じ選択肢を使う。どちらからも import できるように、
 * ただの定数モジュールとしてここに置いている。
 * `@/lib/api` を import していないので、クライアント側に持って行っても安全。
 */

/** 支払い手段。バックエンドの Literal["cash", ...] と一致させる。 */
export const PAYMENT_METHODS = [
  { value: "cash", label: "現金" },
  { value: "credit_card", label: "クレカ" },
  { value: "paypay", label: "PayPay" },
  { value: "wechatpay", label: "WeChat Pay" },
] as const;

/** 支払者。Phase 5 で users テーブルから引くようになるまでの固定値。 */
export const PAYERS = [
  { value: 1, label: "ありす" },
  { value: 2, label: "ひつじ" },
] as const;

/** payment_method の値 → 表示名（一覧の表示用）。 */
export const METHOD_LABEL: Record<string, string> = Object.fromEntries(
  PAYMENT_METHODS.map((m) => [m.value, m.label]),
);

/** users.id → 表示名（一覧の表示用）。 */
export const USER_LABEL: Record<string, string> = Object.fromEntries(
  PAYERS.map((p) => [p.value, p.label]),
);

/** URL クエリで受け取った文字列が、既定の支払い手段かどうか。 */
export const isPaymentMethod = (value: string) =>
  PAYMENT_METHODS.some((m) => m.value === value);

/** URL クエリで受け取った数値が、既定の支払者かどうか。 */
export const isPayer = (value: number) => PAYERS.some((p) => p.value === value);
