# AgentEva Portal

A production-ready multi-tenant AI-powered customer support platform. Each client gets isolated configuration, knowledge base, and analytics while sharing the same codebase.

## Features

- 🤖 **AI-Powered Chat**: OpenAI-powered conversational AI with context awareness
- 🏢 **Multi-Tenant Architecture**: Complete tenant isolation with custom configurations
- 📊 **Analytics & Insights**: Track conversations, resolution rates, and customer satisfaction
- 🎨 **Customizable Branding**: Per-tenant themes, colors, and styling
- 📚 **Knowledge Base**: Vector-based knowledge retrieval using Pinecone
- 🔄 **Smart Escalation**: Automatic escalation based on keywords, confidence, and conversation length
- 🔐 **Secure by Default**: API key authentication, rate limiting, and tenant isolation
- 📱 **Embeddable Widget**: Easy integration into any website

## Project Structure

```
AgentEvaPortal/
├── core/
│   ├── backend/              # FastAPI backend
│   │   ├── main.py          # Application entry point
│   │   ├── config.py        # Settings management
│   │   ├── requirements.txt # Python dependencies
│   │   ├── api/             # REST API endpoints
│   │   ├── services/        # Business logic
│   │   ├── models/          # Pydantic models
│   │   ├── middleware/      # Custom middleware
│   │   └── utils/           # Utilities
│   ├── frontend/            # Frontend applications
│   │   ├── widget/          # Embeddable chat widget
│   │   └── admin/           # Admin dashboard
│   ├── shared/              # Shared utilities
│   │   └── config_loader.py # Tenant config loader
│   └── database/            # Database layer
│       ├── base.py          # SQLAlchemy setup
│       └── models.py        # Database models
├── tenants/                 # Tenant configurations (gitignored secrets)
├── templates/               # Configuration templates
│   └── tenant_config.yaml  # Tenant config template
├── scripts/                 # Setup and utility scripts
│   ├── setup.sh            # Initial setup script
│   └── create_tenant.py    # Create new tenant
├── tests/                   # Test suites
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
└── docs/                    # Documentation
```

## Prerequisites

- **Python 3.11+** (required)
- **PostgreSQL** (for production) or SQLite (for development)
- **Redis** (for caching and rate limiting)
- **OpenAI API Key** (for AI responses)
- **Pinecone Account** (for vector knowledge base)

## Quick Start

### 1. Run Setup Script

```bash
# Make setup script executable (if not already)
chmod +x scripts/setup.sh

# Run setup
./scripts/setup.sh
```

This will:
- Check Python version
- Create virtual environment
- Install dependencies

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/ai_support_platform
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=ai-support-kb
JWT_SECRET=your-secret-key
```

### 3. Set Up Database

```bash
# Create PostgreSQL database
createdb ai_support_platform

# Run migrations (coming soon)
# alembic upgrade head
```

### 4. Create Your First Tenant

```bash
# Using the create_tenant script
python scripts/create_tenant.py \
  --name "Five Star Gulf Rentals" \
  --slug "five-star" \
  --domain "fivestargulfrentals.com"

# Or run interactively
python scripts/create_tenant.py
```

This creates:
- `tenants/five-star/config.yaml` - Configuration (safe to commit)
- `tenants/five-star/secrets.yaml` - API key (gitignored)
- `tenants/five-star/knowledge_base/` - Knowledge documents
- `tenants/five-star/README.md` - Usage instructions

### 5. Start Development Server

```bash
# Navigate to backend
cd core/backend

# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## API Usage

### Chat Endpoint

```bash
curl -X POST http://localhost:8000/api/{tenant-slug}/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "message": "What are your business hours?",
    "session_id": "optional-session-id"
  }'
```

### Get Tenant Configuration

```bash
curl http://localhost:8000/api/{tenant-slug}/config \
  -H "x-api-key: YOUR_API_KEY"
```

### Get Analytics

```bash
curl "http://localhost:8000/api/{tenant-slug}/analytics?days=30" \
  -H "x-api-key: YOUR_API_KEY"
```

## Tenant Configuration

Each tenant has a `config.yaml` with:

### Branding
- Colors (primary, secondary, accent)
- Logo and favicon URLs
- Font family and widget positioning

### AI Settings
- Model selection (gpt-4, gpt-3.5-turbo)
- Temperature, max tokens, and other parameters
- Custom system prompt
- Fallback responses

### Business Information
- Contact details (phone, email, website)
- Business hours by day
- Escalation rules (keywords, thresholds)

