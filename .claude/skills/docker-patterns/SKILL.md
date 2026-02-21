---
name: docker-patterns
description: Docker Compose, multi-stage builds, container security, volume management, networking
---

# Docker Patterns

## Multi-Stage Builds

Minimize image size with staged builds:

```dockerfile
# Stage 1: Build
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
COPY --from=builder /install /usr/local
COPY . /app
WORKDIR /app
USER nobody
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

**Key principles:**
- Separate build dependencies from runtime
- Use `--no-cache-dir` to reduce layer size
- Always run as non-root (`USER nobody`)
- Pin base image versions (not `latest`)

## Docker Compose Patterns

### Service Dependencies

```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    build: .
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
```

**Use `service_healthy` over `service_started`** — prevents race conditions where the app starts before the database is ready.

### Environment Management

```yaml
# docker-compose.override.yml (dev only, gitignored)
services:
  app:
    volumes:
      - .:/app          # Hot reload
    environment:
      - DEBUG=true
```

Separate `docker-compose.yml` (base) from `docker-compose.override.yml` (dev) and `docker-compose.prod.yml` (production).

## Container Security

### Image Hardening Checklist

1. **Base image**: Use `-slim` or `-alpine` variants
2. **No root**: Always set `USER` directive
3. **Read-only filesystem**: `--read-only` flag where possible
4. **No secrets in layers**: Use build args or mounted secrets, never `COPY .env`
5. **Scan images**: `docker scout cves <image>` or Trivy

### Secret Management

```dockerfile
# BAD - secret baked into image layer
COPY .env /app/.env

# GOOD - mounted at runtime
# docker run --env-file .env myapp
```

```yaml
# Docker Compose secrets
services:
  app:
    secrets:
      - db_password
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

## Networking

### Service Discovery

Services in the same Compose network resolve by service name:

```python
# In app container, connect to db container:
DATABASE_URL = "postgresql://user:pass@db:5432/mydb"
#                                       ^^-- service name, not localhost
```

### Port Exposure

```yaml
services:
  app:
    ports:
      - "8000:8000"    # host:container (exposed externally)
    expose:
      - "9090"         # container only (internal metrics)
```

**Use `expose` for internal-only ports** (metrics, debug endpoints).

## Volume Patterns

### Named Volumes for Persistence

```yaml
volumes:
  postgres_data:     # Named volume (persists across restarts)

services:
  db:
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Bind Mounts for Development

```yaml
services:
  app:
    volumes:
      - .:/app                           # Source code (hot reload)
      - /app/node_modules                # Exclude node_modules
      - /app/.venv                       # Exclude virtualenv
```

**Anonymous volume trick**: Mount an empty path to *exclude* host directories from the bind mount.

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| `FROM python:latest` | Pin version: `FROM python:3.12-slim` |
| Running as root | Add `USER nobody` |
| Installing dev deps in prod | Multi-stage build |
| Storing secrets in image | Mount at runtime |
| No `.dockerignore` | Add `.git`, `__pycache__`, `.env`, `node_modules` |
| Fat images (>500MB) | Use slim/alpine + multi-stage |
| No health checks | Add `HEALTHCHECK` or compose healthcheck |

## .dockerignore Template

```
.git
.github
__pycache__
*.pyc
.env
.env.*
node_modules
.venv
*.egg-info
.mypy_cache
.pytest_cache
.coverage
docs/
tests/
```
