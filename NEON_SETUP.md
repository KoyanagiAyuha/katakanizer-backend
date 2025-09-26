# Neon Database Setup Guide

## 1. Neonアカウントの準備

1. [Neon](https://neon.tech) にサインアップ
2. 新しいプロジェクトを作成
3. Dashboard > Connection Details から接続情報を取得

## 2. 接続情報の設定

### Step 1: 環境ファイルの作成
```bash
cd backend
cp .env.neon.example .env.neon
```

### Step 2: Neonの接続情報を記入
`.env.neon`ファイルを編集して、Neonダッシュボードから取得した情報を記入：

```env
DATABASE_URL=postgresql://username:password@xxx.neon.tech/dbname?sslmode=require
```

**重要**:
- `?sslmode=require` は必須（NeonはSSL接続が必要）
- パスワードに特殊文字が含まれる場合はURLエンコードが必要

## 3. 接続テスト

```bash
cd backend
source venv/bin/activate
python scripts/check_neon_connection.py
```

成功すると以下のような出力が表示されます：
```
✅ Successfully connected to Neon database!
   PostgreSQL version: PostgreSQL 16.x
```

## 4. マイグレーションの実行

### 初回セットアップ
```bash
# スクリプトを使用
./scripts/migrate_neon.sh

# または手動で
source venv/bin/activate
export $(grep -v '^#' .env.neon | xargs)
alembic upgrade head
```

### 新しいマイグレーション作成
```bash
source venv/bin/activate
export $(grep -v '^#' .env.neon | xargs)
alembic revision --autogenerate -m "Description of changes"
```

## 5. 本番環境での運用

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

1. **`.env.neon`は絶対にGitにコミットしない**
2. **本番環境では環境変数を使用**
3. **定期的にパスワードを更新**
4. **IPホワイトリストを設定**（可能な場合）

## 参考リンク

- [Neon Documentation](https://neon.tech/docs)
- [Neon Python Guide](https://neon.tech/docs/guides/python)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)