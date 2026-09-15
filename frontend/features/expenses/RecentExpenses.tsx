/**
 * 支出の一覧（モック① の「支出一覧」に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * 絞り込みもページ送りも URL のクエリで表現しているので、
 * 「条件に合う分だけを取ってきて表を組み立てる」処理はサーバーで完結する。
 * ブラウザに JavaScript が要るのは、
 *   - 絞り込みの <select>（ExpenseFilters）
 *   - 行内編集と削除（ExpenseRow）
 * の2つの葉だけ。表の枠・見出し・件数・ページ送りはここで HTML になる。
 */
import Link from "next/link";

import { ExpenseFilters } from "./ExpenseFilters";
import { ExpenseRow } from "./ExpenseRow";
import { buildHref, PAGE_SIZE, type ExpenseQueryState } from "./query";
import { getCategories, getExpenses } from "@/lib/api";

const yen = (n: number) => `¥${n.toLocaleString("ja-JP")}`;

export async function RecentExpenses({ state }: { state: ExpenseQueryState }) {
  // 2つの API を並行して呼ぶ（順番に await すると直列になり遅くなる）
  const [list, categories] = await Promise.all([
    getExpenses({
      yearMonth: state.yearMonth,
      categoryId: state.categoryId,
      paymentMethod: state.paymentMethod,
      paidBy: state.paidBy,
      limit: PAGE_SIZE,
      offset: (state.page - 1) * PAGE_SIZE,
    }),
    getCategories(),
  ]);

  // total は「絞り込み後の全件数」。1ページ分の items.length ではない。
  const lastPage = Math.max(1, Math.ceil(list.total / PAGE_SIZE));
  const firstIndex = (state.page - 1) * PAGE_SIZE + 1;
  const lastIndex = firstIndex + list.items.length - 1;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-bold text-gray-900">支出一覧</h1>
        <p className="text-xs text-gray-500">
          全 {list.total} 件 / 合計 {yen(list.total_amount)}
        </p>
      </div>

      <ExpenseFilters state={state} categories={categories} />

      {list.items.length === 0 ? (
        <EmptyMessage state={state} lastPage={lastPage} />
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="block w-full text-sm sm:table">
              <thead className="hidden bg-gray-50 text-xs text-gray-500 sm:table-header-group">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">日付</th>
                  <th className="px-3 py-2 text-left font-medium">カテゴリ</th>
                  <th className="px-3 py-2 text-left font-medium">メモ</th>
                  <th className="px-3 py-2 text-left font-medium">手段</th>
                  <th className="px-3 py-2 text-right font-medium">金額</th>
                  <th className="px-3 py-2 text-left font-medium">支払者</th>
                  <th className="px-3 py-2 text-left font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="block divide-y divide-gray-100 sm:table-row-group">
                {list.items.map((e) => (
                  <ExpenseRow key={e.id} expense={e} categories={categories} />
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            state={state}
            lastPage={lastPage}
            total={list.total}
            firstIndex={firstIndex}
            lastIndex={lastIndex}
          />
        </>
      )}
    </section>
  );
}

// ============================================================
// 画面の部品（このファイルの中だけで使う）
// ============================================================

/**
 * ページ送り。
 *
 * ここは <Link>（= ただの <a>）で足りる。行き先が押す前から決まっているので、
 * クライアントコンポーネントにする必要がない。
 */
function Pagination({
  state,
  lastPage,
  total,
  firstIndex,
  lastIndex,
}: {
  state: ExpenseQueryState;
  lastPage: number;
  total: number;
  firstIndex: number;
  lastIndex: number;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p className="text-xs text-gray-500 tabular-nums">
        {total} 件中 {firstIndex}〜{lastIndex} 件
      </p>

      <div className="flex items-center gap-1">
        <PageLink
          href={buildHref(state, { page: state.page - 1 })}
          disabled={state.page <= 1}
        >
          ◂ 前へ
        </PageLink>
        <span className="px-2 text-xs tabular-nums text-gray-600">
          {state.page} / {lastPage}
        </span>
        <PageLink
          href={buildHref(state, { page: state.page + 1 })}
          disabled={state.page >= lastPage}
        >
          次へ ▸
        </PageLink>
      </div>
    </div>
  );
}

/** 端まで来たら <a> ではなく <span> にする（押せないリンクを作らない）。 */
function PageLink({
  href,
  disabled,
  children,
}: {
  href: string;
  disabled: boolean;
  children: string;
}) {
  const base = "rounded-md border px-3 py-1.5 text-xs";
  if (disabled) {
    return (
      <span className={`${base} border-gray-100 text-gray-300`}>{children}</span>
    );
  }
  return (
    <Link
      href={href}
      scroll={false}
      className={`${base} border-gray-200 text-gray-700 hover:bg-gray-50`}
    >
      {children}
    </Link>
  );
}

/** 0件のときの表示。理由（絞り込みすぎ / ページの行き過ぎ）で文言を変える。 */
function EmptyMessage({
  state,
  lastPage,
}: {
  state: ExpenseQueryState;
  lastPage: number;
}) {
  // 絞り込みを変えたあとに page だけ残っている、というのは buildHref で
  // 起きないようにしてあるが、URL を直接いじられた場合はここに来る。
  if (state.page > lastPage) {
    return (
      <p className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
        このページには支出がありません。
        <Link
          href={buildHref(state, { page: 1 })}
          className="ml-2 text-blue-600 hover:underline"
        >
          1ページ目へ
        </Link>
      </p>
    );
  }

  return (
    <p className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
      条件に合う支出はありません
    </p>
  );
}
