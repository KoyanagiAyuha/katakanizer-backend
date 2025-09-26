#!/bin/bash

# Script to sync database schema from test to prod (structure only, not data)
# Usage: ./scripts/db_sync.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cd "$(dirname "$0")/.."

echo -e "${BLUE}🔄 Database Schema Sync Tool${NC}"
echo -e "${YELLOW}This will apply all test migrations to production${NC}"
echo -e "${RED}⚠️  WARNING: This will modify the PRODUCTION database!${NC}"
echo -e "${RED}Make sure all migrations have been tested thoroughly!${NC}"
echo ""
echo -e "Are you sure you want to continue? (type 'sync-prod' to confirm)"
read -r confirmation

if [ "$confirmation" != "sync-prod" ]; then
    echo -e "${YELLOW}Sync cancelled.${NC}"
    exit 0
fi

# Activate virtual environment
source venv/bin/activate

# First, check test environment status
echo -e "${BLUE}📊 Checking TEST environment status...${NC}"
if [ ! -f ".env.test" ]; then
    echo -e "${RED}❌ .env.test not found!${NC}"
    exit 1
fi

export $(grep -v '^#' .env.test | xargs)
TEST_REVISION=$(alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)
echo -e "${GREEN}✓ Test environment at revision: $TEST_REVISION${NC}"

# Then, check production environment status
echo -e "${BLUE}📊 Checking PRODUCTION environment status...${NC}"
if [ ! -f ".env.prod" ]; then
    echo -e "${RED}❌ .env.prod not found!${NC}"
    exit 1
fi

export $(grep -v '^#' .env.prod | xargs)
PROD_REVISION=$(alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)
echo -e "${GREEN}✓ Production environment at revision: $PROD_REVISION${NC}"

# Compare revisions
if [ "$TEST_REVISION" = "$PROD_REVISION" ]; then
    echo -e "${GREEN}✅ Test and Production are already in sync!${NC}"
    exit 0
fi

# Show pending migrations
echo -e "${YELLOW}📋 Pending migrations for production:${NC}"
alembic history -r$PROD_REVISION:$TEST_REVISION

echo ""
echo -e "${RED}Final confirmation: Apply these migrations to PRODUCTION? (yes/no)${NC}"
read -r final_confirmation

if [ "$final_confirmation" != "yes" ]; then
    echo -e "${YELLOW}Sync cancelled.${NC}"
    exit 0
fi

# Apply migrations to production
echo -e "${BLUE}🚀 Applying migrations to PRODUCTION...${NC}"
alembic upgrade $TEST_REVISION

echo -e "${GREEN}✅ Production database synced successfully!${NC}"
alembic current