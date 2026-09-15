/**
 * 3画面を行き来するナビゲーション（モックのトップタブ／ボトムタブに対応）。
 *
 * ★ クライアントコンポーネント ★
 *
 * 「今どの画面を見ているか」で見た目を変えるために `usePathname` が要る。
 * これはブラウザ側でしか分からない情報なので 'use client' が必要。
 *
 * ただしクライアントにするのはこのナビだけ。
 * layout.tsx は依然サーバーコンポーネントで、
 * 各ページの中身（集計・一覧など）もサーバーのまま。
 *
 * 未判定バッジの件数は props で受け取る（このコンポーネントは API を叩かない）。
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { logout } from "@/features/auth/actions";

type Item = {
  href: string;
  label: string;
  icon: string;
  /** この接頭辞に一致したら現在地とみなす。 */
  match: (pathname: string) => boolean;
};

const ITEMS: Item[] = [
  {
    href: "/",
    label: "ホーム",
    icon: "🏠",
    match: (p) => p === "/",
  },
  {
    href: "/settlement",
    label: "清算",
    icon: "📊",
    match: (p) => p.startsWith("/settlement"),
  },
  {
    href: "/paypay-import",
    label: "PayPay",
    icon: "📥",
    match: (p) => p.startsWith("/paypay-import"),
  },
];

export function AppNav({
  pendingCount = 0,
  userName,
}: {
  pendingCount?: number;
  /** ログイン中のユーザー名。取得できないときは省略（ログアウトも出さない） */
  userName?: string;
}) {
  const pathname = usePathname();

  return (
    <>
      {/* PC: 上部のタブ */}
      <header className="sticky top-0 z-10 hidden border-b border-gray-800 bg-gray-900 sm:block">
        <div className="mx-auto flex max-w-5xl items-center gap-1 px-6">
          <span className="mr-4 py-3 text-sm font-semibold text-white">
            家計清算
          </span>

          {ITEMS.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative px-4 py-3 text-sm transition ${
                  active
                    ? "bg-gray-800 font-semibold text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {item.label}
                {item.href === "/paypay-import" && pendingCount > 0 && (
                  <span className="ml-2 rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                    {pendingCount}
                  </span>
                )}
              </Link>
            );
          })}

          {userName && (
            <div className="ml-auto flex items-center gap-3 py-3">
              <span className="text-xs text-gray-400">{userName}</span>
              <form action={logout}>
                <button
                  type="submit"
                  className="text-xs text-gray-400 hover:text-white"
                >
                  ログアウト
                </button>
              </form>
            </div>
          )}
        </div>
      </header>

      {/* スマホ: 下部のタブ（親指の届く位置） */}
      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-gray-200 bg-white sm:hidden">
        <div className="flex">
          {ITEMS.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className="relative flex flex-1 flex-col items-center gap-0.5 py-2"
              >
                <span className="text-lg leading-none">{item.icon}</span>
                <span
                  className={`text-[10px] ${
                    active ? "font-semibold text-gray-900" : "text-gray-400"
                  }`}
                >
                  {item.label}
                </span>
                {item.href === "/paypay-import" && pendingCount > 0 && (
                  <span className="absolute right-1/2 top-1 translate-x-4 rounded-full bg-red-600 px-1.5 text-[10px] font-semibold text-white">
                    {pendingCount}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
