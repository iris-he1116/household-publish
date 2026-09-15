"use server";

/**
 * 認証の Server Actions。
 *
 * ログインは「FastAPI が返した Set-Cookie を、Next.js 側の Cookie に写す」だけ。
 * ブラウザは HttpOnly Cookie を受け取るので、JavaScript から JWT は読めない。
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ApiError, apiPostRaw, SESSION_COOKIE, UnauthorizedError } from "@/lib/api";

export type LoginState = { error?: string };

/**
 * FastAPI の Set-Cookie ヘッダから household_session の値と属性を取り出し、
 * Next.js 側の Cookie に設定する。
 *
 * バックエンドと同じ属性（HttpOnly / Secure / SameSite / Max-Age）を維持したいので、
 * 値だけでなく Max-Age も読む。
 */
async function applySetCookie(raw: string | null): Promise<void> {
  if (!raw) return;
  const m = raw.match(new RegExp(`${SESSION_COOKIE}=([^;]+)`));
  if (!m) return;
  const maxAge = Number(raw.match(/Max-Age=(\d+)/i)?.[1] ?? 0) || undefined;

  const jar = await cookies();
  jar.set(SESSION_COOKIE, m[1], {
    httpOnly: true,
    // 属性はバックエンドの判断（COOKIE_SECURE）に合わせる
    secure: /;\s*Secure/i.test(raw),
    sameSite: "lax",
    maxAge,
    path: "/",
  });
}

export async function login(
  _prev: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!username) return { error: "ユーザー名を入力してください" };
  if (!password) return { error: "パスワードを入力してください" };

  try {
    const res = await apiPostRaw<{ id: number; name: string }>(
      "/api/auth/login",
      { username, password },
    );
    await applySetCookie(res.setCookie);
  } catch (e) {
    if (e instanceof UnauthorizedError) {
      // どちらが違うかは言わない（ユーザー名の存在を推測させない）
      return { error: "ユーザー名またはパスワードが違います" };
    }
    if (e instanceof ApiError && e.status === 429) {
      // 「あと何分待てばいいか」はサーバーが文章で返している
      const msg = typeof e.detail === "string" ? e.detail : null;
      return { error: msg ?? "試行回数が多すぎます。しばらく待ってからお試しください" };
    }
    return { error: "ログインできませんでした。時間をおいて試してください" };
  }
  // try の中で redirect すると catch に拾われるのでここで呼ぶ
  redirect("/");
}

export async function logout(): Promise<void> {
  try {
    await apiPostRaw("/api/auth/logout", {});
  } catch {
    // バックエンドが落ちていてもローカルの Cookie は消す
  }
  const jar = await cookies();
  jar.delete(SESSION_COOKIE);
  redirect("/login");
}
