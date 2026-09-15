# Vercel + Neon デプロイ手順

このアプリは1つのリポジトリから、Vercel上の2プロジェクトとNeonのPostgreSQLへ配置する。

```text
Browser -> household-web (Next.js) -> household-api (FastAPI) -> Neon PostgreSQL
```

ブラウザはNext.jsだけへ接続し、FastAPIのURLはサーバー側の環境変数に置く。

## 1. Neon

1. 東京リージョンにPostgreSQLプロジェクトを作る。東京が選べない場合はシンガポールを使い、Vercelのリージョンも `sin1` へ揃える。
2. pooled connection stringを取得する。
3. URLのスキームを `postgresql+psycopg://` にする。
4. ローカルからAlembicを実行してから既存データを移行する。

Neon接続情報や家計データはGitへコミットしない。

## 2. FastAPIプロジェクト

Vercelプロジェクト名は `household-api`、Root Directoryは `backend` とする。

環境変数:

| 名前 | 値 |
| --- | --- |
| `DATABASE_URL` | Neonのpooled connection string（`postgresql+psycopg://...`） |
| `JWT_SECRET` | 32文字以上のランダム値 |
| `JWT_EXPIRE_DAYS` | `30` |
| `COOKIE_SECURE` | `true` |
| `LOG_LEVEL` | `INFO` |

`backend/index.py` がVercel用エントリポイント。`backend/vercel.json` は東京リージョンと実行時間を設定する。

## 3. Next.jsプロジェクト

Vercelプロジェクト名は `household-web`、Root Directoryは `frontend` とする。

環境変数:

| 名前 | 値 |
| --- | --- |
| `API_BASE_URL` | `https://household-api-....vercel.app`（末尾 `/` なし） |

## 4. リリース確認

1. APIの `/healthz` が `{"status":"ok"}` を返す。
2. Webの `/login` が表示される。
3. ありす／ひつじの両方でログインできる。
4. ホームの集計額と支出件数がローカル環境と一致する。
5. 支出の追加・カテゴリ名変更・PayPay CSV取込を各1回確認する。
6. 確認用に作った支出を削除し、件数と金額が元に戻ることを確認する。

## 5. 更新

GitHub Organization所有のprivate repositoryはVercel HobbyのGit連携対象外なので、当面は各ディレクトリからVercel CLIで手動デプロイする。コードを個人所有のprivate repositoryへ移すかVercel Proへ変更すれば、push時の自動デプロイへ切り替えられる。
