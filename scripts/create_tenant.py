#!/usr/bin/env python3
"""Script to create a new tenant configuration."""

import secrets
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import click
import yaml


def generate_api_key(slug: str) -> str:
    """
    Generate a secure API key for the tenant.

    Args:
        slug: Tenant slug (used as prefix)

    Returns:
        API key in format: {slug[:3]}_live_{random_token}
    """
    prefix = slug[:3].lower()
    token = secrets.token_urlsafe(32)
    return f"{prefix}_live_{token}"


def load_template() -> dict:
    """Load the tenant configuration template."""
    template_path = Path(__file__).parent.parent / "templates" / "tenant_config.yaml"

    if not template_path.exists():
        click.echo(f"❌ Error: Template not found at {template_path}", err=True)
        sys.exit(1)

    with open(template_path, "r") as f:
        return yaml.safe_load(f)


def create_tenant_directory(base_path: Path, slug: str) -> Path:
    """
    Create tenant directory structure.

    Args:
        base_path: Base tenants directory
        slug: Tenant slug

    Returns:
        Path to tenant directory
    """
    tenant_dir = base_path / slug
    tenant_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (tenant_dir / "knowledge_base").mkdir(exist_ok=True)
    (tenant_dir / "prompts").mkdir(exist_ok=True)
    (tenant_dir / "uploads").mkdir(exist_ok=True)
    (tenant_dir / "logs").mkdir(exist_ok=True)

    return tenant_dir


def save_config(tenant_dir: Path, config: dict) -> None:
    """Save tenant configuration to YAML file."""
    config_path = tenant_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
    click.echo(f"✓ Configuration saved to: {config_path}")


def save_secrets(tenant_dir: Path, api_key: str) -> None:
    """Save tenant secrets (API key) to gitignored file."""
    secrets_path = tenant_dir / "secrets.yaml"
    secrets_data = {
        "api_key": api_key,
        "created_at": datetime.utcnow().isoformat(),
        "note": "NEVER commit this file to version control!",
    }

    with open(secrets_path, "w") as f:
        yaml.dump(secrets_data, f, default_flow_style=False, sort_keys=False, indent=2)

    # Set restrictive permissions
    secrets_path.chmod(0o600)
    click.echo(f"✓ Secrets saved to: {secrets_path}")


def create_readme(tenant_dir: Path, name: str, slug: str, domain: str, api_key: str) -> None:
    """Create README file for tenant directory."""
    readme_path = tenant_dir / "README.md"
    content = f"""# {name}

**Tenant Slug:** `{slug}`
**Domain:** {domain}
**Created:** {datetime.utcnow().strftime("%Y-%m-%d")}

## Configuration

The tenant configuration is stored in `config.yaml`. This file contains:

- Branding (colors, logo, fonts)
- AI settings (model, temperature, system prompt)
- Business information (contact details, hours)
- Features and integrations
- Rate limiting and analytics

## API Key

The API key is stored in `secrets.yaml` (gitignored).

**API Key:** `{api_key}`

⚠️ **Keep this key secure!** Never commit it to version control.

## Directory Structure

```
{slug}/
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
curl -X POST http://localhost:8000/api/{slug}/chat \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: {api_key}" \\
  -d '{{"message": "Hello, I need help"}}'
```

### Get Tenant Configuration

```bash
curl http://localhost:8000/api/{slug}/config \\
  -H "x-api-key: {api_key}"
```

### Get Analytics

```bash
curl http://localhost:8000/api/{slug}/analytics?days=30 \\
  -H "x-api-key: {api_key}"
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
"""

    with open(readme_path, "w") as f:
        f.write(content)

    click.echo(f"✓ README created: {readme_path}")


