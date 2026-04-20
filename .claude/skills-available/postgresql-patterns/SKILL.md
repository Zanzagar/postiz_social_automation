---
name: postgresql-patterns
description: PostgreSQL query optimization with EXPLAIN ANALYZE, indexing strategies (B-tree, GIN, GiST, BRIN), partitioning, connection pooling, JSONB patterns, CTE performance, PostGIS spatial queries
---
# PostgreSQL Patterns Skill

## Query Optimization

### EXPLAIN ANALYZE
Always analyze before optimizing:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM sensor_readings
WHERE station_id = 42
AND timestamp > '2026-01-01';
```

**Key metrics:**
- `Seq Scan` → Consider adding an index
- `Rows Removed by Filter` (high) → Index not selective enough
- `Buffers: shared hit` vs `shared read` → Cache effectiveness
- `Planning Time` vs `Execution Time` → Index bloat if planning is high

### Index Strategies

| Index Type | Best For | Example |
|-----------|---------|---------|
| **B-tree** (default) | Equality, range, sorting | `CREATE INDEX idx_time ON readings(timestamp)` |
| **GiST** | Spatial, range types, full-text | `CREATE INDEX idx_geom ON sites USING gist(geom)` |
| **GIN** | JSONB, arrays, full-text search | `CREATE INDEX idx_props ON samples USING gin(properties)` |
| **BRIN** | Very large tables, naturally ordered | `CREATE INDEX idx_ts ON logs USING brin(timestamp)` |
| **Hash** | Equality only (rarely needed) | `CREATE INDEX idx_code ON stations USING hash(code)` |

### Partial Indexes
Index only the rows that matter:

```sql
-- Only index active sensors (90% of queries filter on active=true)
CREATE INDEX idx_active_sensors ON sensors(station_id)
WHERE active = true;

-- Only index recent data
CREATE INDEX idx_recent ON readings(timestamp)
WHERE timestamp > '2025-01-01';
```

### Covering Indexes (Index-Only Scans)
Include extra columns to avoid table lookups:

```sql
-- Query: SELECT value, quality FROM readings WHERE station_id = ? AND timestamp > ?
CREATE INDEX idx_readings_cover ON readings(station_id, timestamp)
INCLUDE (value, quality);
```

## PostGIS Spatial Queries

```sql
-- Spatial index (required for performance)
CREATE INDEX idx_sites_geom ON sites USING gist(geom);

-- Find points within polygon
SELECT s.name, s.geom
FROM sites s
WHERE ST_Within(s.geom, ST_GeomFromText('POLYGON((...))'));

-- Find nearest N points
SELECT s.name, ST_Distance(s.geom, target.geom) AS dist
FROM sites s, (SELECT geom FROM targets WHERE id = 1) target
ORDER BY s.geom <-> target.geom  -- KNN operator (uses GiST index)
LIMIT 10;

-- Buffer and intersect
SELECT a.id, b.name
FROM boreholes a
JOIN regions b ON ST_DWithin(a.geom, b.geom, 1000);  -- Within 1000m

-- Transform CRS
SELECT ST_Transform(geom, 32617) AS geom_utm  -- WGS84 to UTM 17N
FROM sites
WHERE ST_SRID(geom) = 4326;
```

## JSONB Patterns

```sql
-- Store flexible metadata
CREATE TABLE samples (
    id SERIAL PRIMARY KEY,
    site_id INT REFERENCES sites(id),
    properties JSONB NOT NULL DEFAULT '{}'
);

-- Query JSONB
SELECT * FROM samples
WHERE properties->>'method' = 'kriging'
AND (properties->>'confidence')::float > 0.8;

-- GIN index for JSONB
CREATE INDEX idx_sample_props ON samples USING gin(properties);

-- Path query
SELECT * FROM samples
WHERE properties @> '{"method": "kriging", "model": "spherical"}';
```

## Connection Pooling

```python
# PgBouncer config (pgbouncer.ini)
# pool_mode = transaction    # Release on transaction end (recommended)
# max_client_conn = 100
# default_pool_size = 25

# Python with psycopg pool
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    conninfo="postgresql://user@localhost/db",
    min_size=5,
    max_size=20,
    max_idle=300,  # Close idle connections after 5 min
)

with pool.connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sites WHERE active")
        results = cur.fetchall()
```

## CTE Performance

```sql
-- CTEs are optimization fences in PostgreSQL < 12
-- In PostgreSQL 12+, CTEs are inlined by default unless MATERIALIZED

-- Force materialization (when CTE is reused multiple times)
WITH MATERIALIZED nearby_sites AS (
    SELECT id, geom FROM sites
    WHERE ST_DWithin(geom, ST_MakePoint(-74.0, 40.7)::geography, 5000)
)
SELECT s.id, r.value
FROM nearby_sites s
JOIN readings r ON r.site_id = s.id;

-- Force inlining (default in 12+, explicit for clarity)
WITH NOT MATERIALIZED filtered AS (
    SELECT * FROM readings WHERE timestamp > now() - interval '1 day'
)
SELECT * FROM filtered WHERE value > threshold;
```

## Partitioning

```sql
-- Range partitioning (for time-series data)
CREATE TABLE readings (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    station_id INT,
    timestamp TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE readings_2026_01 PARTITION OF readings
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE readings_2026_02 PARTITION OF readings
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Automatic partition creation (pg_partman extension)
SELECT partman.create_parent(
    p_parent_table := 'public.readings',
    p_control := 'timestamp',
    p_interval := '1 month'
);
```

## VACUUM and Maintenance

```sql
-- Check table bloat
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
       n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Manual vacuum (for large batch operations)
VACUUM (VERBOSE, ANALYZE) readings;

-- Tune autovacuum for high-write tables
ALTER TABLE readings SET (
    autovacuum_vacuum_scale_factor = 0.01,  -- Vacuum at 1% dead rows (default 20%)
    autovacuum_analyze_scale_factor = 0.005
);
```

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| `SELECT *` | Reads unnecessary columns | Select only needed columns |
| Missing index on FK | Slow JOINs and cascading deletes | Add index on every FK column |
| `COUNT(*)` on large tables | Full table scan | Use `pg_stat_user_tables.n_live_tup` for estimates |
| N+1 queries from ORM | 100 queries instead of 1 | Use JOIN or batch loading |
| Large `IN (...)` lists | Plan cache pollution | Use `= ANY(ARRAY[...])` or temp table |
| `ORDER BY RANDOM()` | Full table scan + sort | Use `TABLESAMPLE` for approximation |
