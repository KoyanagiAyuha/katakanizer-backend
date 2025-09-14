#!/usr/bin/env python3
"""
データベースマイグレーションスクリプト
ConversionHistoryテーブルにuser_idカラムを追加
"""

import sqlite3
import os
from app.database import DATABASE_URL

def migrate_database():
    # データベースファイルのパスを取得
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = db_path[2:]  # "./" を削除
    else:
        print("このスクリプトはSQLiteデータベース専用です")
        return
    
    print(f"マイグレーション対象: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"データベースファイルが見つかりません: {db_path}")
        print("新規作成される場合は、アプリケーション起動時に自動的にuser_idカラムが含まれます")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # user_idカラムが既に存在するかチェック
        cursor.execute("PRAGMA table_info(conversion_history)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' in columns:
            print("user_idカラムは既に存在します。マイグレーション不要です。")
        else:
            print("user_idカラムを追加中...")
            cursor.execute("ALTER TABLE conversion_history ADD COLUMN user_id INTEGER")
            conn.commit()
            print("✅ user_idカラムを正常に追加しました")
        
    except Exception as e:
        print(f"❌ マイグレーション中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database()