---
name: deployment-patterns
description: CI/CD pipelines, blue-green deployments, canary releases, rollback strategies, infrastructure as code
---

# Deployment Patterns

## CI/CD Pipeline Design

### Standard Pipeline Stages

```
┌──────┐   ┌──────┐   ┌───────┐   ┌────────┐   ┌────────┐
│ Lint │──▶│ Test │──▶│ Build │──▶│ Deploy │──▶│ Verify │
└──────┘   └──────┘   └───────┘   │Staging │   └────────┘
                                  └───┬────┘
                                      │ manual gate
                                  ┌───▼────┐
                                  │ Deploy │
                                  │  Prod  │
                                  └────────┘
```

**Principles:**
- Fail fast: lint and unit tests first (cheapest stages)
- Immutable artifacts: build once, deploy everywhere
- Environment parity: staging mirrors production
- Manual gate before production (for most teams)

### GitHub Actions Example

```yaml
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - run: pytest --cov

  build:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .
      - run: docker push myapp:${{ github.sha }}

  deploy-staging:
    needs: build
    environment: staging
    runs-on: ubuntu-latest
    steps:
      - run: deploy --env staging --image myapp:${{ github.sha }}

  deploy-prod:
    needs: deploy-staging
    environment: production  # Requires manual approval
    runs-on: ubuntu-latest
    steps:
      - run: deploy --env production --image myapp:${{ github.sha }}
```

## Deployment Strategies

### Blue-Green Deployment

```
                   ┌─────────────────┐
                   │  Load Balancer  │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼                           ▼
        ┌───────────┐              ┌───────────┐
        │  Blue     │              │  Green    │
        │ (current) │              │  (new)    │
        │  v1.2.0   │              │  v1.3.0   │
        └───────────┘              └───────────┘
```

**Process:**
1. Deploy new version to inactive environment (Green)
2. Run smoke tests against Green
3. Switch load balancer to Green
4. Keep Blue running for instant rollback
5. After confidence period, decommission Blue

**Rollback:** Switch load balancer back to Blue (seconds).

### Canary Release

```
Traffic split:
  ├── 95% ──▶ v1.2.0 (stable)
  └──  5% ──▶ v1.3.0 (canary)

Monitor error rates, latency, business metrics.
If healthy after 30 min, increase to 25%, then 50%, then 100%.
```

**Best for:**
- High-traffic services where full cutover is risky
- When you need to validate with real traffic
- Services with complex failure modes

### Rolling Update

```
Pod 1: v1.2.0 ──▶ v1.3.0  (replace first)
Pod 2: v1.2.0              (still serving)
Pod 3: v1.2.0              (still serving)

Pod 1: v1.3.0              (healthy)
Pod 2: v1.2.0 ──▶ v1.3.0  (replace second)
Pod 3: v1.2.0              (still serving)
...
```

**Default for Kubernetes.** Set `maxUnavailable: 1` and `maxSurge: 1`.

## Rollback Strategies

### Immediate Rollback Checklist

1. **Detect**: Monitoring alerts or manual observation
2. **Decide**: Is rollback faster than fixing forward?
3. **Execute**: Redeploy previous version
4. **Verify**: Confirm metrics return to normal
5. **Investigate**: Root cause analysis post-rollback

### Version Pinning

```bash
# Tag every deployment
docker tag myapp:$SHA myapp:release-2024-01-15

# Rollback to specific version
deploy --image myapp:release-2024-01-14
```

**Never deploy `latest` to production.** Always use immutable tags (SHA or semver).

## Environment Configuration

### 12-Factor App Principles

```
Config via environment variables, not files:

DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=...
LOG_LEVEL=info
FEATURE_FLAG_NEW_UI=true
```

### Secret Management

| Tool | Best For |
|------|----------|
| AWS Secrets Manager | AWS-native apps |
| HashiCorp Vault | Multi-cloud, on-prem |
| SOPS | Git-encrypted secrets |
| Doppler | Team-friendly SaaS |

**Never store secrets in:**
- Git repositories (even private)
- Docker images (baked into layers)
- CI/CD logs (mask all secrets)

## Health Checks & Readiness

### Probe Types

```python
# Liveness: "Is the process alive?"
@app.get("/healthz")
def liveness():
    return {"status": "ok"}

# Readiness: "Can it handle traffic?"
@app.get("/readyz")
def readiness():
    try:
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Not ready")

# Startup: "Has initialization completed?"
@app.get("/startupz")
def startup():
    if not app.state.initialized:
        raise HTTPException(503, "Starting up")
    return {"status": "started"}
```

### Graceful Shutdown

```python
import signal

def shutdown_handler(signum, frame):
    # 1. Stop accepting new requests
    # 2. Finish in-flight requests (30s timeout)
    # 3. Close database connections
    # 4. Exit cleanly
    server.shutdown(timeout=30)

signal.signal(signal.SIGTERM, shutdown_handler)
```

## Monitoring & Observability

### The Three Pillars

| Pillar | Tool Examples | What It Answers |
|--------|--------------|-----------------|
| **Metrics** | Prometheus, Datadog | Is the system healthy? |
| **Logs** | ELK, Loki | What happened? |
| **Traces** | Jaeger, OpenTelemetry | Where is the bottleneck? |

### Key Deployment Metrics

- **Error rate**: Should not increase after deploy
- **Latency p99**: Should not increase significantly
- **Request rate**: Should remain stable (no drops)
- **Saturation**: CPU/memory should stay within bounds

### Deploy-Time Annotations

```bash
# Mark deployment in monitoring
curl -X POST "https://grafana/api/annotations" \
  -d '{"text": "Deploy v1.3.0", "tags": ["deploy"]}'
```

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Deploy on Friday | Deploy early in the week |
| No rollback plan | Always have one-click rollback |
| Skipping staging | Never deploy to prod without staging |
| Manual deploys | Automate with CI/CD |
| Deploying `latest` | Use immutable version tags |
| No health checks | Add liveness + readiness probes |
| Big-bang releases | Small, frequent deployments |
