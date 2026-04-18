# SOVRN API Documentation

Base URL: `http://localhost:8000/api/v1`

## Authentication

SOVRN uses JWT bearer tokens for authentication.

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "<redacted-password>"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Register

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123",
  "name": "John Doe"
}
```

### Using Tokens

Include the access token in all authenticated requests:

```http
Authorization: Bearer eyJ...
```

---

## Projects

### List Projects

```http
GET /projects?page=1&status=generated
Authorization: Bearer {token}
```

Query Parameters:
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 10, max: 100)
- `status` (string): Filter by status (draft, generating, generated, deployed, failed)

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "My Website",
      "slug": "my-website",
      "description": "A business website",
      "status": "generated",
      "locale": "en-US",
      "industry": "technology",
      "business_type": "saas",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T12:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10,
  "pages": 3
}
```

### Get Project

```http
GET /projects/{id}
Authorization: Bearer {token}
```

Response includes all generations for the project.

### Create Project

```http
POST /projects
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "My New Website",
  "description": "A website for my business",
  "locale": "en-US",
  "industry": "technology",
  "business_type": "saas"
}
```

### Update Project

```http
PATCH /projects/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description"
}
```

### Delete Project

```http
DELETE /projects/{id}
Authorization: Bearer {token}
```

### Generate Website

Starts the AI generation process for a project.

```http
POST /projects/{id}/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "brief": "I need a landing page for my SaaS product that helps small businesses manage invoices. The target audience is small business owners aged 30-50. I want to emphasize ease of use, time savings, and professional look. Include pricing section, features, testimonials, and a demo request form.",
  "locale": "en-US",
  "industry": "technology",
  "business_type": "saas",
  "target_audience": {
    "age_range": "30-50",
    "profession": "small business owners"
  },
  "goals": ["lead_generation", "brand_awareness"],
  "settings": {
    "style_preference": "modern",
    "color_preference": "blue"
  }
}
```

Response:
```json
{
  "id": "job-uuid",
  "project_id": "project-uuid",
  "type": "site_generation",
  "status": "pending",
  "spark_cost": 1,
  "created_at": "2025-01-15T10:00:00Z"
}
```

### Get Preview Artifact

Returns normalized generation files and resolved preview HTML for browser runtime mounting.

```http
GET /projects/{id}/preview-artifact?generation_id={generation_id}&entrypoint=index.html
Authorization: Bearer {token}
```

Authentication modes:
- Access token (`type=access`) for regular authenticated project access.
- Preview session token (`type=preview_session`) for runtime bootstrap artifact fetches constrained by token claims.

Query Parameters:
- `generation_id` (uuid, optional): Use a specific generation. Defaults to latest generation for the project.
- `entrypoint` (string, optional): Preferred HTML entrypoint path (default: `index.html`).

Response:
```json
{
  "project_id": "project-uuid",
  "generation_id": "generation-uuid",
  "generation_version": 4,
  "entrypoint": "index.html",
  "preview_html": "<!doctype html>...",
  "files": [
    {
      "path": "index.html",
      "content": "<!doctype html>...",
      "language": "html",
      "size_bytes": 1024
    }
  ],
  "source": "site_generation"
}
```

### Create Preview Session

Issues a short-lived signed token for preview runtime bootstrap.

```http
POST /projects/{id}/preview-session
Authorization: Bearer {token}
Content-Type: application/json

{
  "generation_id": "generation-uuid",
  "entrypoint": "index.html",
  "ttl_seconds": 600
}
```

Response:
```json
{
  "token": "eyJ...",
  "token_type": "preview_session",
  "expires_at": "2026-04-17T12:00:00Z",
  "project_id": "project-uuid",
  "generation_id": "generation-uuid",
  "entrypoint": "index.html",
  "artifact_endpoint": "/api/v1/projects/project-uuid/preview-artifact?generation_id=generation-uuid&entrypoint=index.html"
}
```

### Verify Preview Session

Verifies preview session token claims for bootstrap handshake before mounting preview artifacts.

```http
POST /projects/{id}/preview-session/verify
Content-Type: application/json

{
  "token": "eyJ...",
  "generation_id": "generation-uuid",
  "entrypoint": "index.html"
}
```

Response:
```json
{
  "valid": true,
  "token_type": "preview_session",
  "project_id": "project-uuid",
  "generation_id": "generation-uuid",
  "entrypoint": "index.html",
  "expires_at": "2026-04-17T12:00:00Z",
  "artifact_endpoint": "/api/v1/projects/project-uuid/preview-artifact?generation_id=generation-uuid&entrypoint=index.html"
}
```

