/**
 * 未判定のステージング行を1件表示して、「共有」か「個人」かを決めるカード。
 *
 * ★ クライアントコンポーネント ★
 *
 * カテゴリの選択とメモの入力を持ち、押したボタンによって
 * 呼ぶ Server Action を変える必要があるので 'use client' が要る。
 *
 * 一覧（StagingList）はサーバーコンポーネントのままで、
 * このカードだけがブラウザで動く。
 */
"use client";

import { useActionState } from "react";

import type { Category, StagingRow } from "@/lib/api";

import { adoptRow, excludeRow, type RowActionState } from "./actions";

const INITIAL_STATE: RowActionState = { ok: null, message: null };

const yen = (n: number) => `¥ ${n.toLocaleString("ja-JP")}`;

export function StagingCard({
  row,
  categories,
}: {
  row: StagingRow;
  categories: Category[];
}) {
  // 「共有として登録」と「個人として除外」で別の Server Action を使う。
  // どちらも同じ <form> の中に置き、button の formAction で切り替える。
  const [adoptState, adoptAction, adopting] = useActionState(
    adoptRow,
    INITIAL_STATE,
  );
  const [excludeState, excludeAction, excluding] = useActionState(
    excludeRow,
    INITIAL_STATE,
  );

  const pending = adopting || excluding;
  const state = adoptState.message ? adoptState : excludeState;

  return (
    <li className="rounded-lg border border-gray-200 p-4">
      {/* 店舗名・金額・日付 */}
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-900">
            {row.merchant_name ?? "（店舗名なし）"}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            {row.occurred_on}
            <span className="ml-2 text-gray-400">{row.paypay_txn_id}</span>
          </p>
        </div>
        <p className="shrink-0 text-lg font-bold tabular-nums text-gray-900">
          {yen(row.amount)}
        </p>
      </div>

      {/* 判定 */}
      <form className="mt-3 flex flex-wrap items-end gap-2">
        <input type="hidden" name="staging_id" value={row.id} />

        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-500">カテゴリ</span>
          <select
            name="category_id"
            defaultValue=""
            disabled={pending}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          >
            <option value="">選択</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs text-gray-500">メモ（任意）</span>
          <input
            type="text"
            name="note"
            placeholder={row.merchant_name ?? ""}
            disabled={pending}
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </label>

        <button
          type="submit"
          formAction={adoptAction}
          disabled={pending}
          className="rounded-md bg-gray-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {adopting ? "登録中…" : "共有にする"}
        </button>

        <button
          type="submit"
          formAction={excludeAction}
          disabled={pending}
          className="rounded-md border border-gray-300 px-4 py-1.5 text-sm text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {excluding ? "除外中…" : "個人にする"}
        </button>
      </form>

      {state.message && (
        <p
          className={`mt-2 text-xs ${
            state.ok ? "text-green-700" : "text-red-600"
          }`}
        >
          {state.message}
        </p>
      )}
    </li>
  );
}
