"use client";

/**
 * ログインフォーム。
 *
 * ★ クライアントコンポーネント ★
 * 送信中の状態（useActionState の pending）を使うため。
 * 入力値そのものは state に持たず、FormData から取る。
 */
import { useActionState } from "react";

import { login, type LoginState } from "./actions";

export function LoginForm() {
  const [state, formAction, pending] = useActionState<LoginState, FormData>(
    login,
    {},
  );

  return (
    <form action={formAction} className="space-y-4">
      <div>
        <label
          htmlFor="username"
          className="mb-1 block text-sm font-semibold text-gray-900"
        >
          ユーザー名
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          autoFocus
          required
          placeholder="alice / hitsuji"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-base
                     focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="mb-1 block text-sm font-semibold text-gray-900"
        >
          パスワード
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-base
                     focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
        />
      </div>

      {state.error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {state.error}
        </p>
      )}

      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-base font-semibold
                   text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {pending ? "確認中..." : "ログイン"}
      </button>

      <p className="text-center text-xs text-gray-500">
        30日間使わなかった場合のみ、再度ログインが必要です
      </p>
    </form>
  );
}
