#!/usr/bin/env python3
"""
Manual Tenant Onboarding Script

Usage:
    python scripts/create_tenant.py

This script will guide you through creating a new tenant with:
- Tenant slug and name
- Contact information
- API key generation
- Branding configuration (colors, logo, welcome message)
- Channel configuration (web, SMS, voice, email)
- Pinecone namespace creation
"""

import sys
import os
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from core.database.base import SessionLocal
from core.database.models import Tenant
from core.backend.utils.security import generate_api_key, hash_api_key


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_success(text):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print error message."""
    print(f"✗ {text}")


def get_input(prompt, default=None, required=True):
    """Get user input with optional default."""
    if default:
        prompt = f"{prompt} [{default}]"
    prompt += ": "

    value = input(prompt).strip()

    if not value and default:
        return default

    if not value and required:
        print_error("This field is required!")
        return get_input(prompt.rstrip(": "), default, required)

    return value or None


def get_yes_no(prompt, default="y"):
    """Get yes/no input."""
    value = get_input(f"{prompt} (y/n)", default, required=False) or default
    return value.lower() in ['y', 'yes']


def slugify(text):
    """Convert text to slug format."""
    return text.lower().replace(" ", "-").replace("_", "-")


def create_tenant_interactive(db: Session):
    """Interactive tenant creation."""
    print_header("AgentEva Manual Tenant Onboarding")

    print("Let's create a new tenant. I'll walk you through the process.\n")

    # Step 1: Basic Information
    print_header("Step 1: Basic Information")

    company_name = get_input("Company name")
    suggested_slug = slugify(company_name)
    tenant_slug = get_input("Tenant slug (used in URLs/API)", suggested_slug)

    # Check if slug already exists
    existing = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if existing:
        print_error(f"Tenant with slug '{tenant_slug}' already exists!")
        return None

    contact_email = get_input("Contact email")
    contact_name = get_input("Contact name", required=False)

    # Step 2: Generate API Key
    print_header("Step 2: API Key Generation")

    prefix = tenant_slug[:3]
    api_key, api_key_hash = generate_api_key(prefix)

    print_success(f"Generated API key: {api_key}")
    print("⚠️  IMPORTANT: Save this key securely! It won't be shown again.\n")

    # Step 3: Branding Configuration
    print_header("Step 3: Branding Configuration")

    primary_color = get_input("Primary color (hex)", "#667eea", required=False)
    secondary_color = get_input("Secondary color (hex)", "#764ba2", required=False)
    welcome_message = get_input("Welcome message", "Hi! How can we help you today?", required=False)
    logo_url = get_input("Logo URL (optional)", required=False)
    widget_position = get_input("Widget position", "bottom-right", required=False)

    # Step 4: Channel Configuration
    print_header("Step 4: Channel Configuration")

    web_enabled = get_yes_no("Enable web chat?", "y")
    sms_enabled = get_yes_no("Enable SMS (Twilio)?", "n")
    voice_enabled = get_yes_no("Enable voice (Twilio/Vapi)?", "n")
    email_enabled = get_yes_no("Enable email (SendGrid)?", "n")

    sms_phone = None
    voice_phone = None
    support_email = None

    if sms_enabled:
        sms_phone = get_input("Twilio phone number for SMS (e.g., +15551234567)")

    if voice_enabled:
        voice_phone = get_input("Phone number for voice (e.g., +15551234567)")

    if email_enabled:
        support_email = get_input("Support email address")

    # Step 5: AI Configuration
    print_header("Step 5: AI Configuration")

    ai_model = get_input("OpenAI model", "gpt-4o-mini", required=False)
    temperature = get_input("Temperature (0.0-1.0)", "0.7", required=False)
    max_tokens = get_input("Max tokens", "500", required=False)

    custom_prompt = get_input("Custom system prompt (optional)", required=False)
    if not custom_prompt:
        custom_prompt = f"You are a helpful customer support assistant for {company_name}. Be friendly, concise, and accurate."

    # Build configuration
    config = {
        "branding": {
            "logo_url": logo_url or "",
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "company_name": company_name,
            "support_email": support_email or contact_email,
            "welcome_message": welcome_message,
            "widget_position": widget_position
        },
        "ai_config": {
            "model": ai_model,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "system_prompt": custom_prompt,
            "escalation_keywords": ["human", "speak to person", "talk to agent", "representative"]
        },
        "channels": {
            "web": {"enabled": web_enabled},
            "sms": {
                "enabled": sms_enabled,
                "phone_number": sms_phone or ""
            },
            "voice": {
                "enabled": voice_enabled,
                "phone_number": voice_phone or ""
            },
            "email": {
                "enabled": email_enabled,
                "support_email": support_email or ""
            }
        },
        "rate_limits": {
            "requests_per_minute": 60,
            "custom_limits": {}
        }
    }

    # Step 6: Confirmation
    print_header("Step 6: Confirmation")

    print("Review tenant details:")
    print(f"  Company Name: {company_name}")
    print(f"  Slug: {tenant_slug}")
    print(f"  Contact: {contact_name or 'N/A'} <{contact_email}>")
    print(f"  API Key: {api_key}")
    print(f"  Primary Color: {primary_color}")
    print(f"  Channels: Web={web_enabled}, SMS={sms_enabled}, Voice={voice_enabled}, Email={email_enabled}")
    print()

    if not get_yes_no("Create this tenant?", "y"):
        print("\nTenant creation cancelled.")
        return None

    # Create tenant
    try:
        tenant = Tenant(
            id=uuid4(),
            slug=tenant_slug,
            name=company_name,
            api_key=api_key,  # Store plaintext for backwards compatibility
            api_key_hash=api_key_hash,  # Store hash for security
            config=config,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        print_header("✓ Tenant Created Successfully!")

        print(f"""