### Preview Event Stream

Streams incremental preview update events for builder runtime apply.

```http
GET /projects/{id}/preview-events?generation_id={generation_id}&entrypoint=index.html&preview_token={preview_session_token}
Accept: text/event-stream
```

Query Parameters:
- `generation_id` (uuid, optional): Stream updates for a specific generation; defaults to latest visible generation.
- `entrypoint` (string, optional): HTML entrypoint path (default: `index.html`).
- `preview_token` (string, optional): Preview session token for runtime bootstrap authorization.
- `poll_interval_ms` (int, optional): Poll cadence for update checks (default: 1500ms, min 250, max 15000).

Event Types:
- `preview.updated`: Emitted when generation id/version changes; contains normalized files + preview HTML.
- `heartbeat`: Liveness ping with generation metadata and timestamp.

---

## Jobs

### List Jobs

```http
GET /jobs?page=1&status=completed
Authorization: Bearer {token}
```

### Get Job

```http
GET /jobs/{id}
Authorization: Bearer {token}
```

Response:
```json
{
  "id": "uuid",
  "project_id": "project-uuid",
  "type": "site_generation",
  "status": "completed",
  "spark_cost": 1,
  "priority": 0,
  "input": { "brief": "..." },
  "output": { "generation_id": "..." },
  "started_at": "2025-01-15T10:00:00Z",
  "completed_at": "2025-01-15T10:03:00Z",
  "created_at": "2025-01-15T10:00:00Z"
}
```

Job statuses: `pending`, `processing`, `completed`, `failed`, `cancelled`

### Cancel Job

```http
POST /jobs/{id}/cancel
Authorization: Bearer {token}
```

### Retry Job

```http
POST /jobs/{id}/retry
Authorization: Bearer {token}
```

---

## Sparks

### Get Balance

```http
GET /sparks/balance
Authorization: Bearer {token}
```

Response:
```json
{
  "id": "account-uuid",
  "sparks_balance": 47,
  "sparks_used_total": 53,
  "plan": {
    "id": "plan-uuid",
    "name": "Growth",
    "type": "growth",
    "sparks_included": 50
  }
}
```

### Get History

```http
GET /sparks/history?page=1
Authorization: Bearer {token}
```

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "type": "debit",
      "amount": -1,
      "balance_after": 47,
      "description": "Website generation: My Website",
      "reference_type": "job",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 53,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

### Get Plans

```http
GET /sparks/plans
```

Response:
```json
[
  {
    "id": "uuid",
    "name": "Starter",
    "type": "starter",
    "sparks_included": 10,
    "price_cents": 1000,
    "features": {}
  },
  {
    "id": "uuid",
    "name": "Growth",
    "type": "growth",
    "sparks_included": 50,
    "price_cents": 4000,
    "features": { "popular": true }
  }
]
```

### Create Invoice

```http
POST /sparks/invoices
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan_type": "growth"
}
```

Response includes payment instructions for manual payment.

---

## Templates

### List Templates

```http
GET /templates?category=business&industry=technology
```

### Get Template

```http
GET /templates/{id}
```

### Get Categories

```http
GET /templates/categories
```

### Get Industries

```http
GET /templates/industries
```

---

## Locales

### List Locales

```http
GET /locales
```

Response:
```json
[
  {
    "id": "uuid",
    "locale_code": "en-US",
    "name": "English (United States)",
    "currency": "USD",
    "currency_symbol": "$",
    "date_format": "MM/DD/YYYY",
    "rtl": false,
    "payment_methods": ["credit_card", "paypal", "apple_pay"],
    "legal_requirements": ["privacy_policy", "terms_of_service"],
    "cultural_notes": "Direct communication style..."
  }
]
```

### Get Locale

```http
GET /locales/{code}
```

---

## Admin Endpoints

Requires admin privileges.

### List Users

```http
GET /admin/users?page=1
Authorization: Bearer {admin-token}
```

### Get System Stats

```http
GET /admin/stats
Authorization: Bearer {admin-token}
```

### Verify Invoice Payment

```http
POST /admin/invoices/{id}/verify
Authorization: Bearer {admin-token}
Content-Type: application/json

{
  "payment_reference": "TXN123456",
  "payment_method": "bank_transfer"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (invalid input)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

---

## Rate Limits

- Anonymous: 20 requests/minute
- Authenticated: 100 requests/minute
- Generation: 10 requests/minute

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642252800
```

---

## Webhooks (Coming Soon)

Configure webhooks to receive notifications:
- `job.completed` - When a generation job completes
- `job.failed` - When a generation job fails
- `invoice.paid` - When a payment is confirmed
