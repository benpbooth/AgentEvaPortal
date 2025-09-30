# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgentEva Portal is a production-ready multi-tenant AI-powered customer support platform built with Python/FastAPI. Each tenant gets isolated configuration, knowledge base, and analytics while sharing the same codebase. The platform provides OpenAI-powered conversational AI with vector-based knowledge retrieval using Pinecone.

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL (production) / SQLite (development)
- **Caching**: Redis
- **AI**: OpenAI GPT-4, Pinecone (vector database)
- **Authentication**: API key-based (per tenant)

## Key Architecture Concepts

### Multi-Tenant Architecture

**Critical**: Every database query MUST filter by `tenant_id` to ensure isolation.

The platform uses strict tenant isolation with:
- Separate configuration files in `tenants/{slug}/config.yaml`
- Per-tenant API keys stored in gitignored `secrets.yaml`
- Database models with `tenant_id` foreign keys
- URL-based tenant routing: `/api/{tenant_id}/...`
- Header-based authentication: `x-api-key` header

### Layer Structure

The codebase follows a clean architecture pattern:

**Backend (`core/backend/`):**
- `main.py` - FastAPI application entry point with middleware
- `config.py` - Pydantic Settings for environment configuration
- `api/routes.py` - REST API endpoints with Pydantic models
- `services/` - Business logic layer (to be implemented)
- `models/` - Pydantic validation models
- `middleware/` - FastAPI middleware (auth, logging, etc.)
- `utils/` - Shared utility functions

**Database (`core/database/`):**
- `base.py` - SQLAlchemy engine, session factory, and `get_db()` dependency
- `models.py` - SQLAlchemy ORM models (Tenant, Conversation, Message, KnowledgeDoc, Analytics)

**Shared (`core/shared/`):**
- `config_loader.py` - `TenantConfig` class for loading tenant YAML configs with dot notation

**Frontend (`core/frontend/`):**
- `admin/` - Admin dashboard (to be implemented)
- `widget/` - Embeddable chat widget (to be implemented)

### Database Models

All models use UUID primary keys with `default=uuid.uuid4`:
- **Tenant**: slug (unique), name, domain, config (JSON), status, api_key
- **Conversation**: tenant_id (FK), session_id, channel, resolution_status, escalated
- **Message**: conversation_id (FK), tenant_id (FK), role (enum), content
- **KnowledgeDoc**: tenant_id (FK), title, content, metadata (JSON), vector_id
- **Analytics**: tenant_id (FK), date, metrics (conversations, resolution rate, response time, CSAT)

## Development Commands

### Setup
```bash
# Run setup script (creates venv, installs deps)
./scripts/setup.sh

# Create virtual environment manually
cd core/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Development Server
```bash
cd core/backend
source venv/bin/activate
uvicorn main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Tenant Management
```bash
# Create new tenant (interactive)
python scripts/create_tenant.py

# Create tenant (non-interactive)
python scripts/create_tenant.py \
  --name "Company Name" \
  --slug "company-slug" \
  --domain "company.com"
```

### Testing
```bash
pytest                      # Run all tests
pytest --cov=core          # With coverage
pytest tests/unit/         # Unit tests only
pytest tests/integration/  # Integration tests only
```

### Code Quality
```bash
black core/                # Format code
ruff check core/           # Lint code
mypy core/                 # Type checking
```

## Configuration Management

### Environment Variables (.env)

