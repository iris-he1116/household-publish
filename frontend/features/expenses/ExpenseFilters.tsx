/**
 * 支出一覧の絞り込みバー（モック① の「◂ 2026-08 ▸ / カテゴリ ▾ / …」に対応）。
 *
 * ★ 必要最小限のクライアントコンポーネント ★
 *
 * ここが 'use client' なのは `<select>` の onChange を拾うためだけ。
 * 「今どの条件か」は自分では持たず、props（= URL から復元した状態）で受け取る。
 * 選ばれた値は state ではなく URL に書き戻し、
 * 絞り込み後の一覧はサーバーコンポーネントが作り直す。
 *
 * ## <Link> と useRouter を使い分けている理由
 *
 * - 月の前後移動・クリア → `<Link>`
 *   行き先が押す前から決まっている。ただのリンクなので JavaScript が
 *   動かなくても機能するし、Next.js が事前読み込み（prefetch）してくれる。
 *
 * - 月の直接選択 / カテゴリ / 手段 / 支払者 → `useRouter().replace()`
 *   行き先が「選ばれた値」で決まるので、リンクにするなら選択肢の数だけ
 *   <a> を並べることになる。素直に onChange で遷移させる。
 *   push ではなく replace なのは、絞り込みを3回変えたあとに戻るボタンを
 *   押したとき、履歴を3回さかのぼらされるのを避けるため。
 *   scroll: false は、一覧の位置にいるのに毎回ページ先頭へ飛ばされないように。
 */
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { PAYERS, PAYMENT_METHODS } from "./constants";
import {
  buildHref,
  hasNarrowingFilter,
  shiftMonth,
  type ExpenseQueryState,
} from "./query";
// `import type` はコンパイル時に消えるので、
// server-only な @/lib/api がブラウザ側のバンドルに入ることはない。
import type { Category } from "@/lib/api";

type Props = {
  /** 今の絞り込み条件（支出ページが URL から復元したもの）。 */
  state: ExpenseQueryState;
  /** サーバー側で getCategories() した結果。 */
  categories: Category[];
};

export function ExpenseFilters({ state, categories }: Props) {
  const router = useRouter();

  const go = (changes: Partial<ExpenseQueryState>) => {
    router.replace(buildHref(state, changes), { scroll: false });
  };

  /** select の値は文字列。空文字を「絞り込みなし」として扱う。 */
  const toId = (value: string) => (value === "" ? null : Number(value));

  return (
    <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center">
      {/* 月の前後移動 */}
      <div className="col-span-2 grid grid-cols-[2.5rem_minmax(0,1fr)_2.5rem] items-center gap-2 sm:col-span-1 sm:grid-cols-[2.5rem_9.5rem_2.5rem]">
        <MonthLink
          href={buildHref(state, { yearMonth: shiftMonth(state.yearMonth, -1) })}
          label="前の月"
        >
          ◂
        </MonthLink>
        <input
          type="month"
          aria-label="表示する月を選択"
          value={state.yearMonth}
          onChange={(event) => {
            if (event.target.value) go({ yearMonth: event.target.value });
          }}
          className="min-w-0 w-full cursor-pointer rounded-md border border-gray-200 bg-white px-3 py-2 text-center text-sm font-bold tabular-nums text-gray-900 shadow-sm transition hover:border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <MonthLink
          href={buildHref(state, { yearMonth: shiftMonth(state.yearMonth, 1) })}
          label="次の月"
        >
          ▸
        </MonthLink>
      </div>

      <select
        aria-label="カテゴリで絞り込む"
        value={state.categoryId === null ? "" : String(state.categoryId)}
        onChange={(e) => go({ categoryId: toId(e.target.value) })}
        className={selectClass}
      >
        <option value="">カテゴリ：すべて</option>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>

      <select
        aria-label="支払い手段で絞り込む"
        value={state.paymentMethod ?? ""}
        onChange={(e) =>
          go({ paymentMethod: e.target.value === "" ? null : e.target.value })
        }
        className={selectClass}
      >
        <option value="">支払い手段：すべて</option>
        {PAYMENT_METHODS.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>

      <select
        aria-label="支払者で絞り込む"
        value={state.paidBy === null ? "" : String(state.paidBy)}
        onChange={(e) => go({ paidBy: toId(e.target.value) })}
        className={selectClass}
      >
        <option value="">支払者：すべて</option>
        {PAYERS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>

      {/*
        絞り込みが掛かっているときだけ出す。
        表示中の月は残し、カテゴリ・手段・支払者だけを外す。
        （月は必ず何かの値を持つので「解除」という概念が無いため）
      */}
      {hasNarrowingFilter(state) && (
        <Link
          href={buildHref(state, {
            categoryId: null,
            paymentMethod: null,
            paidBy: null,
          })}
          scroll={false}
          className="rounded-md px-2 py-1.5 text-sm text-blue-600 hover:bg-blue-50 hover:underline"
        >
          クリア
        </Link>
      )}
    </div>
  );
}

const selectClass =
  "min-w-0 w-full rounded-md border border-gray-200 px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400 sm:w-auto";

function MonthLink({
  href,
  label,
  children,
}: {
  href: string;
  label: string;
  children: string;
}) {
  return (
    <Link
      href={href}
      scroll={false}
      aria-label={label}
      className="flex size-10 items-center justify-center rounded-md border border-gray-200 bg-white text-sm text-gray-500 transition hover:border-gray-300 hover:bg-gray-50 hover:text-gray-900"
    >
      {children}
    </Link>
  );
}