Tenant Details:
  ID: {tenant.id}
  Slug: {tenant.slug}
  Name: {tenant.name}
  API Key: {api_key}

Pinecone Namespace: {tenant_slug}

Widget Embed Code:
<script src="http://127.0.0.1:8000/widget/widget.js"
        data-tenant="{tenant_slug}"
        data-api-key="{api_key}"></script>

API Endpoints:
  Chat: POST http://127.0.0.1:8000/api/{tenant_slug}/chat
  Config: GET http://127.0.0.1:8000/api/{tenant_slug}/config
  Knowledge: POST http://127.0.0.1:8000/api/{tenant_slug}/knowledge

Next Steps:
  1. Save the API key securely
  2. Upload knowledge base documents via API
  3. Test the chat widget
  4. Configure webhooks for SMS/Voice/Email if enabled

⚠️  Remember to create Pinecone namespace: {tenant_slug}
        """)

        return tenant

    except Exception as e:
        print_error(f"Failed to create tenant: {e}")
        db.rollback()
        return None


def list_tenants(db: Session):
    """List all existing tenants."""
    print_header("Existing Tenants")

    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()

    if not tenants:
        print("No tenants found.")
        return

    print(f"{'Slug':<20} {'Name':<30} {'Active':<10} {'Created':<20}")
    print("-" * 80)

    for tenant in tenants:
        active = "✓ Yes" if tenant.is_active else "✗ No"
        created = tenant.created_at.strftime("%Y-%m-%d %H:%M") if tenant.created_at else "N/A"
        print(f"{tenant.slug:<20} {tenant.name:<30} {active:<10} {created:<20}")

    print(f"\nTotal: {len(tenants)} tenant(s)")


def main():
    """Main entry point."""
    db = SessionLocal()

    try:
        print("\nAgentEva Tenant Management")
        print("\n1. Create new tenant")
        print("2. List existing tenants")
        print("3. Exit")

        choice = get_input("\nSelect option", "1")

        if choice == "1":
            create_tenant_interactive(db)
        elif choice == "2":
            list_tenants(db)
        else:
            print("Exiting...")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()