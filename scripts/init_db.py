#!/usr/bin/env python3
"""Initialize database tables."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database.base import engine, Base
from core.database.models import Tenant, Conversation, Message, KnowledgeDoc, Analytics

def init_db():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")

if __name__ == "__main__":
    init_db()