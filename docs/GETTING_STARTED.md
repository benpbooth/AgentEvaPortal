# Getting Started with AgentEva Portal

This guide will help you set up and run the AgentEva Portal on your local machine.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or higher** installed
- **PostgreSQL** installed and running (or use SQLite for development)
- **Redis** installed and running (optional for development)
- **OpenAI API key** (get one at https://platform.openai.com)
- **Pinecone account** (sign up at https://www.pinecone.io)

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd AgentEvaPortal

# Run the setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Check your Python version
- Create a virtual environment in `core/backend/venv/`
- Install all Python dependencies

## Step 2: Configure Environment

```bash
# Copy the environment template
cp .env.example .env

# Edit the .env file with your credentials
nano .env  # or use your preferred editor
```

### Required Environment Variables

```bash
# Database (use SQLite for quick start)
DATABASE_URL=sqlite:///./dev.db
# Or PostgreSQL for production-like setup
# DATABASE_URL=postgresql://user:password@localhost:5432/ai_support_platform

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Pinecone
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=ai-support-kb

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET=your-secret-key-here

# Development settings
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Step 3: Set Up Database (PostgreSQL)

If using PostgreSQL:

```bash
# Create the database
createdb ai_support_platform

# Run migrations (when available)
# cd core/backend
# source venv/bin/activate
# alembic upgrade head
```

If using SQLite, it will be created automatically.

## Step 4: Create Your First Tenant

```bash
# Interactive mode
python scripts/create_tenant.py

# Or provide all details upfront
python scripts/create_tenant.py \
  --name "Five Star Gulf Rentals" \
  --slug "five-star" \
  --domain "fivestargulfrentals.com"
```

This will create:
- `tenants/five-star/` directory
- `config.yaml` with default configuration
- `secrets.yaml` with a generated API key
- `knowledge_base/`, `prompts/`, `uploads/`, `logs/` subdirectories
- `README.md` with usage instructions

**Save the API key!** You'll need it to make API requests.

## Step 5: Start the Development Server

```bash
# Navigate to backend
cd core/backend

# Activate virtual environment
source venv/bin/activate

# Start the server
uvicorn main:app --reload
```

The server will start at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Step 6: Test the API

### Using curl

```bash
# Replace {slug} with your tenant slug and {api_key} with your API key
curl -X POST http://localhost:8000/api/five-star/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: fiv_live_..." \
  -d '{
    "message": "Hello, what are your business hours?"
  }'
```

### Using the Interactive Docs

1. Open http://localhost:8000/docs
2. Click on the `/api/{tenant_id}/chat` endpoint
3. Click "Try it out"
4. Fill in the tenant_id and API key
5. Enter your message
6. Click "Execute"

## Step 7: Customize Your Tenant

Edit the configuration file:

```bash
nano tenants/five-star/config.yaml
```

Key sections to customize:

### Branding
```yaml
branding:
  primary_color: "#007bff"
  logo_url: "https://yourcompany.com/logo.png"
  widget_position: "bottom-right"
```

### AI Behavior
```yaml
ai:
  model: "gpt-4"  # or gpt-3.5-turbo
  temperature: 0.7
  system_prompt: |
    You are a helpful assistant for Five Star Gulf Rentals...
```

### Business Info
```yaml
business:
  phone: "+1-555-0100"
  email: "support@fivestargulfrentals.com"
  hours:
    monday: "09:00-17:00"
    # ... etc
```

The configuration is automatically reloaded when you save changes.

## Step 8: Add Knowledge Base Documents

Place documents in your tenant's knowledge base:

```bash
# Add documents
cp your-faq.pdf tenants/five-star/knowledge_base/
cp policies.txt tenants/five-star/knowledge_base/
```

Supported formats:
- PDF (.pdf)
- Text files (.txt)
- Markdown (.md)
- Word documents (.docx)

**Note**: Vector embedding implementation is coming soon. For now, documents are stored but not yet searchable.

## Common Development Tasks

### View Logs

```bash
# Server logs appear in the terminal
# Or check log level in .env
LOG_LEVEL=DEBUG  # For more verbose logging
```

### Run Tests

```bash
cd core/backend
source venv/bin/activate
pytest
```

### Format Code

```bash
black core/
```

### Lint Code

```bash
ruff check core/
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
uvicorn main:app --reload --port 8001
```

### Database Connection Error

Check your DATABASE_URL in `.env`:
- For SQLite: Use relative path `sqlite:///./dev.db`
- For PostgreSQL: Ensure PostgreSQL is running and credentials are correct

### API Key Not Working

Make sure:
1. You're using the correct API key from `tenants/{slug}/secrets.yaml`
2. The `x-api-key` header is set
3. The tenant slug in the URL matches your tenant

### Import Errors

Ensure you're in the correct directory and virtual environment is activated:

```bash
cd core/backend
source venv/bin/activate
python -c "import fastapi; print('OK')"
```

## Next Steps

- Explore the [API documentation](http://localhost:8000/docs)
- Read the main [README.md](../README.md) for architecture details
- Check [CLAUDE.md](../CLAUDE.md) for development patterns
- Implement custom business logic in `core/backend/services/`
- Build the embeddable widget in `core/frontend/widget/`
- Create the admin dashboard in `core/frontend/admin/`

## Getting Help

- Open an issue on GitHub
- Check the documentation in `docs/`
- Review example tenant configurations in `templates/`

Happy coding! 🚀