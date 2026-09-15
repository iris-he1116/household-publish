/**
 * 判定済みの履歴（モック③ の下部に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * 「この取引はもう処理した」を確認するための一覧。
 * 同じ取引を二重に登録していないことが目で見える。
 */
import { getStagingRows, type StagingRow } from "@/lib/api";

const yen = (n: number) => `¥ ${n.toLocaleString("ja-JP")}`;

type MonthGroup = {
  yearMonth: string;
  rows: StagingRow[];
  totalAmount: number;
  sharedCount: number;
  personalCount: number;
};

function groupByMonth(rows: StagingRow[]): MonthGroup[] {
  const groups = new Map<string, MonthGroup>();

  for (const row of rows) {
    const yearMonth = row.occurred_on.slice(0, 7);
    const group = groups.get(yearMonth) ?? {
      yearMonth,
      rows: [],
      totalAmount: 0,
      sharedCount: 0,
      personalCount: 0,
    };

    group.rows.push(row);
    group.totalAmount += row.amount;
    if (row.status === "adopted") group.sharedCount += 1;
    else group.personalCount += 1;
    groups.set(yearMonth, group);
  }

  return [...groups.values()];
}

function monthLabel(yearMonth: string): string {
  const [year, month] = yearMonth.split("-");
  return `${year}年${Number(month)}月`;
}

function Badge({ status }: { status: StagingRow["status"] }) {
  if (status === "adopted") {
    return (
      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
        共有
      </span>
    );
  }
  return (
    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
      個人
    </span>
  );
}

export async function ProcessedHistory() {
  // 採用・除外の2種類を並行して取る
  const [adopted, excluded] = await Promise.all([
    getStagingRows("adopted"),
    getStagingRows("excluded"),
  ]);

  const rows = [...adopted, ...excluded].sort((a, b) =>
    b.occurred_on.localeCompare(a.occurred_on),
  );

  if (rows.length === 0) {
    return null;
  }

  const monthGroups = groupByMonth(rows);

  return (
    <section className="rounded-lg border border-gray-200 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-900">判定済みの履歴</h2>
        <p className="text-xs text-gray-500">
          取引情報で重複を判定しているので、同じ明細は二重に登録されません
        </p>
      </div>

      <div className="mt-3 space-y-2">
        {monthGroups.map((group, index) => (
          <details
            key={group.yearMonth}
            open={index === 0}
            className="group overflow-hidden rounded-lg border border-gray-200"
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 bg-gray-50 px-3 py-3 [&::-webkit-details-marker]:hidden">
              <div className="flex min-w-0 items-center gap-2">
                <span
                  aria-hidden="true"
                  className="shrink-0 text-gray-400 transition-transform group-open:rotate-90"
                >
                  ▸
                </span>
                <span className="font-semibold text-gray-900">
                  {monthLabel(group.yearMonth)}
                </span>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-medium tabular-nums text-gray-900">
                  {group.rows.length}件・{yen(group.totalAmount)}
                </p>
                <p className="text-[11px] text-gray-500">
                  共有 {group.sharedCount}件 / 個人 {group.personalCount}件
                </p>
              </div>
            </summary>

            <ul className="divide-y divide-gray-100 bg-white">
              {group.rows.map((r) => (
                <li
                  key={r.id}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5 text-sm"
                >
                  <span className="tabular-nums text-gray-500">
                    {r.occurred_on.slice(5).replace("-", "/")}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-gray-900">
                    {r.merchant_name ?? "（店舗名なし）"}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
                    {r.source_label ?? "PayPay"}
                  </span>
                  <span className="tabular-nums text-gray-900">
                    {yen(r.amount)}
                  </span>
                  <Badge status={r.status} />
                  <span className="basis-full pl-12 text-xs text-gray-500 sm:basis-auto sm:pl-0">
                    {r.status === "adopted"
                      ? `支出 #${r.linked_expense_id} として登録済み`
                      : "集計に含めない（記録だけ残す）"}
                  </span>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
    </section>
  );
}
