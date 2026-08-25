/**
 * 未判定のステージング行の一覧（モック③ に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * 一覧を取ってくるのも、枠を組み立てるのもサーバー。
 * ブラウザに JavaScript が要るのは、1行ごとの判定カード（StagingCard）だけ。
 */
import { getCategories, getStagingRows } from "@/lib/api";

import { StagingCard } from "./StagingCard";

export async function StagingList() {
  // 2つの API を並行して呼ぶ（順に await すると直列になる）
  const [rows, categories] = await Promise.all([
    getStagingRows("pending"),
    getCategories(),
  ]);

  const total = rows.reduce((sum, r) => sum + r.amount, 0);

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-bold text-gray-900">
          未判定の行（{rows.length} 件）
        </h2>
        {rows.length > 0 && (
          <p className="text-xs text-gray-500">
            合計 ¥ {total.toLocaleString("ja-JP")}
          </p>
        )}
      </div>

      {rows.length === 0 ? (
        <p className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
          未判定の行はありません。CSV を取り込むとここに並びます。
        </p>
      ) : (
        <>
          <p className="text-xs text-gray-500">
            2人で使った分は「共有にする」、自分だけの分は「個人にする」を選びます。
            共有にすると支出として登録され、月次清算の対象になります。
          </p>
          <ul className="space-y-3">
            {rows.map((row) => (
              <StagingCard key={row.id} row={row} categories={categories} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
