---
name: database-migrations
description: Migration safety, zero-downtime patterns, Alembic, Django, Prisma, Drizzle, rollback strategies
---

# Database Migration Patterns

## Zero-Downtime Migration Strategy

The golden rule: **never lock tables during deployment**. Split risky migrations into safe steps.

### The Expand-Contract Pattern

```
Phase 1 (Expand): Add new column/table alongside old
Phase 2 (Migrate): Backfill data, update code to write both
Phase 3 (Contract): Remove old column/table after all readers updated
```

### Safe vs Unsafe Operations

| Operation | Safe? | Risk | Mitigation |
|-----------|-------|------|------------|
| Add nullable column | Yes | None | |
| Add column with default | Depends | Table lock (Postgres <11) | Use `ALTER ... SET DEFAULT` separately |
| Add NOT NULL column | No | Table lock + backfill | Add nullable → backfill → set NOT NULL |
| Drop column | Risky | Code may reference it | Remove code references first |
| Rename column | No | Breaks running code | Add new → migrate → drop old |
| Add index | Risky | Table lock | `CREATE INDEX CONCURRENTLY` |
| Change column type | No | Table rewrite | Add new column → migrate → drop old |
| Drop table | Risky | Data loss | Verify no references, backup first |

## Framework-Specific Patterns

### Alembic (SQLAlchemy / FastAPI)

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "add user email column"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current version
alembic current

# Show history
alembic history
```

**Migration file template:**

```python
def upgrade():
    # Safe: add nullable column
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))

    # Safe: create index concurrently (PostgreSQL)
    op.execute('CREATE INDEX CONCURRENTLY ix_users_email ON users (email)')

def downgrade():
    op.drop_index('ix_users_email', table_name='users')
    op.drop_column('users', 'email')
```

**Best practices:**
- Always write `downgrade()` functions
- Use `op.execute()` for `CONCURRENTLY` operations
- Split data migrations from schema migrations
- Never import application models in migrations (use raw SQL)

### Django Migrations

```bash
# Generate migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Rollback to specific migration
python manage.py migrate myapp 0005

# Show migration status
python manage.py showmigrations

# SQL preview (don't execute)
python manage.py sqlmigrate myapp 0006
```

**Data migration pattern:**

```python
from django.db import migrations

def populate_email(apps, schema_editor):
    User = apps.get_model('myapp', 'User')
    User.objects.filter(email__isnull=True).update(email='')

class Migration(migrations.Migration):
    dependencies = [('myapp', '0005_add_email')]

    operations = [
        migrations.RunPython(populate_email, migrations.RunPython.noop),
    ]
```

**Django-specific safety:**
- Use `AddIndex` with `concurrently=True` (Django 4.2+)
- Split `makemigrations` and data migrations
- Use `apps.get_model()` not direct model imports
- Always provide `reverse_code` for `RunPython`

### Prisma (Node.js / TypeScript)

```bash
# Generate migration from schema changes
npx prisma migrate dev --name add_email

# Apply in production
npx prisma migrate deploy

# Reset database (dev only!)
npx prisma migrate reset

# Check status
npx prisma migrate status
```

**Schema change:**

```prisma
model User {
  id    Int     @id @default(autoincrement())
  email String? // nullable first, make required later

  @@index([email])
}
```

### Drizzle (TypeScript)

```bash
# Generate migration
npx drizzle-kit generate

# Apply migration
npx drizzle-kit migrate

# Push schema directly (dev only)
npx drizzle-kit push
```

## Large Table Migration Patterns

### Batched Backfill

For tables with millions of rows, never update all at once:

```python
# Alembic / SQLAlchemy
def upgrade():
    conn = op.get_bind()
    batch_size = 10000
    offset = 0

    while True:
        result = conn.execute(text(
            f"UPDATE users SET email_lower = LOWER(email) "
            f"WHERE id IN (SELECT id FROM users WHERE email_lower IS NULL LIMIT {batch_size})"
        ))
        if result.rowcount == 0:
            break
        offset += batch_size
```

```python
# Django
from django.db.models import F, Func

def backfill_email_lower(apps, schema_editor):
    User = apps.get_model('myapp', 'User')
    batch_size = 10000

    while User.objects.filter(email_lower__isnull=True).exists():
        ids = list(
            User.objects.filter(email_lower__isnull=True)
            .values_list('id', flat=True)[:batch_size]
        )
        User.objects.filter(id__in=ids).update(
            email_lower=Func(F('email'), function='LOWER')
        )
```

**Rules:**
- Batch size: 1,000-10,000 rows per transaction
- Add `time.sleep(0.1)` between batches to reduce DB load
- Run during low-traffic periods
- Monitor replication lag if using replicas

### Online Schema Change Tools

| Tool | Database | Use Case |
|------|----------|----------|
| `pt-online-schema-change` | MySQL | Column type changes, large ALTERs |
| `pg_repack` | PostgreSQL | Table/index bloat |
| `gh-ost` | MySQL | GitHub's online schema migration |
| `CREATE INDEX CONCURRENTLY` | PostgreSQL | Non-blocking index creation |

## Rollback Strategies

### Pre-Migration Checklist

1. **Backup**: `pg_dump` or equivalent before risky migrations
2. **Downgrade tested**: Verify `downgrade()` works
3. **Code compatibility**: Old code works with new schema (expand phase)
4. **Monitoring**: Watch for slow queries during migration
5. **Off-peak**: Schedule large migrations during low traffic

### Rollback Decision Matrix

| Scenario | Action |
|----------|--------|
| Migration failed mid-way | Fix and retry (don't leave partial state) |
| Migration succeeded but app broken | Rollback migration + redeploy old code |
| Data migration corrupted data | Restore from backup |
| Performance degraded | Add missing indexes, then investigate |

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Running migrations in deployment pipeline | Separate migration step with its own rollback |
| `DROP COLUMN` without removing code references | Remove code first, then column in next release |
| Not testing rollback | Always run `downgrade` in CI |
| Importing app models in migrations | Use `apps.get_model()` or raw SQL |
| Adding NOT NULL without default | Add nullable → backfill → alter to NOT NULL |
| Single migration for schema + data | Split into separate migration files |
| No migration in version control | Always commit migrations with the code |
