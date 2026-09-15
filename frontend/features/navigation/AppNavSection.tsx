/**
 * ナビに未判定バッジの件数を渡すためのラッパ。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * API を叩くのはここまで。AppNav 本体はブラウザで動くので、
 * 必要な数字は props で渡し切る。
 *
 * 取得に失敗してもナビは出したいので、エラーは握って 0 件として扱う
 * （バックエンドが落ちていても画面遷移はできるべき）。
 */
import { getMe, getStagingRows } from "@/lib/api";

import { AppNav } from "./AppNav";

export async function AppNavSection() {
  // 2つとも失敗してよい（バッジと名前が出ないだけ）。
  // 未ログインのときは middleware が /login に飛ばすので、ここには来ない。
  const [pendingCount, userName] = await Promise.all([
    getStagingRows("pending")
      .then((rows) => rows.length)
      .catch(() => 0),
    getMe()
      .then((me) => me.name)
      .catch(() => undefined),
  ]);

  return <AppNav pendingCount={pendingCount} userName={userName} />;
}
