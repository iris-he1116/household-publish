/** クイック入力から開く、カテゴリ名の編集ダイアログ。 */
"use client";

import { useState, useTransition } from "react";

import { updateCategoryName } from "./actions";
import type { Category } from "@/lib/api";

export function CategoryManagerButton({
  categories,
}: {
  categories: Category[];
}) {
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draftName, setDraftName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const startEditing = (category: Category) => {
    setEditingId(category.id);
    setDraftName(category.name);
    setMessage(null);
    setError(null);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setDraftName("");
    setError(null);
  };

  const close = () => {
    cancelEditing();
    setMessage(null);
    setOpen(false);
  };

  const save = (categoryId: number) => {
    startTransition(async () => {
      const result = await updateCategoryName(categoryId, draftName);
      if (result.ok) {
        setEditingId(null);
        setDraftName("");
        setError(null);
        setMessage(result.message);
      } else {
        setError(result.message);
      }
    });
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="shrink-0 text-xs text-gray-500 hover:text-blue-700 hover:underline"
      >
        編集
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/40 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="category-manager-title"
            className="w-full max-w-md rounded-xl bg-white shadow-xl"
          >
            <div className="flex items-start justify-between border-b border-gray-100 px-5 py-4">
              <div>
                <h2
                  id="category-manager-title"
                  className="text-lg font-bold text-gray-900"
                >
                  カテゴリを編集
                </h2>
                <p className="mt-1 text-xs text-gray-500">
                  名前を変更すると、過去の支出にも反映されます
                </p>
              </div>
              <button
                type="button"
                onClick={close}
                disabled={pending}
                aria-label="閉じる"
                className="rounded-md px-2 py-1 text-xl leading-none text-gray-400 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-not-allowed"
              >
                ×
              </button>
            </div>

            <div className="max-h-[60vh] overflow-y-auto p-3">
              {message && (
                <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  {message}
                </p>
              )}
              <ul className="divide-y divide-gray-100">
                {categories.map((category) => (
                  <li key={category.id} className="px-2 py-3">
                    {editingId === category.id ? (
                      <div>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={draftName}
                            maxLength={50}
                            autoFocus
                            aria-label={`${category.name}の新しい名前`}
                            aria-invalid={Boolean(error)}
                            onChange={(event) => setDraftName(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                save(category.id);
                              }
                              if (event.key === "Escape") cancelEditing();
                            }}
                            className={`min-w-0 flex-1 rounded-md border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-400 ${
                              error ? "border-red-400" : "border-gray-200"
                            }`}
                          />
                          <button
                            type="button"
                            onClick={() => save(category.id)}
                            disabled={pending}
                            className="rounded-md bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                          >
                            {pending ? "保存中…" : "保存"}
                          </button>
                          <button
                            type="button"
                            onClick={cancelEditing}
                            disabled={pending}
                            className="rounded-md px-2 py-2 text-xs text-gray-500 hover:bg-gray-100 disabled:cursor-not-allowed"
                          >
                            取消
                          </button>
                        </div>
                        {error && (
                          <p className="mt-1 text-xs text-red-600">{error}</p>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-medium text-gray-900">
                          {category.name}
                        </span>
                        <button
                          type="button"
                          onClick={() => startEditing(category)}
                          className="rounded-md px-3 py-1.5 text-xs text-blue-700 hover:bg-blue-50"
                        >
                          名前を変更
                        </button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
