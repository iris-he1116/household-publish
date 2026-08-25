/**
 * 入力フォームのカテゴリ欄の横に出す「+ 新規」（モック① に対応）。
 *
 * ★ 小さなクライアントコンポーネント ★
 *
 * 「入力欄を開いているか」は一時的な見た目の状態なので useState で持つ。
 * 追加そのものは Server Action（createCategory）に任せ、
 * 成功したら refresh() でカテゴリの選択肢がサーバー側から作り直される。
 *
 * ## なぜ <form> を使っていないか
 *
 * この部品は支出の入力フォーム（QuickExpenseForm の <form>）の中に置かれる。
 * HTML では <form> を入れ子にできないので、素の <input> + <button> にして、
 * Server Action は onClick から直接呼んでいる。
 * その代わり Enter キーでも追加できるように onKeyDown を拾っている。
 */
"use client";

import { useRef, useState, useTransition } from "react";

import { createCategory } from "./actions";

type Props = {
  /**
   * 追加できたときに呼ばれる。
   * 呼び出し側（QuickExpenseForm）が、そのカテゴリを選択状態にする。
   */
  onCreated: (categoryId: number) => void;
};

export function NewCategoryButton({ onCreated }: Props) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);

  const close = () => {
    setOpen(false);
    setError(null);
  };

  const submit = () => {
    const name = inputRef.current?.value ?? "";
    startTransition(async () => {
      const result = await createCategory(name);
      if (result.ok && result.categoryId !== null) {
        onCreated(result.categoryId);
        close();
      } else {
        setError(result.message);
      }
    });
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="shrink-0 text-xs text-blue-600 hover:underline"
      >
        + 新規
      </button>
    );
  }

  // basis-full: 呼び出し側の flex-wrap な行の中で、1行まるごと使う
  return (
    <div className="basis-full">
      <div className="flex gap-1">
        <input
          ref={inputRef}
          type="text"
          maxLength={50}
          autoFocus
          placeholder="カテゴリ名"
          aria-label="新しいカテゴリ名"
          aria-invalid={Boolean(error)}
          onKeyDown={(e) => {
            // Enter で追加、Esc で取消。
            // <form> の中ではないので、この2つは自前で拾う必要がある。
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
            if (e.key === "Escape") close();
          }}
          className={[
            "w-full rounded-md border px-2 py-1 text-sm text-gray-900",
            "focus:outline-none focus:ring-2 focus:ring-blue-400",
            error ? "border-red-400" : "border-gray-200",
          ].join(" ")}
        />
        <button
          type="button"
          onClick={submit}
          disabled={pending}
          className="shrink-0 rounded-md bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {pending ? "…" : "追加"}
        </button>
        <button
          type="button"
          onClick={close}
          disabled={pending}
          className="shrink-0 rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed"
        >
          取消
        </button>
      </div>
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </div>
  );
}
