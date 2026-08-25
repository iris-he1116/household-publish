/**
 * 清算の状態を進めるボタン（「締める」「確認する」）。
 *
 * ★ クライアントコンポーネント ★
 *
 * onClick で反応し、送信中の状態（pending）を持つ必要があるので 'use client' が要る。
 * ただし付けるのはこのボタンだけ。集計の表示部分（SettlementDetail）は
 * サーバーコンポーネントのまま保つ。
 */
"use client";

import { useActionState } from "react";

import type { SettlementActionState } from "./actions";

const INITIAL_STATE: SettlementActionState = { ok: null, message: null };

type Props = {
  /** 対象の年月（"2026-08"）。 */
  yearMonth: string;
  /** 押したときに呼ぶ Server Action。 */
  action: (
    prevState: SettlementActionState,
    formData: FormData,
  ) => Promise<SettlementActionState>;
  /** ボタンの文言。 */
  label: string;
  /** 送信中の文言。 */
  pendingLabel: string;
  /** 押せない理由。指定すると無効化してこの文言を出す。 */
  disabledReason?: string;
  /** 見た目。primary = 主要な操作、secondary = 補助的な操作。 */
  variant?: "primary" | "secondary";
};

export function SettlementActionButton({
  yearMonth,
  action,
  label,
  pendingLabel,
  disabledReason,
  variant = "primary",
}: Props) {
  const [state, formAction, pending] = useActionState(action, INITIAL_STATE);

  const base =
    "rounded-md px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50";
  const style =
    variant === "primary"
      ? "bg-gray-900 text-white hover:bg-gray-700"
      : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50";

  return (
    <div className="space-y-2">
      <form action={formAction}>
        {/* 対象の年月は入力欄ではないので hidden で送る */}
        <input type="hidden" name="year_month" value={yearMonth} />
        <button
          type="submit"
          disabled={pending || Boolean(disabledReason)}
          className={`${base} ${style}`}
        >
          {pending ? pendingLabel : label}
        </button>
      </form>

      {disabledReason && (
        <p className="text-xs text-gray-500">{disabledReason}</p>
      )}

      {state.message && (
        <p
          className={`text-xs ${
            state.ok ? "text-green-700" : "text-red-600"
          }`}
        >
          {state.message}
        </p>
      )}
    </div>
  );
}
