#!/usr/bin/env python3
"""
Script to test Neon database connection
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parents[1]))

def test_connection():
    # Load Neon environment variables
    env_file = Path(__file__).parents[1] / '.env.neon'
    if env_file.exists():
        load_dotenv(env_file)
        print("✅ Loaded .env.neon file")
    else:
        print("❌ .env.neon file not found!")
        print("Please create .env.neon with your Neon database credentials")
        return False

    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False

    print(f"📊 Database URL: {database_url[:20]}...")

    # Test connection
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Successfully connected to Neon database!")
            print(f"   PostgreSQL version: {version}")

            # Check tables
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]

            if tables:
                print(f"📋 Existing tables: {', '.join(tables)}")
            else:
                print("📋 No tables found (empty database)")

        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Neon database connection...")
    success = test_connection()
    sys.exit(0 if success else 1)