Loaded via Pydantic Settings in `core/backend/config.py`:
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key
- `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, `PINECONE_INDEX_NAME`
- `JWT_SECRET`, `CORS_ORIGINS`, `LOG_LEVEL`

Access via: `from core.backend.config import get_settings; settings = get_settings()`

### Tenant Configuration

Each tenant has a YAML config in `tenants/{slug}/config.yaml` with:
- `branding` - Colors, logo, fonts, widget positioning
- `ai` - Model, temperature, system prompt, fallback responses
- `business` - Contact info, hours, escalation rules
- `features` - Enable/disable chat, email, voice, analytics, etc.
- `integrations` - CRM, booking, payment, webhooks
- `rate_limiting` - Per-minute/hour/day limits
- `analytics` - Tracking, goals, retention policies

Load config with:
```python
from core.shared.config_loader import TenantConfig
config = TenantConfig(tenant_id="five-star")
model = config.get("ai.model")  # Dot notation
branding = config.branding      # Property accessor
```

### Secrets Management

**CRITICAL**: API keys are stored in `tenants/{slug}/secrets.yaml` which is gitignored.

Never commit:
- `tenants/*/secrets.yaml` - API keys
- `tenants/*/uploads/` - User uploads
- `tenants/*/logs/` - Logs
- `.env` - Environment variables

## API Endpoints

All endpoints require:
1. Tenant slug in URL: `/api/{tenant_id}/...`
2. API key in header: `x-api-key: {api_key}`

### Current Endpoints

- `POST /api/{tenant_id}/chat` - Send chat message
- `GET /api/{tenant_id}/config` - Get tenant configuration
- `GET /api/{tenant_id}/analytics?days=30` - Get analytics

### Adding New Endpoints

1. Define Pydantic request/response models in `core/backend/api/routes.py`
2. Add route handler with `@router.{method}()` decorator
3. Use `verify_api_key()` dependency for authentication
4. Implement business logic in `core/backend/services/`
5. Always filter database queries by `tenant_id`

Example:
```python
@router.post("/{tenant_id}/endpoint", response_model=ResponseModel)
async def endpoint(
    tenant_id: str,
    request: RequestModel,
    x_api_key: Optional[str] = Header(None),
) -> ResponseModel:
    await verify_api_key(tenant_id, x_api_key)
    # Implement logic here
    return ResponseModel(...)
```

## Important Patterns

### Tenant Isolation (CRITICAL)

**Every database query MUST filter by tenant_id:**

```python
# Correct
conversations = db.query(Conversation).filter(
    Conversation.tenant_id == tenant_id
).all()

# WRONG - DO NOT DO THIS
conversations = db.query(Conversation).all()  # Leaks data across tenants!
```

### Configuration Loading

```python
# Load tenant config
config = TenantConfig(tenant_id)
system_prompt = config.get("ai.system_prompt")
escalation_keywords = config.get("business.escalation.keywords", [])

# Reload after changes
config.reload()
```

### Async/Await

Use async functions in FastAPI routes:
```python
async def route_handler(...):
    # Use await for async operations
    result = await some_async_function()
    return result
```

### Error Handling

Let FastAPI's global exception handler catch errors in production. For specific errors:
```python
from fastapi import HTTPException, status

if not found:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Resource not found"
    )
```

## Adding New Features

### Standard Flow

1. **Define database model** in `core/database/models.py`
   - Use UUID primary keys
   - Add `tenant_id` foreign key
   - Include timestamps (`created_at`, `updated_at`)
   - Add indexes for common queries

2. **Create Pydantic models** in `core/backend/models/` or inline in routes
   - Request models for input validation
   - Response models for output serialization

3. **Implement business logic** in `core/backend/services/`
   - Separate concerns from API layer
   - Make testable, reusable functions

4. **Add API endpoint** in `core/backend/api/routes.py`
   - Use proper HTTP methods (GET, POST, PUT, DELETE)
   - Include authentication
   - Add OpenAPI documentation (docstrings, descriptions)

5. **Update tenant config template** if needed (`templates/tenant_config.yaml`)

### Testing Strategy

- **Unit tests** (`tests/unit/`): Test individual functions, config loading, utilities
- **Integration tests** (`tests/integration/`): Test API endpoints end-to-end
- Use `pytest` fixtures for database setup, test tenants
- Mock external services (OpenAI, Pinecone) in tests

## Common Tasks

### Add New Tenant Configuration Field

1. Update `templates/tenant_config.yaml` with new field
2. Document in README.md tenant configuration section
3. Update `TenantConfig` properties in `core/shared/config_loader.py` if needed
4. Existing tenants won't break (default values via `config.get("key", default)`)

### Add New Database Model

1. Define in `core/database/models.py` with proper relationships
2. Create Alembic migration: `alembic revision --autogenerate -m "description"`
3. Review and edit migration if needed
4. Apply: `alembic upgrade head`

### Add New API Endpoint

1. Define request/response Pydantic models
2. Add route in `core/backend/api/routes.py`
3. Implement in service layer
4. Add integration test
5. Document in README.md API usage section

## Security Best Practices

- ✅ Always validate API keys via `verify_api_key()`
- ✅ Always filter database queries by `tenant_id`
- ✅ Use Pydantic for input validation
- ✅ Never commit `secrets.yaml` files
- ✅ Use environment variables for sensitive config
- ✅ Enable CORS only for trusted origins
- ✅ Use HTTPS in production
- ✅ Implement rate limiting (Redis-based)
- ✅ Log security events

## Production Deployment

### Environment Setup

- Set `ENVIRONMENT=production` to disable docs
- Use strong `JWT_SECRET`
- Configure proper `CORS_ORIGINS`
- Use connection pooling for PostgreSQL
- Set `LOG_LEVEL=WARNING` or `ERROR`

### Database

- Use PostgreSQL (not SQLite)
- Enable connection pooling (pgBouncer)
- Set up automated backups
- Run migrations: `alembic upgrade head`

### Monitoring

- Log to centralized logging (Datadog, CloudWatch)
- Monitor response times, error rates
- Set up alerts for failed API keys, high error rates
- Track tenant usage and quotas

## File Structure Reference

```
core/backend/
├── main.py              # FastAPI app, middleware, startup/shutdown
├── config.py            # Pydantic Settings (env vars)
├── requirements.txt     # Python dependencies
├── api/
│   └── routes.py       # API endpoints (chat, config, analytics)
├── services/           # Business logic (to implement)
├── models/             # Pydantic models (to implement)
├── middleware/         # Custom middleware (to implement)
└── utils/              # Utilities (to implement)

core/database/
├── base.py             # SQLAlchemy setup, get_db() dependency
└── models.py           # ORM models (Tenant, Conversation, Message, etc.)

core/shared/
└── config_loader.py    # TenantConfig class for YAML loading

tenants/{slug}/
├── config.yaml         # Tenant configuration (safe to commit)
├── secrets.yaml        # API keys (NEVER COMMIT - gitignored)
├── README.md           # Tenant-specific docs
├── knowledge_base/     # Documents for vector DB
├── prompts/            # Custom prompts
├── uploads/            # User files (gitignored)
└── logs/               # Logs (gitignored)
```