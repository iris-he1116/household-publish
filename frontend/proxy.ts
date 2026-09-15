/**
 * 未ログインのアクセスを /login に飛ばす。
 *
 * ## ここでやること／やらないこと
 *
 * やること   : Cookie が「有るか無いか」だけ見て振り分ける
 * やらないこと: JWT の検証。署名鍵はバックエンドにしか無いし、
 *               proxy は全リクエストで動くので重い処理を置かない
 *
 * Cookie を偽造して通り抜けても、API 側が 401 を返すので実害はない。
 * これは「入口の案内」であって「鍵」ではない。鍵は FastAPI 側にある。
 */
import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "household_session";

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);

  // ログイン済みの人がログイン画面を開いたらホームに戻す
  if (pathname === "/login") {
    if (hasSession) return NextResponse.redirect(new URL("/", request.url));
    return NextResponse.next();
  }

  if (!hasSession) {
    const url = new URL("/login", request.url);
    // ログイン後に元のページへ戻すため、行き先を覚えておく
    if (pathname !== "/") url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // 静的ファイルと Next.js の内部パスは対象外にする
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|ico)$).*)"],
};
