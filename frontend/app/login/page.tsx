/**
 * ログイン画面（Phase 5）。
 *
 * ★ サーバーコンポーネント ★
 * フォーム部分だけがクライアント（送信中の表示に pending が要るため）。
 *
 * この画面はナビを出さない。未ログインの状態で
 * 「ホーム / 清算 / PayPay」を見せても遷移できないため。
 */
import { LoginForm } from "@/features/auth/LoginForm";

export const metadata = { title: "ログイン｜家計清算" };

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-gray-900">家計清算</h1>
          <p className="mt-1 text-sm text-gray-500">ありす ／ ひつじ の共有支出</p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <LoginForm />
        </div>
      </div>
    </main>
  );
}
