# Demo Company

**Tenant Slug:** `demo`
**Domain:** demo.com
**Created:** 2025-09-30

## Configuration

The tenant configuration is stored in `config.yaml`. This file contains:

- Branding (colors, logo, fonts)
- AI settings (model, temperature, system prompt)
- Business information (contact details, hours)
- Features and integrations
- Rate limiting and analytics

## API Key

The API key is stored in `secrets.yaml` (gitignored).

**API Key:** `dem_live_nUw5urvXzJvOuquM0cOh_NE8z1BzXTvJ_AcV_X-RDBA`

⚠️ **Keep this key secure!** Never commit it to version control.

## Directory Structure

```
demo/
├── config.yaml          # Main configuration (safe to commit)
├── secrets.yaml         # API keys and secrets (NEVER COMMIT)
├── README.md           # This file
├── knowledge_base/     # Knowledge base documents
├── prompts/            # Custom prompts and templates
├── uploads/            # User-uploaded files
└── logs/               # Tenant-specific logs
```

## Usage

### Making API Requests

```bash
curl -X POST http://localhost:8000/api/demo/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: dem_live_nUw5urvXzJvOuquM0cOh_NE8z1BzXTvJ_AcV_X-RDBA" \
  -d '{"message": "Hello, I need help"}'
```

### Get Tenant Configuration

```bash
curl http://localhost:8000/api/demo/config \
  -H "x-api-key: dem_live_nUw5urvXzJvOuquM0cOh_NE8z1BzXTvJ_AcV_X-RDBA"
```

### Get Analytics

```bash
curl http://localhost:8000/api/demo/analytics?days=30 \
  -H "x-api-key: dem_live_nUw5urvXzJvOuquM0cOh_NE8z1BzXTvJ_AcV_X-RDBA"
```

## Adding Knowledge Base Documents

1. Place documents in the `knowledge_base/` directory
2. Supported formats: PDF, TXT, MD, DOCX
3. Documents will be automatically indexed and embedded

## Customizing AI Behavior

Edit `config.yaml` to customize:

- System prompt (`ai.system_prompt`)
- AI model and parameters (`ai.model`, `ai.temperature`)
- Escalation rules (`business.escalation`)
- Response behavior

## Next Steps

1. Update branding in `config.yaml`
2. Customize the system prompt
3. Add knowledge base documents
4. Test the API endpoints
5. Integrate the widget into your website
