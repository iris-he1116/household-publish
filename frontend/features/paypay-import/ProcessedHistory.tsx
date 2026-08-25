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

  return (
    <section className="rounded-lg border border-gray-200 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-900">判定済みの履歴</h2>
        <p className="text-xs text-gray-500">
          取引ID で重複を判定しているので、同じ取引は二重に登録されません
        </p>
      </div>

      <ul className="mt-3 divide-y divide-gray-100">
        {rows.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
            <span className="tabular-nums text-gray-500">{r.occurred_on}</span>
            <span className="text-gray-900">
              {r.merchant_name ?? "（店舗名なし）"}
            </span>
            <span className="tabular-nums text-gray-900">{yen(r.amount)}</span>
            <Badge status={r.status} />
            <span className="text-xs text-gray-500">
              {r.status === "adopted"
                ? `→ 支出 #${r.linked_expense_id} として登録済み`
                : "→ 集計に含めない（記録だけ残す）"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
