/**
 * 過去の清算履歴（モック② の下部に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 */
import Link from "next/link";

import { getSettlements, type Settlement } from "@/lib/api";

const STATUS_STYLE: Record<
  Settlement["status"],
  { label: string; className: string }
> = {
  in_progress: { label: "進行中", className: "bg-gray-100 text-gray-700" },
  closed: { label: "締め済み", className: "bg-amber-100 text-amber-800" },
  partially_confirmed: {
    label: "片方確認済",
    className: "bg-blue-100 text-blue-800",
  },
  settled: { label: "清算済", className: "bg-green-100 text-green-800" },
};

export async function SettlementHistory({
  currentYearMonth,
}: {
  currentYearMonth: string;
}) {
  const settlements = await getSettlements();

  if (settlements.length === 0) {
    return null;
  }

  return (
    <section className="rounded-lg border border-gray-200 p-4">
      <h2 className="text-sm font-semibold text-gray-900">過去の清算</h2>
      <ul className="mt-3 divide-y divide-gray-100">
        {settlements.map((s) => {
          const style = STATUS_STYLE[s.status];
          const isCurrent = s.year_month === currentYearMonth;
          return (
            <li
              key={s.year_month}
              className="flex items-center gap-3 py-2 text-sm"
            >
              <Link
                href={`/settlement/${s.year_month}`}
                className={`tabular-nums ${
                  isCurrent
                    ? "font-semibold text-gray-900"
                    : "text-blue-600 hover:underline"
                }`}
              >
                {s.year_month}
              </Link>
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${style.className}`}
              >
                {style.label}
              </span>
              {s.has_stale_updates && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                  更新あり
                </span>
              )}
              {isCurrent && (
                <span className="text-xs text-gray-400">表示中</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
