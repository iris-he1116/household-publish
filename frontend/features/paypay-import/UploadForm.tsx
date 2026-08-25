/**
 * PayPay の履歴 CSV をアップロードするフォーム。
 *
 * ★ クライアントコンポーネント ★
 *
 * ファイル選択（<input type="file">）はブラウザの機能なので 'use client' が要る。
 * 送信中の表示（pending）も持つ。
 */
"use client";

import { useActionState, useRef } from "react";

import { importCsv, type ImportState } from "./actions";

const INITIAL_STATE: ImportState = { ok: null, message: null, result: null };

export function UploadForm() {
  const [state, formAction, pending] = useActionState(importCsv, INITIAL_STATE);
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <section className="space-y-3">
      <form
        action={formAction}
        className="rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-6"
      >
        <p className="text-center text-sm text-gray-600">
          PayPay の履歴 CSV をアップロード
        </p>
        <p className="mt-1 text-center text-xs text-gray-400">
          列は 取引日 / 金額 / 店舗名 / 取引ID
        </p>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          <input
            ref={fileRef}
            type="file"
            name="file"
            accept=".csv,text/csv"
            className="text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-gray-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-gray-700"
          />
          <button
            type="submit"
            disabled={pending}
            className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {pending ? "取り込み中…" : "取り込む"}
          </button>
        </div>
      </form>

      {state.message && (
        <div
          className={`rounded-lg border p-3 text-sm ${
            state.ok
              ? "border-cyan-300 bg-cyan-50 text-cyan-900"
              : "border-red-300 bg-red-50 text-red-800"
          }`}
        >
          <p>{state.message}</p>
          {state.result && (
            <p className="mt-1 text-xs">
              全 {state.result.total_rows} 行 ・ 新規 {state.result.new_rows} 行
              ・ 重複 {state.result.duplicate_rows} 行（自動で除外）
            </p>
          )}
        </div>
      )}

      <p className="text-xs text-gray-500">
        同じ取引を二重に登録しないよう、取引ID で重複を判定しています。
        取り込めるのは自分の履歴だけで、相手の分は表示されません。
      </p>
    </section>
  );
}
