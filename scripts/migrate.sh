#!/bin/bash

# Universal migration script for different environments
# Usage: ./scripts/migrate.sh [test|prod|local]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get environment argument
ENV=${1:-local}

# Navigate to backend directory
cd "$(dirname "$0")/.."

echo -e "${BLUE}🚀 Starting database migration for ${YELLOW}$ENV${BLUE} environment...${NC}"

# Activate virtual environment
source venv/bin/activate

# Load appropriate environment file
case $ENV in
    local|development|dev)
        ENV_FILE=".env"
        echo -e "${GREEN}📝 Loading LOCAL environment...${NC}"
        ;;
    neon|test)
        ENV_FILE=".env.neon"
        echo -e "${BLUE}📝 Loading NEON TEST environment...${NC}"
        export DATABASE_URL=$(grep TEST_DATABASE_URL .env.neon | cut -d '=' -f2-)
        ;;
    prod|production)
        ENV_FILE=".env.neon"
        echo -e "${RED}⚠️  Loading NEON PRODUCTION environment...${NC}"
        echo -e "${RED}   Are you sure you want to run migrations on PRODUCTION? (yes/no)${NC}"
        read -r confirmation
        if [ "$confirmation" != "yes" ]; then
            echo -e "${YELLOW}Migration cancelled.${NC}"
            exit 0
        fi
        export DATABASE_URL=$(grep PROD_DATABASE_URL .env.neon | cut -d '=' -f2-)
        ;;
    *)
        echo -e "${RED}❌ Invalid environment: $ENV${NC}"
        echo "Usage: $0 [test|prod|local|neon]"
        exit 1
        ;;
esac

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: $ENV_FILE file not found!${NC}"
    echo "Please create $ENV_FILE with your database credentials"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' $ENV_FILE | xargs)

# Display connection info (safely)
if [ ! -z "$DATABASE_URL" ]; then
    HOST=$(echo $DATABASE_URL | sed 's/.*@\([^/:]*\).*/\1/')
    DB=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
    echo -e "${BLUE}🔗 Connecting to:${NC}"
    echo -e "   Host: ${GREEN}$HOST${NC}"
    echo -e "   Database: ${GREEN}$DB${NC}"
    echo -e "   Environment: ${YELLOW}$ENV${NC}"
fi

# Run migrations
echo -e "${BLUE}📊 Running migrations...${NC}"
alembic upgrade head

echo -e "${GREEN}✅ Migration completed successfully!${NC}"

# Show current revision
echo -e "${BLUE}📍 Current revision:${NC}"
alembic current

# Show recent history
echo -e "${BLUE}📜 Recent migration history:${NC}"
alembic history --verbose | head -10