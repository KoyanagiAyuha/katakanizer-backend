# 環境構成ガイド

このプロジェクトは **local / test / prod** の3環境で運用する。
設定の実体は環境変数（`DATABASE_URL` など）で、読み込み元が環境ごとに異なる。

## 環境の一覧

| 環境 | 用途 | DB | 設定の読み込み元 |
|------|------|----|----|
| **local** | ローカル開発 | docker compose の PostgreSQL | リポジトリ直下の `.env` |
| **test** | デプロイ前検証 / ステージング | Neon (test) | Vercel: Preview 環境変数 |
| **prod** | 本番 | Neon (prod) | Vercel: Production 環境変数 |

ポイント:

- 設定は **環境変数**。`config.py` の `Settings` が読む。
- `.env` は **ローカル専用**。`.gitignore` 済みで、Vercel にはデプロイされない。
- `.env.test` / `.env.prod` のようなファイルは**作らない**。test / prod の値は
  Vercel の Environment Variables で管理する（後述）。

## アプリの設定（Vercel）

デプロイされたアプリの環境変数は Vercel ダッシュボードで設定する。
`Project → Settings → Environment Variables` で、環境ごとにスコープを指定できる。

| 変数 | local (`.env`) | test (Preview) | prod (Production) |
|------|------|------|------|
| `DATABASE_URL` | ローカル docker | Neon test（`-pooler` 付き推奨） | Neon prod（`-pooler` 付き推奨） |
| `DEBUG` | `true` | `true` | `false` |
| `CORS_ORIGINS` | `http://localhost:3000` | test 用フロントの URL | 本番フロントの URL |
| `FIREBASE_PROJECT_ID` | Firebase プロジェクト ID | 同左（環境を分けるなら test 用） | 同左 |
| `OPENAI_API_KEY` | OpenAI キー | 同左 | 同左 |
| `FREE_USER_DAILY_LIMIT` | `5` | `5` | 任意 |

> 利用可能な変数の一覧は `.env.example` と `src/config.py` の `Settings` を参照。

## Neon のデータベース構成

test / prod は次のどちらかで分離する（すでに用意済みのものをそのまま使う）。

- **ブランチ戦略**: 1 プロジェクト内で `prod` / `test` ブランチを分ける。
  スキーマ・データのコピーが容易でコスト効率がよい。
- **別プロジェクト戦略**: prod 用 / test 用にプロジェクト自体を分ける。
  完全に独立し、課金・権限を分離できる。

接続文字列の取得手順は [NEON_SETUP.md](NEON_SETUP.md) を参照。

## マイグレーション

スキーマ管理は Alembic。**接続先は実行時に `DATABASE_URL` をインライン指定**して
切り替える（`.env` はローカル用のまま使う）。

```bash
# local（.env を使用）
uv run alembic upgrade head

# test
DATABASE_URL='postgresql://...test...neon.tech/db?sslmode=require' \
  uv run alembic upgrade head

# prod（慎重に）
DATABASE_URL='postgresql://...prod...neon.tech/db?sslmode=require' \
  uv run alembic upgrade head
```

詳細・初回導入手順（`alembic stamp head`）は [README_MIGRATIONS.md](README_MIGRATIONS.md) を参照。

## デプロイ／変更のワークフロー

1. **ローカルで開発**
   ```bash
   docker compose up -d
   uv run uvicorn src.main:app --reload
   ```
2. **モデルを変更したらマイグレーション作成**
   ```bash
   uv run alembic revision --autogenerate -m "変更内容"
   # 生成ファイルを確認し、ローカル DB で uv run alembic upgrade head
   ```
3. **test 環境へ**
   ```bash
   DATABASE_URL='<test の URL>' uv run alembic upgrade head
   # Vercel の Preview デプロイで動作確認
   ```
4. **prod 環境へ**
   ```bash
   DATABASE_URL='<prod の URL>' uv run alembic upgrade head
   vercel deploy --prod
   ```

## セキュリティ

- `.env` は絶対に Git にコミットしない（`.gitignore` 済み）。
- test / prod の秘密情報はファイルに置かず、Vercel の環境変数で管理する。
- `DATABASE_URL` をインライン指定するとシェル履歴に残る。共有端末では注意し、
  必要なら履歴から削除する。
- prod の認証情報は定期的にローテーションする（Neon の Roles からパスワード再発行）。

## デプロイ時チェックリスト

- [ ] ローカルで動作確認
- [ ] マイグレーションファイルを作成・レビュー
- [ ] test 環境にマイグレーション適用 → 動作確認
- [ ] prod 環境にマイグレーション適用
- [ ] prod デプロイ → 動作確認
