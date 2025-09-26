# Database Migrations with Alembic

## Setup

1. Create and activate virtual environment:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Using Alembic

### Create a new migration
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Or create empty migration
alembic revision -m "Description of changes"
```

### Apply migrations
```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision>
```

### Rollback migrations
```bash
# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision>

# Downgrade all the way to base
alembic downgrade base
```

### View migration status
```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show migration history with details
alembic history --verbose
```

## Environment Variables

The database connection uses the following environment variables:
- `DATABASE_URL` - Full database URL (overrides all other DB_ variables)
- `DB_USER` - Database username (default: katakanizer)
- `DB_PASSWORD` - Database password (default: password)
- `DB_HOST` - Database host (default: localhost)
- `DB_PORT` - Database port (default: 5432)
- `DB_NAME` - Database name (default: katakanizer)

## Docker Usage

When using Docker, run migrations inside the container:
```bash
docker exec katakanizer-backend-1 alembic upgrade head
```

## Notes

- Always review auto-generated migrations before applying them
- Test migrations in development before applying to production
- Keep migration files in version control
- Never edit migration files after they've been applied to a database