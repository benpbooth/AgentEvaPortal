"""
Script to add ElevenLabs credentials to Five Star tenant configuration.
Run this script to configure voice integration.
"""
from core.database.base import SessionLocal
from core.database.models import Tenant

# Replace these with your actual ElevenLabs credentials
ELEVENLABS_API_KEY = "your_elevenlabs_api_key_here"
ELEVENLABS_AGENT_ID = "your_elevenlabs_agent_id_here"

def add_elevenlabs_credentials():
    db = SessionLocal()

    try:
        # Get Five Star tenant
        tenant = db.query(Tenant).filter(Tenant.slug == "fivestar").first()

        if not tenant:
            print("❌ Five Star tenant not found!")
            return

        # Update config with ElevenLabs credentials
        config = tenant.config or {}
        config["elevenlabs"] = {
            "api_key": ELEVENLABS_API_KEY,
            "agent_id": ELEVENLABS_AGENT_ID
        }

        tenant.config = config
        db.commit()

        print("✅ ElevenLabs credentials added successfully!")
        print(f"   API Key: {ELEVENLABS_API_KEY[:20]}...")
        print(f"   Agent ID: {ELEVENLABS_AGENT_ID}")
        print("\nNext steps:")
        print("1. Configure ElevenLabs webhooks (see FIVE_STAR_VOICE_SETUP.md)")
        print("2. Test voice integration")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_elevenlabs_credentials()
