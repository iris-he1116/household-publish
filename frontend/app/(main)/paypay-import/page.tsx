/**
 * PayPay 取り込み画面（モック③ に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * DESIGN.md §1.4 / §2.6:
 *   CSV アップロード → ステージングに取り込み（重複は自動除外）
 *   → 1行ずつ「共有 / 個人」を判定 → 共有分だけ支出に昇格
 *
 * PayPay の履歴は各自が自分の分をアップロードする運用なので、
 * この画面に出るのは自分が取り込んだ行だけ（サーバーがログイン中のユーザーで絞る）。
 */
import { Suspense } from "react";

import { ProcessedHistory } from "@/features/paypay-import/ProcessedHistory";
import { StagingList } from "@/features/paypay-import/StagingList";
import { UploadForm } from "@/features/paypay-import/UploadForm";

function Skeleton({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-gray-200 p-8 text-center text-sm text-gray-400">
      {label}を読み込んでいます…
    </div>
  );
}

export default function PayPayImportPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">PayPay 取り込み</h1>
          <p className="mt-1 text-sm text-gray-500">
            自分の PayPay 履歴 CSV をアップロードして、2人で使った分だけを支出に登録します
          </p>
        </div>

        {/* 唯一の対話部分の1つ。ファイル選択はブラウザの機能なのでクライアント。 */}
        <UploadForm />

        <Suspense fallback={<Skeleton label="未判定の行" />}>
          <StagingList />
        </Suspense>

        <Suspense fallback={<Skeleton label="判定済みの履歴" />}>
          <ProcessedHistory />
        </Suspense>
      </div>
    </main>
  );
}
