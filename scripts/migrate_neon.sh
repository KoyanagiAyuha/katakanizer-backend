#!/bin/bash

# Script to run Alembic migrations on Neon database
# Usage: ./scripts/migrate_neon.sh

set -e

echo "🚀 Starting Neon database migration..."

# Navigate to backend directory
cd "$(dirname "$0")/.."

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Load Neon environment variables
if [ -f .env.neon ]; then
    echo "📝 Loading Neon environment variables..."
    export $(grep -v '^#' .env.neon | xargs)
else
    echo "❌ Error: .env.neon file not found!"
    echo "Please create .env.neon with your Neon database credentials"
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL not set in .env.neon"
    exit 1
fi

echo "🔗 Connecting to Neon database..."
echo "   Host: $(echo $DATABASE_URL | sed 's/.*@\([^/]*\).*/\1/')"

# Run migrations
echo "📊 Running migrations..."
alembic upgrade head

echo "✅ Migration completed successfully!"

# Show current revision
echo "📍 Current revision:"
alembic current