### Features
- Enable/disable chat, email, voice, SMS
- Analytics, knowledge base, file uploads
- Sentiment analysis, multilingual support

### Integrations
- CRM (Salesforce, HubSpot, Zendesk)
- Booking systems (Calendly, Acuity)
- Payment processors (Stripe, Square, PayPal)
- Email providers (SMTP, SendGrid, Mailgun)
- Webhooks for events

### Rate Limiting
- Messages per minute/hour/day
- Concurrent conversations limit

### Analytics
- Conversation and message tracking
- Resolution rate, response time goals
- CSAT targets
- Data retention policies

## Database Models

- **Tenant**: Organization/client with configuration
- **Conversation**: Chat session with metadata
- **Message**: Individual message in conversation
- **KnowledgeDoc**: Document in knowledge base
- **Analytics**: Aggregated daily metrics

All models use UUID primary keys and include proper indexes for tenant isolation.

## Development

### Code Structure

The platform follows a layered architecture:

1. **API Layer** (`core/backend/api/`): Route handlers, request/response models
2. **Service Layer** (`core/backend/services/`): Business logic (to be implemented)
3. **Database Layer** (`core/database/`): SQLAlchemy models and queries
4. **Shared Layer** (`core/shared/`): Configuration loading, utilities

### Adding New Features

1. Define database model in `core/database/models.py`
2. Create Pydantic models in `core/backend/models/`
3. Implement business logic in `core/backend/services/`
4. Add API endpoint in `core/backend/api/routes.py`
5. Update tenant config template if needed

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core

# Run specific test file
pytest tests/unit/test_config.py
```

### Code Quality

```bash
# Format code
black core/

# Lint code
ruff check core/

# Type checking
mypy core/
```

## Tenant Management

### Creating a Tenant

```bash
python scripts/create_tenant.py \
  --name "Company Name" \
  --slug "company-slug" \
  --domain "company.com"
```

### Tenant Directory Structure

```
tenants/company-slug/
├── config.yaml          # Configuration (safe to commit)
├── secrets.yaml         # API key (NEVER COMMIT)
├── README.md           # Usage instructions
├── knowledge_base/     # Knowledge documents
├── prompts/            # Custom prompts
├── uploads/            # User uploads (gitignored)
└── logs/               # Logs (gitignored)
```

### Security Best Practices

- ✅ `config.yaml` - Safe to commit (no secrets)
- ❌ `secrets.yaml` - Gitignored, contains API keys
- ❌ `uploads/`, `logs/` - Gitignored, may contain sensitive data

## Multi-Tenant Isolation

Every API request requires:
1. **Tenant ID** in URL path (`/api/{tenant_id}/...`)
2. **API Key** in `x-api-key` header

All database queries automatically filter by `tenant_id` to ensure isolation.

## Production Deployment

### Environment Variables

Set these in production:

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://...  # Use connection pooling
REDIS_URL=redis://...
LOG_LEVEL=WARNING
```

### Security Checklist

- [ ] Change JWT_SECRET to a strong random value
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS_ORIGINS for your domains only
- [ ] Set up database backups
- [ ] Enable rate limiting in reverse proxy
- [ ] Monitor logs for suspicious activity
- [ ] Regularly rotate API keys

### Scaling Considerations

- Use PostgreSQL with connection pooling (pgBouncer)
- Deploy Redis for caching and rate limiting
- Use CDN for static assets (widget, admin)
- Implement horizontal scaling with load balancer
- Monitor with Prometheus/Grafana

## Architecture

### Backend (Python/FastAPI)

- **Async/Await**: Non-blocking I/O for high performance
- **Type Safety**: Full type hints with Pydantic validation
- **Auto Documentation**: OpenAPI/Swagger at `/docs`
- **Error Handling**: Global exception handler with logging

### Database (PostgreSQL)

- **SQLAlchemy ORM**: Type-safe database queries
- **UUID Primary Keys**: Better security and distribution
- **Proper Indexes**: Optimized for tenant isolation queries
- **Migrations**: Alembic for schema management

### AI Integration

- **OpenAI**: GPT-4 for conversational AI
- **Pinecone**: Vector database for knowledge base
- **Embedding**: Context-aware responses from knowledge base

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with tests
4. Run code quality checks: `black`, `ruff`, `mypy`
5. Commit: `git commit -m "Add feature"`
6. Push: `git push origin feature-name`
7. Create a Pull Request

## License

[License information to be added]

## Support

For issues and questions:
- Open an issue on GitHub
- [Contact information to be added]