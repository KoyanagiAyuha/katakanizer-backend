# Database Migrations with Alembic

DB スキーマは Alembic で管理する。接続先は `DATABASE_URL` で決まり、
`alembic/env.py` が以下の優先順位で読み込む（OS 環境変数が `.env` より優先）。

- **ローカル**: `.env` の `DATABASE_URL`（docker compose の PostgreSQL）
- **test / prod**: コマンド実行時に `DATABASE_URL=...` をインライン指定（後述）

## セットアップ

依存は `uv` で管理しているため、追加インストールは不要。

```bash
uv sync
```

## マイグレーションの作成

モデル（`src/models/`）を変更したら、ローカル DB に対して自動生成する。

```bash
# モデル変更から自動生成（.env のローカル DB を使用）
uv run alembic revision --autogenerate -m "変更内容の説明"

# 空のマイグレーションを作成
uv run alembic revision -m "変更内容の説明"
```

> 自動生成されたファイルは適用前に必ず内容を確認すること。

## マイグレーションの適用

```bash
# 最新まで適用
uv run alembic upgrade head

# 特定リビジョンまで適用
uv run alembic upgrade <revision>
```

## ロールバック

```bash
# 1つ戻す
uv run alembic downgrade -1

# 特定リビジョンまで戻す
uv run alembic downgrade <revision>
```

## 状態確認

```bash
# 現在のリビジョン
uv run alembic current

# 履歴
uv run alembic history --verbose

# モデルと DB の差分チェック（差分があれば非ゼロ終了）
uv run alembic check
```

## 環境別の実行（local / test / prod）

`.env` はローカル開発専用。test / prod の Neon に対しては、
`DATABASE_URL` をコマンド実行時にインライン指定して切り替える。

```bash
# ローカル（.env をそのまま使用）
uv run alembic upgrade head

# test 環境
DATABASE_URL='postgresql://...test...neon.tech/dbname?sslmode=require' \
  uv run alembic upgrade head

# prod 環境（慎重に）
DATABASE_URL='postgresql://...prod...neon.tech/dbname?sslmode=require' \
  uv run alembic upgrade head
```

運用フロー: **ローカルで生成・検証 → test に適用して動作確認 → prod に適用**。

> メモ: マイグレーション（DDL）実行時は Neon の **Direct connection**
> （ホスト名に `-pooler` が付かない方）を使うのが安全。
> プール経由（`-pooler` 付き）はアプリ実行用に使う。

## 既存 DB への初回導入（重要）

test / prod の Neon には既にテーブルが存在する（旧 `create_tables()` で作成済み）。
このため初回マイグレーション `initial schema` を **実行せずに適用済みとして記録**する。

```bash
# 各環境ごとに 1 回だけ実行する
DATABASE_URL='<test または prod の URL>' uv run alembic stamp head

# スキーマがモデルと一致しているか確認
DATABASE_URL='<同じ URL>' uv run alembic check
```

`alembic stamp head` 以降は、モデル変更 → `revision --autogenerate` →
`upgrade head` の通常フローで運用する。

## 注意

- 接続先は `alembic.ini` には書かず、`.env` またはインライン `DATABASE_URL` で切り替える。
- 適用済みのマイグレーションファイルは編集しない。
- マイグレーションファイルは必ずバージョン管理に含める。
- prod 適用前に必ず local → test の順で検証する。
