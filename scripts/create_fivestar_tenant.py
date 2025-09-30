#!/usr/bin/env python3
"""Create Five Star Gulf Rentals tenant."""

import sys
import os
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database.base import SessionLocal
from core.database.models import Tenant, TenantStatus
from core.backend.utils.security import generate_api_key, hash_api_key

def create_fivestar_tenant():
    """Create Five Star Gulf Rentals tenant."""
    db = SessionLocal()

    try:
        # Check if already exists
        existing = db.query(Tenant).filter(Tenant.slug == "fivestar").first()
        if existing:
            print(f"✓ Tenant 'fivestar' already exists")
            print(f"  API Key: {existing.api_key}")
            print(f"  Tenant ID: {existing.id}")
            return

        # Generate API key
        api_key, api_key_hash = generate_api_key("fiv")

        # Tenant configuration
        config = {
            "branding": {
                "logo_url": "",
                "primary_color": "#2563eb",
                "secondary_color": "#1e40af",
                "company_name": "Five Star Gulf Rentals",
                "support_email": "reservations@fivestargulfrentals.com",
                "welcome_message": "Welcome to Five Star Gulf Rentals! How can we help you plan your perfect beach vacation?",
                "widget_position": "bottom-right"
            },
            "ai_config": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 600,
                "system_prompt": "You are a friendly and knowledgeable vacation rental assistant for Five Star Gulf Rentals in Destin, Florida. Help guests with bookings, property information, local recommendations, and check-in procedures. Be warm, professional, and focus on creating memorable vacation experiences.",
                "escalation_keywords": ["speak to person", "human agent", "talk to someone", "manager", "complaint"]
            },
            "channels": {
                "web": {"enabled": True},
                "sms": {"enabled": False, "phone_number": ""},
                "voice": {"enabled": False, "phone_number": ""},
                "email": {"enabled": False, "support_email": "reservations@fivestargulfrentals.com"}
            },
            "rate_limits": {
                "requests_per_minute": 60,
                "custom_limits": {}
            }
        }

        # Create tenant
        tenant = Tenant(
            id=uuid4(),
            slug="fivestar",
            name="Five Star Gulf Rentals",
            api_key=api_key,
            api_key_hash=api_key_hash,
            config=config,
            status=TenantStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        print("\n" + "=" * 70)
        print("  ✓ Five Star Gulf Rentals tenant created successfully!")
        print("=" * 70)
        print(f"\nTenant Details:")
        print(f"  Slug: {tenant.slug}")
        print(f"  Name: {tenant.name}")
        print(f"  Tenant ID: {tenant.id}")
        print(f"  API Key: {api_key}")
        print(f"\nAPI Endpoints:")
        print(f"  Chat: POST /api/fivestar/chat")
        print(f"  Knowledge: POST /api/fivestar/knowledge")
        print(f"  Widget Config: GET /api/fivestar/widget/config")
        print("\n" + "=" * 70 + "\n")

    except Exception as e:
        print(f"✗ Error creating tenant: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_fivestar_tenant()
