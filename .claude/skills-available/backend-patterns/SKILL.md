---
name: backend-patterns
description: Backend architecture, caching strategies, message queues, service communication, resilience patterns
---

# Backend Architecture Patterns

## Layered Architecture

```
┌─────────────────────────────┐
│      API / Controllers      │  ← HTTP handling, validation, serialization
├─────────────────────────────┤
│      Service / Business     │  ← Business logic, orchestration
├─────────────────────────────┤
│      Repository / Data      │  ← Database access, queries
├─────────────────────────────┤
│      Infrastructure         │  ← External APIs, caching, messaging
└─────────────────────────────┘
```

**Rules:**
- Each layer only calls the layer directly below it
- Never import controllers in services or repositories
- Business logic lives in the service layer, not in controllers
- Repository layer returns domain objects, not ORM models

### Dependency Injection

```python
# Good: inject dependencies
class UserService:
    def __init__(self, user_repo: UserRepository, email_service: EmailService):
        self.user_repo = user_repo
        self.email_service = email_service

# Bad: create dependencies internally
class UserService:
    def __init__(self):
        self.user_repo = UserRepository(get_db())  # hard to test
```

## Caching Strategies

### Cache-Aside (Lazy Loading)

```python
async def get_user(user_id: int) -> User:
    # 1. Check cache
    cached = await cache.get(f"user:{user_id}")
    if cached:
        return User.from_json(cached)

    # 2. Cache miss → fetch from DB
    user = await db.get_user(user_id)

    # 3. Populate cache
    await cache.set(f"user:{user_id}", user.to_json(), ttl=300)
    return user
```

### Write-Through

```python
async def update_user(user_id: int, data: dict) -> User:
    # 1. Update DB
    user = await db.update_user(user_id, data)

    # 2. Update cache simultaneously
    await cache.set(f"user:{user_id}", user.to_json(), ttl=300)
    return user
```

### Cache Invalidation Patterns

| Pattern | When to Use | Complexity |
|---------|-------------|------------|
| TTL expiry | Read-heavy, eventual consistency OK | Low |
| Event-based invalidation | Write-heavy, need consistency | Medium |
| Write-through | Need strong consistency | Medium |
| Cache stampede protection | High-traffic keys | High |

### Cache Stampede Prevention

```python
async def get_with_lock(key: str, fetch_fn, ttl=300):
    value = await cache.get(key)
    if value:
        return value

    # Acquire lock to prevent multiple DB hits
    lock = await cache.set(f"lock:{key}", "1", nx=True, ttl=10)
    if lock:
        value = await fetch_fn()
        await cache.set(key, value, ttl=ttl)
        return value
    else:
        # Another process is fetching; wait and retry
        await asyncio.sleep(0.1)
        return await get_with_lock(key, fetch_fn, ttl)
```

## Message Queue Patterns

### When to Use Queues

| Scenario | Direct Call | Queue |
|----------|------------|-------|
| User-facing response needed | Yes | No |
| Can tolerate delay | No | Yes |
| Retry on failure needed | Maybe | Yes |
| Multiple consumers | No | Yes |
| Spike absorption | No | Yes |

### Common Patterns

**Work Queue (Task Distribution):**
```
Producer ──▶ Queue ──▶ Worker 1
                  ──▶ Worker 2
                  ──▶ Worker 3
```

Use for: email sending, image processing, report generation.

**Pub/Sub (Event Broadcasting):**
```
Publisher ──▶ Exchange ──▶ Queue A ──▶ Service A
                     ──▶ Queue B ──▶ Service B
                     ──▶ Queue C ──▶ Service C
```

Use for: event-driven architecture, audit logging, notifications.

**Dead Letter Queue:**
```
Main Queue ──▶ Consumer ──(fail 3x)──▶ Dead Letter Queue
                                           │
                                    Manual review / retry
```

Always configure a DLQ for failed messages. Never silently drop.

### Message Idempotency

```python
async def process_payment(message):
    idempotency_key = message["idempotency_key"]

    # Check if already processed
    if await db.exists("processed_messages", idempotency_key):
        return  # Skip duplicate

    # Process
    await payment_service.charge(message["amount"])

    # Mark as processed
    await db.insert("processed_messages", idempotency_key)
```

## Service Communication

### Synchronous (HTTP/gRPC)

| Protocol | Best For | Latency |
|----------|----------|---------|
| REST/HTTP | Public APIs, CRUD | Medium |
| gRPC | Internal services, streaming | Low |
| GraphQL | Frontend-driven queries | Medium |

### Circuit Breaker Pattern

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
async def call_payment_service(data):
    response = await httpx.post("http://payments/charge", json=data)
    response.raise_for_status()
    return response.json()
```

**States:**
- **Closed** (normal): Requests pass through
- **Open** (tripped): Requests fail immediately (no call)
- **Half-Open** (testing): Allow one request to test recovery

### Retry with Exponential Backoff

```python
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=1, max=60), stop=stop_after_attempt(5))
async def call_external_api(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

**Backoff sequence:** 1s → 2s → 4s → 8s → 16s (with jitter).

## Background Job Patterns

### Task Queue (Celery / RQ / Dramatiq)

```python
# Define task
@celery.task(bind=True, max_retries=3)
def send_welcome_email(self, user_id: int):
    try:
        user = User.objects.get(id=user_id)
        email_service.send_welcome(user.email)
    except Exception as exc:
        self.retry(exc=exc, countdown=60)

# Enqueue
send_welcome_email.delay(user_id=42)
```

### Scheduled Jobs

```python
# Celery Beat
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-sessions': {
        'task': 'tasks.cleanup_sessions',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

## Resilience Patterns

### Bulkhead (Isolation)

Isolate failures so one failing component doesn't take down everything:

```python
# Separate thread pools / connection pools per service
payment_pool = httpx.AsyncClient(limits=httpx.Limits(max_connections=10))
email_pool = httpx.AsyncClient(limits=httpx.Limits(max_connections=5))
```

### Timeout Everything

```python
# Never make a call without a timeout
async with httpx.AsyncClient(timeout=5.0) as client:
    response = await client.get(url)
```

**Default timeouts:**
- Internal service calls: 5s
- External API calls: 10-30s
- Database queries: 5-10s
- Background jobs: task-specific (minutes to hours)

### Graceful Degradation

```python
async def get_recommendations(user_id: int):
    try:
        return await recommendation_service.get(user_id)
    except (TimeoutError, CircuitBreakerError):
        # Fall back to popular items
        return await cache.get("popular_items")
```

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Business logic in controllers | Move to service layer |
| Direct DB calls from controllers | Use repository pattern |
| No timeouts on HTTP calls | Set explicit timeouts everywhere |
| Synchronous external calls in request path | Use message queues for non-critical work |
| No retry logic | Add retries with exponential backoff |
| No circuit breakers | Add circuit breakers for external services |
| Hardcoded config | Use environment variables |
| No health checks | Add `/healthz` and `/readyz` endpoints |
| Logging sensitive data | Sanitize PII from logs |
