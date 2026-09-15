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
  const [personalCandidates, setPersonalCandidates] = useState<Set<number>>(new Set());
  const [categoryByRow, setCategoryByRow] = useState<Record<number, number>>({});
  const [bulkCategoryId, setBulkCategoryId] = useState("");
  const [excludeState, excludeAction, excluding] = useActionState(excludeRows, INITIAL_STATE);
  const [adoptState, adoptAction, adopting] = useActionState(adoptRows, INITIAL_STATE);

  const personalRows = rows.filter((row) => personalCandidates.has(row.id));
  const sharedRows = rows.filter((row) => !personalCandidates.has(row.id));
  const missingCategoryCount = sharedRows.filter((row) => !categoryByRow[row.id]).length;
  const allSelected = rows.length > 0 && personalRows.length === rows.length;
  const personalTotal = personalRows.reduce((sum, row) => sum + row.amount, 0);
  const sharedTotal = sharedRows.reduce((sum, row) => sum + row.amount, 0);
  const pending = excluding || adopting;
  const sharedItemsJson = JSON.stringify(
    sharedRows.map((row) => ({
      staging_id: row.id,
      category_id: categoryByRow[row.id] ?? 0,
      note: null,
    })),
  );

  function togglePersonal(id: number) {
    setPersonalCandidates((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAllPersonal() {
    setPersonalCandidates(allSelected ? new Set() : new Set(rows.map((row) => row.id)));
  }

  function applyBulkCategory() {
    const categoryId = Number(bulkCategoryId);
    if (!Number.isInteger(categoryId) || categoryId <= 0) return;
    setCategoryByRow((current) => {
      const next = { ...current };
      for (const row of sharedRows) {
        if (!next[row.id]) next[row.id] = categoryId;
      }
      return next;
    });
  }

  return (
    <>
      <div className="sticky top-2 z-10 space-y-3 rounded-xl border border-gray-200 bg-white/95 p-4 shadow-sm backdrop-blur">
        <div className="grid gap-3 md:grid-cols-2">
          <form action={excludeAction} className="rounded-lg bg-gray-50 p-3">
            {personalRows.map((row) => (
              <input key={row.id} type="hidden" name="staging_id" value={row.id} />
            ))}
            <p className="text-xs font-semibold text-gray-500">1. 個人分を選んで確定</p>
            <p className="mt-1 text-sm text-gray-700">
              {personalRows.length} 件・{yen(personalTotal)} を選択中
            </p>
            <button
              type="submit"
              disabled={pending || personalRows.length === 0}
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-800 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {excluding ? "個人分を確定中…" : `選択した ${personalRows.length} 件を個人にする`}
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
            <input type="hidden" name="items" value={sharedItemsJson} />
            <p className="text-xs font-semibold text-emerald-700">2. 残りのカテゴリを入れて共有</p>
            <p className="mt-1 text-sm text-gray-700">
              共有候補 {sharedRows.length} 件・{yen(sharedTotal)}
              {missingCategoryCount > 0 && `（カテゴリ未入力 ${missingCategoryCount} 件）`}
            </p>
            <button
              type="submit"
              disabled={
                pending ||
                personalRows.length > 0 ||
                sharedRows.length === 0 ||
                missingCategoryCount > 0
              }
              className="mt-2 w-full rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {adopting ? "共有分を登録中…" : `残りの ${sharedRows.length} 件を共有にする`}
            </button>
            {personalRows.length > 0 && (
              <p className="mt-1 text-xs text-amber-700">先に選択中の個人分を確定してください</p>
            )}
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

        <div className="flex flex-wrap items-end gap-2 border-t border-gray-100 pt-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs text-gray-500">未入力の共有候補に一括設定</span>
            <select
              value={bulkCategoryId}
              onChange={(event) => setBulkCategoryId(event.target.value)}
              disabled={pending || sharedRows.length === 0}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
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
            type="button"
            onClick={applyBulkCategory}
            disabled={pending || bulkCategoryId === "" || missingCategoryCount === 0}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            未入力すべてに適用
          </button>
        </div>

      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200">
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border-b border-gray-200 bg-gray-50 px-4 py-3 md:grid-cols-[auto_1fr_auto_12rem]">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAllPersonal}
            disabled={pending}
            aria-label="すべて個人候補にする"
            className="size-4 accent-gray-900"
          />
          <button
            type="button"
            onClick={toggleAllPersonal}
            disabled={pending}
            className="text-left text-xs font-semibold text-gray-600"
          >
            {allSelected ? "個人候補をすべて解除" : "すべて個人候補に選択"}
          </button>
          <span className="text-right text-xs font-semibold text-gray-500">金額</span>
          <span className="hidden text-xs font-semibold text-gray-500 md:block">共有カテゴリ</span>
        </div>

        <ul className="divide-y divide-gray-100">
          {rows.map((row) => {
            const isPersonal = personalCandidates.has(row.id);
            return (
              <li
                key={row.id}
                className={`grid grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-3 md:grid-cols-[auto_1fr_auto_12rem] ${
                  isPersonal ? "bg-gray-50" : "bg-white"
                }`}
              >
                <input
                  type="checkbox"
                  checked={isPersonal}
                  onChange={() => togglePersonal(row.id)}
                  disabled={pending}
                  aria-label={`${row.merchant_name ?? "店舗名なし"}を個人候補にする`}
                  className="size-4 accent-gray-900"
                />
                <div className={isPersonal ? "text-gray-400 line-through" : ""}>
                  <p className="text-sm font-semibold">
                    {row.merchant_name ?? "（店舗名なし）"}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {row.occurred_on}
                    <span className="ml-2 text-gray-400">{row.paypay_txn_id}</span>
                  </p>
                </div>
                <p className={`text-right text-sm font-bold tabular-nums ${isPersonal ? "text-gray-400" : "text-gray-900"}`}>
                  {yen(row.amount)}
                </p>
                <select
                  value={categoryByRow[row.id] ?? ""}
                  onChange={(event) =>
                    setCategoryByRow((current) => ({
                      ...current,
                      [row.id]: Number(event.target.value),
                    }))
                  }
                  disabled={pending || isPersonal}
                  aria-label={`${row.merchant_name ?? "店舗名なし"}の共有カテゴリ`}
                  className="col-start-2 col-end-4 rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:bg-gray-100 md:col-start-auto md:col-end-auto"
                >
                  <option value="">カテゴリを選択</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </li>
            );
          })}
        </ul>
      </div>
    </>
  );
}
