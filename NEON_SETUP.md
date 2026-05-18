# Neon Database Setup Guide

## 1. Neonアカウントの準備

1. [Neon](https://neon.tech) にサインアップ
2. 新しいプロジェクトを作成
3. Dashboard > Connection Details から接続情報を取得

## 2. 接続情報の設定

`.env` ファイルの `DATABASE_URL` に、Neon ダッシュボードから取得した接続文字列を記入する：

```env
DATABASE_URL=postgresql://username:password@xxx.neon.tech/dbname?sslmode=require
```

**重要**:
- `?sslmode=require` は必須（NeonはSSL接続が必要）
- パスワードに特殊文字が含まれる場合はURLエンコードが必要
- `postgresql://` は `alembic/env.py` 側で自動的に `postgresql+asyncpg://` に変換される

## 3. マイグレーションの実行

依存は `uv` で管理しているため、`uv run` でそのまま実行できる。

### 初回セットアップ（既存テーブルがある場合）

Neon に既にテーブルが存在する場合は、初回マイグレーションを実行せず
適用済みとして記録する：

```bash
uv run alembic stamp head
uv run alembic check   # スキーマがモデルと一致しているか確認
```

### 通常のマイグレーション適用

```bash
uv run alembic upgrade head
```

### 新しいマイグレーション作成

```bash
uv run alembic revision --autogenerate -m "変更内容の説明"
```

詳細は [README_MIGRATIONS.md](README_MIGRATIONS.md) を参照。

## 4. 本番環境での運用

### Docker環境の場合
```bash
# Dockerfileまたはdocker-compose.ymlで環境変数を設定
docker run -e DATABASE_URL="postgresql://..." your-app
```

### バックアップ
Neonは自動バックアップを提供していますが、重要な変更前には手動でバックアップを取ることを推奨：
```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

## トラブルシューティング

### SSL接続エラー
```
Error: SSL connection required
```
→ URLに`?sslmode=require`が含まれているか確認

### 接続タイムアウト
```
Error: Connection timeout
```
→ IPアドレスのホワイトリスト設定を確認（Neon Dashboardで設定）

### 権限エラー
```
Error: Permission denied
```
→ ユーザーの権限設定を確認（Neon Dashboardで設定）

## セキュリティ注意事項

1. **`.env`は絶対にGitにコミットしない**（`.gitignore` 済み）
2. **本番環境では環境変数を使用**
3. **定期的にパスワードを更新**
4. **IPホワイトリストを設定**（可能な場合）

## 参考リンク

- [Neon Documentation](https://neon.tech/docs)
- [Neon Python Guide](https://neon.tech/docs/guides/python)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)