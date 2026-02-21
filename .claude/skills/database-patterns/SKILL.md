---
name: database-patterns
description: SQL optimization, indexing, migration safety, N+1 prevention, connection pooling
---
# Database Patterns Skill

## SQL Optimization

### Reading EXPLAIN Output
```sql
EXPLAIN ANALYZE SELECT u.name, COUNT(o.id)
FROM users u JOIN orders o ON u.id = o.user_id
WHERE u.active = true
GROUP BY u.name;
```

Key things to look for:
- **Seq Scan** on large tables → Needs index
- **Nested Loop** with large outer table → Consider hash/merge join
- **Sort** with high cost → Add index matching ORDER BY
- **Actual rows** vs **estimated rows** — Large discrepancy = stale statistics (`ANALYZE`)

### Join Optimization
- Put the most restrictive filter conditions in WHERE, not HAVING
- Filter before joining (subqueries or CTEs for pre-filtering)
- Index foreign key columns
- Avoid joining on expressions (non-sargable)

### Subquery vs JOIN
- **Use JOIN**: When you need data from both tables
- **Use subquery**: When checking existence (`WHERE EXISTS`)
- **Use CTE**: For readability in complex queries
- **Avoid**: Correlated subqueries in SELECT (N+1 at SQL level)

## Indexing Strategies

### B-tree (Default)
- Equality and range queries: `=`, `<`, `>`, `BETWEEN`, `LIKE 'prefix%'`
- Column order matters in composite indexes: put equality columns first, then range

```sql
-- For: WHERE status = 'active' AND created_at > '2024-01-01'
CREATE INDEX idx_users_status_created ON users (status, created_at);
```

### Covering Indexes (INCLUDE)
```sql
-- Avoids table lookup for name/email
CREATE INDEX idx_users_active ON users (status)
INCLUDE (name, email);
```

### Partial Indexes
```sql
-- Only index active users (smaller, faster)
CREATE INDEX idx_active_users ON users (email)
WHERE active = true;
```

### GIN (Generalized Inverted Index)
- Full-text search, JSONB, array containment
```sql
CREATE INDEX idx_posts_tags ON posts USING gin (tags);
-- Enables: WHERE tags @> ARRAY['python', 'django']
```

### When NOT to Index
- Tables with <1000 rows (full scan is fast enough)
- Columns with very low cardinality (boolean columns, unless partial index)
- Write-heavy columns that change frequently
- Unused query patterns

## Migration Safety

### Zero-Downtime Pattern
```
1. Add nullable column (no lock)
2. Deploy code that writes to both old and new columns
3. Backfill existing data (batched)
4. Add NOT NULL constraint with DEFAULT
5. Deploy code that reads from new column
6. Drop old column (separate migration)
```

### Large Table Operations
```sql
-- Add column: safe (no rewrite in PostgreSQL 11+)
ALTER TABLE users ADD COLUMN bio TEXT;

-- Add NOT NULL with default: safe in PG 11+ (stores default in catalog)
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user';

-- DANGEROUS: Adding constraint on large table locks for validation
-- Instead:
ALTER TABLE users ADD CONSTRAINT chk_email
CHECK (email IS NOT NULL) NOT VALID;  -- Immediate, no validation
ALTER TABLE users VALIDATE CONSTRAINT chk_email;  -- Background validation
```

### Rollback Strategies
- Forward-fix preferred over rollback
- If rollback needed: reverse migration must be safe too
- Never drop columns in the same deploy as code changes

## N+1 Prevention

### Django
```python
# BAD: N+1 (one query per author)
books = Book.objects.all()
for book in books:
    print(book.author.name)

# GOOD: Single JOIN
books = Book.objects.select_related('author')

# GOOD: Separate prefetch for M2M/reverse FK
books = Book.objects.prefetch_related('tags', 'reviews')
```

### SQLAlchemy
```python
# BAD: Lazy loading (N+1)
users = session.query(User).all()
for user in users:
    print(user.orders)

# GOOD: Eager loading
from sqlalchemy.orm import joinedload, subqueryload
users = session.query(User).options(joinedload(User.orders)).all()
```

### Detection
- Django: `django-debug-toolbar` shows query count per request
- SQLAlchemy: `echo=True` on engine logs all queries
- General: Any request with >10 DB queries is suspicious

## Connection Pooling

### PgBouncer
```ini
[pgbouncer]
pool_mode = transaction    # Release connection after each transaction
max_client_conn = 400
default_pool_size = 20
min_pool_size = 5
```

### Django
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Reuse connections for 10 minutes
        'CONN_HEALTH_CHECKS': True,  # Django 4.1+
    }
}
```

### SQLAlchemy
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,      # Check connection health
    pool_recycle=3600,        # Recycle after 1 hour
)
```
