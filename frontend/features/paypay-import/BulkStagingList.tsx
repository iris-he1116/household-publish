"use client";

import { useActionState, useState } from "react";

import type { Category, StagingRow } from "@/lib/api";

import { adoptRows, excludeRows, type BatchActionState } from "./actions";

const INITIAL_STATE: BatchActionState = {
  ok: null,
  message: null,
  processedCount: 0,
};

const yen = (amount: number) => `¥ ${amount.toLocaleString("ja-JP")}`;

export function BulkStagingList({
  rows,
  categories,
}: {
  rows: StagingRow[];
  categories: Category[];
}) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [categoryId, setCategoryId] = useState("");
  const [excludeState, excludeAction, excluding] = useActionState(excludeRows, INITIAL_STATE);
  const [adoptState, adoptAction, adopting] = useActionState(adoptRows, INITIAL_STATE);

  const selectedRows = rows.filter((row) => selectedIds.has(row.id));
  const selectedTotal = selectedRows.reduce((sum, row) => sum + row.amount, 0);
  const allSelected = rows.length > 0 && selectedRows.length === rows.length;
  const pending = excluding || adopting;

  function toggleRow(id: number) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelectedIds(allSelected ? new Set() : new Set(rows.map((row) => row.id)));
  }

  const hiddenSelectedIds = selectedRows.map((row) => (
    <input key={row.id} type="hidden" name="staging_id" value={row.id} />
  ));

  return (
    <>
      <div className="sticky top-2 z-10 space-y-3 rounded-xl border border-gray-200 bg-white/95 p-4 shadow-sm backdrop-blur">
        <div>
          <p className="text-xs font-semibold text-gray-500">処理する明細を選択</p>
          <p className="mt-1 text-sm text-gray-700">
            {selectedRows.length} 件・{yen(selectedTotal)} を選択中
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <form action={excludeAction} className="rounded-lg bg-gray-50 p-3">
            {hiddenSelectedIds}
            <p className="text-xs font-semibold text-gray-600">選択した明細が自分だけの支出なら</p>
            <button
              type="submit"
              disabled={pending || selectedRows.length === 0}
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-800 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {excluding ? "個人分を確定中…" : `選択した ${selectedRows.length} 件を個人にする`}
            </button>
            {excludeState.message && (
              <p
                aria-live="polite"
                className={`mt-2 text-xs ${excludeState.ok ? "text-green-700" : "text-red-600"}`}
              >
                {excludeState.message}
              </p>
            )}
          </form>

          <form action={adoptAction} className="rounded-lg bg-emerald-50 p-3">
            {hiddenSelectedIds}
            <label className="flex flex-col gap-1">
              <span className="text-xs font-semibold text-emerald-700">
                選択した明細を共有するカテゴリ
              </span>
              <select
                name="category_id"
                value={categoryId}
                onChange={(event) => setCategoryId(event.target.value)}
                disabled={pending}
                className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">カテゴリを選択</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              disabled={pending || selectedRows.length === 0 || categoryId === ""}
              className="mt-2 w-full rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {adopting ? "共有分を登録中…" : `選択した ${selectedRows.length} 件を共有にする`}
            </button>
            {adoptState.message && (
              <p
                aria-live="polite"
                className={`mt-2 text-xs ${adoptState.ok ? "text-green-700" : "text-red-600"}`}
              >
                {adoptState.message}
              </p>
            )}
          </form>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200">
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border-b border-gray-200 bg-gray-50 px-4 py-3">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
            disabled={pending}
            aria-label="すべて選択"
            className="size-4 accent-blue-700"
          />
          <button
            type="button"
            onClick={toggleAll}
            disabled={pending}
            className="text-left text-xs font-semibold text-gray-600"
          >
            {allSelected ? "すべての選択を解除" : "すべて選択"}
          </button>
          <span className="text-right text-xs font-semibold text-gray-500">金額</span>
        </div>

        <ul className="divide-y divide-gray-100">
          {rows.map((row) => {
            const selected = selectedIds.has(row.id);
            return (
              <li
                key={row.id}
                className={`grid grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-3 ${
                  selected ? "bg-blue-50" : "bg-white"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => toggleRow(row.id)}
                  disabled={pending}
                  aria-label={`${row.merchant_name ?? "店舗名なし"}を選択`}
                  className="size-4 accent-blue-700"
                />
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    {row.merchant_name ?? "（店舗名なし）"}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {row.occurred_on}
                    <span className="ml-2 text-gray-400">{row.paypay_txn_id}</span>
                  </p>
                </div>
                <p className="text-right text-sm font-bold tabular-nums text-gray-900">
                  {yen(row.amount)}
                </p>
              </li>
            );
          })}
        </ul>
      </div>
    </>
  );
}
