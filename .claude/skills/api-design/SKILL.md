---
name: api-design
description: REST API design, versioning, pagination, error handling, OpenAPI, rate limiting
---

# API Design Patterns

## RESTful Resource Design

### URL Structure

```
GET    /api/v1/users              # List users
POST   /api/v1/users              # Create user
GET    /api/v1/users/{id}         # Get user
PUT    /api/v1/users/{id}         # Replace user
PATCH  /api/v1/users/{id}         # Partial update
DELETE /api/v1/users/{id}         # Delete user

# Nested resources (one level deep max)
GET    /api/v1/users/{id}/orders  # User's orders

# Actions (when CRUD doesn't fit)
POST   /api/v1/users/{id}/activate
POST   /api/v1/orders/{id}/cancel
```

**Conventions:**
- Plural nouns for resources (`/users` not `/user`)
- Maximum one level of nesting
- Use query params for filtering: `/users?status=active&role=admin`
- Use hyphens, not underscores: `/user-profiles` not `/user_profiles`

### HTTP Methods & Status Codes

| Method | Success | Failure | Idempotent |
|--------|---------|---------|------------|
| GET | 200 | 404 | Yes |
| POST | 201 + Location header | 400/409 | No |
| PUT | 200 | 400/404 | Yes |
| PATCH | 200 | 400/404 | No |
| DELETE | 204 (no body) | 404 | Yes |

## Versioning

### URL Path Versioning (Recommended)

```
/api/v1/users
/api/v2/users
```

**When to bump version:**
- Breaking changes to response shape
- Removing fields or endpoints
- Changing field types

**When NOT to bump:**
- Adding new optional fields
- Adding new endpoints
- Bug fixes

### Deprecation Strategy

```http
Sunset: Sat, 01 Jan 2027 00:00:00 GMT
Deprecation: true
Link: </api/v2/users>; rel="successor-version"
```

Return deprecation headers for 6+ months before removing.

## Pagination

### Cursor-Based (Recommended for Large Datasets)

```json
GET /api/v1/users?limit=20&cursor=eyJpZCI6MTAwfQ

{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIwfQ",
    "has_more": true
  }
}
```

**Why cursor over offset:** Offset pagination breaks when items are inserted/deleted between pages. Cursor is stable.

### Offset-Based (Simple, for Small Datasets)

```json
GET /api/v1/users?page=2&per_page=20

{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address",
        "code": "invalid_format"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

### Error Code Conventions

| HTTP Status | When to Use |
|------------|-------------|
| 400 | Malformed request, validation errors |
| 401 | Missing or invalid authentication |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (duplicate, state conflict) |
| 422 | Semantically invalid (valid JSON, bad values) |
| 429 | Rate limited |
| 500 | Unexpected server error |

**Never return 200 with an error body.** Use proper HTTP status codes.

## Rate Limiting

### Response Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 67
X-RateLimit-Reset: 1640000000
Retry-After: 30
```

### Implementation Strategies

| Strategy | Use Case | Complexity |
|----------|----------|------------|
| Fixed window | Simple APIs | Low |
| Sliding window | Smooth traffic | Medium |
| Token bucket | Burst-friendly | Medium |
| Per-user + per-IP | Public APIs | High |

## Authentication Patterns

### Bearer Token (JWT)

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**JWT Best Practices:**
- Short expiry (15 min access, 7 day refresh)
- Store refresh token server-side (not in JWT)
- Include only essential claims (user_id, roles)
- Use RS256 for multi-service, HS256 for single-service

### API Key

```http
X-API-Key: sk_live_abc123...
```

Use for server-to-server. Never expose in client-side code.

## Request/Response Conventions

### Filtering & Sorting

```
GET /api/v1/users?status=active&sort=-created_at,name
```

- Prefix with `-` for descending
- Comma-separated for multiple sort fields
- Use query params, not request body for GET

### Field Selection (Sparse Fieldsets)

```
GET /api/v1/users?fields=id,name,email
```

Reduces payload size. Useful for mobile clients.

### Bulk Operations

```json
POST /api/v1/users/bulk
{
  "operations": [
    {"method": "create", "data": {"name": "Alice"}},
    {"method": "create", "data": {"name": "Bob"}}
  ]
}

// Response: 207 Multi-Status
{
  "results": [
    {"status": 201, "data": {"id": 1, "name": "Alice"}},
    {"status": 201, "data": {"id": 2, "name": "Bob"}}
  ]
}
```

## OpenAPI / Documentation

### Minimum Viable Spec

Every API should have:
1. OpenAPI 3.1 spec (auto-generated or hand-written)
2. Authentication instructions
3. Error response examples
4. Rate limit documentation
5. Changelog for breaking changes

### Framework Integration

| Framework | Auto-Gen Tool |
|-----------|---------------|
| FastAPI | Built-in (`/docs`, `/openapi.json`) |
| Django REST | drf-spectacular |
| Express | swagger-jsdoc |
| Spring Boot | springdoc-openapi |
| Go | swaggo/swag |
