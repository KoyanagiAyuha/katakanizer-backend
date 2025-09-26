# 環境構成ガイド

## 🎯 環境の種類

### 1. Local Development (ローカル開発)
- **用途**: 開発時のローカル環境
- **データベース**: Docker PostgreSQL または SQLite
- **設定ファイル**: `.env`
- **特徴**: デバッグモード有効、メール送信スキップ可能

### 2. Test Environment (テスト環境)
- **用途**: 本番デプロイ前のテスト、ステージング
- **データベース**: Neon Test Branch または別プロジェクト
- **設定ファイル**: `.env.test`
- **特徴**: 本番に近い設定、テストデータ使用可

### 3. Production Environment (本番環境)
- **用途**: 実際のユーザーが使用する環境
- **データベース**: Neon Main Branch
- **設定ファイル**: `.env.prod`
- **特徴**: 最高のセキュリティ、パフォーマンス最適化

## 📦 Neonでの環境構成

### オプション1: ブランチ戦略（推奨）
```
Neon Project
├── main (本番)
├── test (テスト)
└── dev (開発) ※必要に応じて
```

**メリット**:
- データベーススキーマの同期が簡単
- ブランチ間でのデータコピーが可能
- コスト効率的

### オプション2: 別プロジェクト戦略
```
Neon
├── katakanizer-prod (本番プロジェクト)
├── katakanizer-test (テストプロジェクト)
└── katakanizer-dev (開発プロジェクト)
```

**メリット**:
- 完全に独立した環境
- 権限管理が明確
- 課金の分離

## 🚀 セットアップ手順

### 1. Neonでデータベースを作成

#### ブランチ戦略の場合:
```bash
# Neon CLIを使用（オプション）
neon branch create test --project-id your-project-id
```

または、Neonダッシュボードから:
1. Project → Branches
2. 「Create Branch」をクリック
3. 「test」ブランチを作成

### 2. 環境ファイルの設定

```bash
cd backend

# テスト環境
cp .env.test.example .env.test
nano .env.test  # Neon test branchの接続情報を記入

# 本番環境
cp .env.prod.example .env.prod
nano .env.prod  # Neon main branchの接続情報を記入
```

### 3. 各環境でのマイグレーション実行

```bash
# テスト環境
./scripts/migrate.sh test

# 本番環境（慎重に！）
./scripts/migrate.sh prod
```

## 🔄 ワークフロー

### 標準的な開発フロー

1. **ローカル開発**
   ```bash
   # ローカルで開発・テスト
   docker-compose up
   ./scripts/migrate.sh local
   ```

2. **テスト環境へデプロイ**
   ```bash
   # マイグレーション作成
   alembic revision --autogenerate -m "Add new feature"

   # テスト環境で検証
   ./scripts/migrate.sh test
   ```

3. **本番環境へデプロイ**
   ```bash
   # テストが完了したら本番へ
   ./scripts/migrate.sh prod

   # または同期スクリプトを使用
   ./scripts/db_sync.sh
   ```

## 🔐 セキュリティベストプラクティス

### 1. 環境変数の管理
- **絶対にGitにコミットしない**: `.env.*` ファイル
- **強力なパスワード**: 本番環境は特に注意
- **定期的な更新**: 3ヶ月ごとにパスワード変更

### 2. アクセス制限
```python
# app/config.py で環境別設定
import os

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    # 本番環境の設定
    DEBUG = False
    ALLOWED_HOSTS = ['katakanizer.com']
    SECURE_SSL_REDIRECT = True
elif ENVIRONMENT == 'test':
    # テスト環境の設定
    DEBUG = True
    ALLOWED_HOSTS = ['test.katakanizer.com']
else:
    # 開発環境の設定
    DEBUG = True
    ALLOWED_HOSTS = ['*']
```

### 3. バックアップ戦略
```bash
# 本番データベースの定期バックアップ
# crontab -e で追加
0 3 * * * /path/to/backup_prod.sh
```

## 📊 環境別の推奨設定

| 設定項目 | Local | Test | Production |
|---------|-------|------|------------|
| DEBUG | true | true | false |
| EMAIL_VERIFICATION | false | true | true |
| RATE_LIMITING | false | true | true |
| LOG_LEVEL | debug | info | warning |
| CORS | * | test domain | prod domain |
| SSL | optional | required | required |
| DB_POOL_SIZE | 5 | 10 | 20 |

## 🔧 トラブルシューティング

### 環境変数が読み込まれない
```bash
# 環境変数を確認
env | grep DATABASE_URL

# 手動で読み込み
source .env.test
```

### マイグレーションの不整合
```bash
# 現在のリビジョンを確認
alembic current

# ヘッドを確認
alembic heads

# 強制的に特定のリビジョンにマーク
alembic stamp head
```

### 環境間でのデータ移行
```bash
# Neonのデータコピー機能を使用（ブランチ戦略の場合）
# または pg_dump/pg_restore を使用

# テストから本番へ（構造のみ）
pg_dump $TEST_DATABASE_URL --schema-only | psql $PROD_DATABASE_URL
```

## 📝 チェックリスト

### 新機能デプロイ時
- [ ] ローカルでテスト完了
- [ ] マイグレーションファイル作成
- [ ] テスト環境でマイグレーション実行
- [ ] テスト環境で機能テスト
- [ ] 本番環境のバックアップ取得
- [ ] 本番環境でマイグレーション実行
- [ ] 本番環境で動作確認
- [ ] モニタリング確認

### 月次メンテナンス
- [ ] 各環境のディスク使用量確認
- [ ] 不要なブランチの削除
- [ ] パフォーマンスメトリクスの確認
- [ ] セキュリティアップデートの確認