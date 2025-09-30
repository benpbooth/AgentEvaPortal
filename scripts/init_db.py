#!/usr/bin/env python3
"""Initialize database tables and seed demo tenant with branding config."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database.base import engine, Base, SessionLocal
from core.database.models import Tenant, Conversation, Message, KnowledgeDoc, Analytics
from core.backend.utils.security import hash_api_key

def init_db():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")

def seed_demo_tenant():
    """Create or update demo tenant with default branding configuration and hash API key."""
    from datetime import datetime
    from uuid import uuid4

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "demo").first()

        # Default config
        default_config = {
            "branding": {
                "logo_url": "",
                "primary_color": "#667eea",
                "secondary_color": "#764ba2",
                "company_name": "Demo Company",
                "support_email": "support@democompany.com",
                "welcome_message": "Hi! How can we help you today?",
                "widget_position": "bottom-right"
            },
            "ai_config": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 500,
                "system_prompt": "You are a helpful customer support assistant.",
                "escalation_keywords": ["human", "speak to person", "agent", "representative"]
            },
            "channels": {
                "web": {"enabled": True},
                "sms": {"enabled": False, "phone_number": ""},
                "voice": {"enabled": False, "phone_number": ""},
                "email": {"enabled": False, "support_email": ""}
            },
            "rate_limits": {
                "requests_per_minute": 60,
                "custom_limits": {}
            }
        }

        if tenant:
            # Update existing tenant
            if tenant.api_key and not tenant.api_key_hash:
                tenant.api_key_hash = hash_api_key(tenant.api_key)
                print(f"✓ Hashed API key for demo tenant")

            tenant.config = default_config
            db.commit()
            print("✓ Demo tenant branding config updated!")
        else:
            # Create new demo tenant
            api_key = "dem_live_nUw5urvXzJvOuquM0cOh_NE8z1BzXTvJ_AcV_X-RDBA"
            api_key_hash = hash_api_key(api_key)

            from core.database.models import TenantStatus
            tenant = Tenant(
                id=uuid4(),
                slug="demo",
                name="Demo Company",
                api_key=api_key,
                api_key_hash=api_key_hash,
                config=default_config,
                status=TenantStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tenant)
            db.commit()
            print("✓ Demo tenant created successfully!")
            print(f"  API Key: {api_key}")
    finally:
        db.close()

if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(f"Error during table creation: {e}")
        pass  # Tables might already exist

    seed_demo_tenant()