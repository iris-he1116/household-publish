/**
 * カテゴリの追加を行う Server Action。
 *
 * ★ サーバーでだけ動く（'use server'）★
 *
 * 支出側（features/expenses/actions.ts）と同じ流儀で書いている。
 * 422 の日本語化と 400/500 の文言づくりは lib/apiErrors.ts に共通化してあるので、
 * ここに置くのは「カテゴリのどの欄に何と出すか」だけ。
 */
"use server";

import { refresh } from "next/cache";

import { ApiError, apiGet, apiPost, type Category } from "@/lib/api";
import {
  MESSAGE_BY_TYPE,
  toFieldErrors,
  toGeneralMessage,
} from "@/lib/apiErrors";

// ============================================================
// 型
// ============================================================

const FIELDS = ["name"] as const;

type CategoryField = (typeof FIELDS)[number];

/**
 * `createCategory` の戻り値。
 *
 * 支出フォームのような入力欄が1つしかないので、
 * ExpenseFormState のような fieldErrors は持たず message ひとつにまとめている。
 */
// 注: 'use server' ファイルから export できるのは async 関数だけ。
//     型は消えるので export してよいが、初期値は呼び出し側に置く。
export type NewCategoryState = {
  ok: boolean;
  /** 追加できたカテゴリの id。呼び出し側でそのまま選択状態にする。 */
  categoryId: number | null;
  /** 失敗理由。入力欄の下に出す。 */
  message: string | null;
};

// ============================================================
// 422 を日本語にする
// ============================================================

const MESSAGE_BY_FIELD_AND_TYPE: Record<string, string> = {
  "name:missing": "カテゴリ名を入力してください",
  "name:string_too_short": "カテゴリ名を入力してください",
  "name:string_too_long": "カテゴリ名は50文字以内で入力してください",
};

function isCategoryField(value: unknown): value is CategoryField {
  return (
    typeof value === "string" && (FIELDS as readonly string[]).includes(value)
  );
}

function messageFor(field: CategoryField, type: string): string {
  return (
    MESSAGE_BY_FIELD_AND_TYPE[`${field}:${type}`] ??
    MESSAGE_BY_TYPE[type] ??
    "カテゴリ名が正しくありません"
  );
}

// ============================================================
// Server Action
// ============================================================

const failure = (message: string): NewCategoryState => ({
  ok: false,
  categoryId: null,
  message,
});

/**
 * カテゴリを1件追加する（入力フォームの「+ 新規」）。
 *
 * 入力欄が1つだけなので FormData ではなく文字列をそのまま受け取る。
 * （`<form>` は入れ子にできず、支出フォームの中に置けないという事情もある。
 *   詳しくは NewCategoryButton.tsx のコメント）
 */
export async function createCategory(
  rawName: string,
): Promise<NewCategoryState> {
  const name = rawName.trim();
  if (name === "") return failure("カテゴリ名を入力してください");

  // 名前は DB で unique。重複したまま POST すると 500 になってしまうので、
  // 先に既存の一覧と突き合わせて分かりやすいメッセージを返す。
  // （アーカイブ済みのカテゴリはこの一覧に出てこないので、
  //   そちらと重なった場合は下の 500 の文言に落ちる）
  const existing = await apiGet<Category[]>("/api/categories/").catch(
    () => [] as Category[],
  );
  if (existing.some((c) => c.name === name)) {
    return failure("同じ名前のカテゴリがすでにあります");
  }

  let created: Category;
  try {
    created = await apiPost<Category>("/api/categories/", {
      name,
      // 既存の最大 +1。指定しないと 0 になり、一覧の先頭に割り込んでしまう。
      display_order:
        existing.reduce((max, c) => Math.max(max, c.display_order), 0) + 1,
    });
  } catch (error) {
    // 422: 名前の長さ違反など
    if (error instanceof ApiError && error.status === 422) {
      const fieldErrors = toFieldErrors(
        error.detail,
        isCategoryField,
        messageFor,
      );
      return failure(fieldErrors.name ?? "入力内容を確認してください。");
    }
    return failure(toGeneralMessage(error, "追加"));
  }

  // 一覧・入力フォームのカテゴリ選択肢をサーバー側で作り直させる。
  refresh();

  return { ok: true, categoryId: created.id, message: null };
}