@click.command()
@click.option(
    "--name",
    prompt="Tenant name",
    help="Full name of the tenant/organization",
)
@click.option(
    "--slug",
    prompt="Tenant slug (lowercase, no spaces)",
    help="URL-friendly identifier (e.g., 'five-star')",
)
@click.option(
    "--domain",
    prompt="Domain",
    help="Primary domain (e.g., 'example.com')",
)
@click.option(
    "--base-path",
    default="tenants",
    help="Base path for tenant directories",
)
def create_tenant(name: str, slug: str, domain: str, base_path: str):
    """
    Create a new tenant configuration.

    This script creates a new tenant directory with configuration files,
    generates an API key, and sets up the necessary subdirectories.
    """
    click.echo("")
    click.echo("=" * 50)
    click.echo("Creating New Tenant")
    click.echo("=" * 50)
    click.echo("")

    # Validate slug
    if not slug.replace("-", "").replace("_", "").isalnum():
        click.echo("❌ Error: Slug must contain only letters, numbers, hyphens, and underscores", err=True)
        sys.exit(1)

    slug = slug.lower()

    # Check if tenant already exists
    base_path_obj = Path(base_path)
    tenant_dir = base_path_obj / slug

    if tenant_dir.exists():
        click.echo(f"❌ Error: Tenant '{slug}' already exists at {tenant_dir}", err=True)
        sys.exit(1)

    # Load template
    click.echo("Loading configuration template...")
    template = load_template()

    # Fill in template variables
    template["tenant"]["slug"] = slug
    template["tenant"]["name"] = name
    template["tenant"]["domain"] = domain

    # Update system prompt with business name
    if "ai" in template and "system_prompt" in template["ai"]:
        template["ai"]["system_prompt"] = template["ai"]["system_prompt"].replace(
            "{business_name}", name
        )
        template["ai"]["system_prompt"] = template["ai"]["system_prompt"].replace(
            "{business_phone}", template["business"]["phone"]
        )
        template["ai"]["system_prompt"] = template["ai"]["system_prompt"].replace(
            "{business_email}", template["business"]["email"]
        )
        template["ai"]["system_prompt"] = template["ai"]["system_prompt"].replace(
            "{business_hours}", f"{template['business']['hours']['monday']} {template['business']['hours']['timezone']}"
        )

    # Update business info
    template["business"]["website"] = f"https://{domain}"

    click.echo("✓ Template loaded and configured")

    # Generate API key
    api_key = generate_api_key(slug)
    click.echo(f"✓ Generated API key: {api_key}")

    # Create tenant directory structure
    click.echo("Creating tenant directory...")
    tenant_dir = create_tenant_directory(base_path_obj, slug)
    click.echo(f"✓ Created: {tenant_dir}")

    # Save configuration
    click.echo("Saving configuration files...")
    save_config(tenant_dir, template)
    save_secrets(tenant_dir, api_key)
    create_readme(tenant_dir, name, slug, domain, api_key)

    click.echo("")
    click.echo("=" * 50)
    click.echo("✓ Tenant Created Successfully!")
    click.echo("=" * 50)
    click.echo("")
    click.echo(f"Name:     {name}")
    click.echo(f"Slug:     {slug}")
    click.echo(f"Domain:   {domain}")
    click.echo(f"Location: {tenant_dir}")
    click.echo(f"API Key:  {api_key}")
    click.echo("")
    click.echo("Next steps:")
    click.echo("")
    click.echo(f"1. Review and customize the configuration:")
    click.echo(f"   {tenant_dir}/config.yaml")
    click.echo("")
    click.echo(f"2. Add knowledge base documents to:")
    click.echo(f"   {tenant_dir}/knowledge_base/")
    click.echo("")
    click.echo(f"3. Test the API endpoint:")
    click.echo(f"   curl -X POST http://localhost:8000/api/{slug}/chat \\")
    click.echo(f"     -H 'x-api-key: {api_key}' \\")
    click.echo(f"     -H 'Content-Type: application/json' \\")
    click.echo(f"     -d '{{\"message\": \"Hello\"}}'")
    click.echo("")
    click.echo("⚠️  Keep your API key secure - it's stored in secrets.yaml (gitignored)")
    click.echo("")


if __name__ == "__main__":
    create_tenant()