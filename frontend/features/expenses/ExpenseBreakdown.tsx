import type { Category, SettlementSummary } from "@/lib/api";

import { METHOD_LABEL } from "./constants";

const yen = (n: number) => `¥ ${n.toLocaleString("ja-JP")}`;

const FALLBACK_COLORS = [
  "#2563eb",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#ec4899",
  "#64748b",
];

function categoryColor(
  categoryId: number,
  categories: Category[],
): string {
  return (
    categories.find((category) => category.id === categoryId)?.color ??
    FALLBACK_COLORS[(categoryId - 1) % FALLBACK_COLORS.length]
  );
}

export function ExpenseBreakdown({
  summary,
  categories,
}: {
  summary: SettlementSummary;
  categories: Category[];
}) {
  const slices = summary.categories.map((category) => ({
    ...category,
    color: categoryColor(category.category_id, categories),
    percentage:
      summary.total_amount > 0
        ? (category.amount / summary.total_amount) * 100
        : 0,
  }));

  const gradient = slices
    .reduce<{ offset: number; segments: string[] }>(
      (state, slice) => {
        const end = state.offset + slice.percentage;
        return {
          offset: end,
          segments: [
            ...state.segments,
            `${slice.color} ${state.offset}% ${end}%`,
          ],
        };
      },
      { offset: 0, segments: [] },
    )
    .segments.join(", ");

  const monthLabel = `${Number(summary.year_month.slice(5))}月`;

  return (
    <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-5 py-4">
        <h2 className="text-sm font-semibold text-gray-900">
          {monthLabel}の支出内訳
        </h2>
        <p className="mt-1 text-xs text-gray-500">
          カテゴリと支払い手段ごとの合計です
        </p>
      </div>

      <div className="grid divide-y divide-gray-100 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)] lg:divide-x lg:divide-y-0">
        <section className="p-5" aria-labelledby="category-breakdown-title">
          <h3
            id="category-breakdown-title"
            className="text-sm font-semibold text-gray-900"
          >
            カテゴリ別
          </h3>

          {slices.length === 0 ? (
            <p className="mt-4 text-sm text-gray-400">この月の支出はありません</p>
          ) : (
            <div className="mt-4 grid items-center gap-6 sm:grid-cols-[12rem_minmax(0,1fr)]">
              <div className="mx-auto">
                <div
                  role="img"
                  aria-label={`${monthLabel}のカテゴリ別支出。合計${yen(summary.total_amount)}`}
                  className="relative aspect-square w-44 rounded-full sm:w-48"
                  style={{ background: `conic-gradient(${gradient})` }}
                >
                  <div className="absolute inset-[27%] flex flex-col items-center justify-center rounded-full bg-white text-center shadow-[inset_0_0_0_1px_#f3f4f6]">
                    <span className="text-[11px] text-gray-500">合計</span>
                    <strong className="mt-0.5 text-sm tabular-nums text-gray-900 sm:text-base">
                      {yen(summary.total_amount)}
                    </strong>
                  </div>
                </div>
              </div>

              <ul className="grid gap-x-5 gap-y-3 sm:grid-cols-2">
                {slices.map((slice) => (
                  <li key={slice.category_id} className="min-w-0 text-sm">
                    <div className="flex items-center gap-2">
                      <span
                        aria-hidden="true"
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: slice.color }}
                      />
                      <span className="min-w-0 flex-1 truncate text-gray-700">
                        {slice.category_name}
                      </span>
                      <span className="text-xs tabular-nums text-gray-400">
                        {Math.round(slice.percentage)}%
                      </span>
                    </div>
                    <div className="mt-1 flex items-baseline justify-between pl-[18px]">
                      <span className="font-medium tabular-nums text-gray-900">
                        {yen(slice.amount)}
                      </span>
                      <span className="text-xs text-gray-400">{slice.count}件</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="p-5" aria-labelledby="payment-breakdown-title">
          <h3
            id="payment-breakdown-title"
            className="text-sm font-semibold text-gray-900"
          >
            支払い手段
          </h3>
          {summary.payment_methods.length === 0 ? (
            <p className="mt-4 text-sm text-gray-400">—</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {summary.payment_methods.map((method) => (
                <li
                  key={method.payment_method}
                  className="flex items-baseline justify-between gap-4 text-sm"
                >
                  <span className="text-gray-700">
                    {METHOD_LABEL[method.payment_method] ?? method.payment_method}
                  </span>
                  <span className="font-medium tabular-nums text-gray-900">
                    {yen(method.amount)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </section>
  );
}
