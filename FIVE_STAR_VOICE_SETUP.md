# Five Star Gulf Rentals - Voice Integration Setup

## Overview
Your AgentEva AI assistant now supports voice calls via ElevenLabs Conversational AI! Guests can call your business number and speak with an AI-powered voice agent that accesses your knowledge base in real-time.

---

## Step 1: Get ElevenLabs Credentials

1. **Sign up for ElevenLabs**: https://elevenlabs.io/
2. **Create a Conversational AI agent** in the ElevenLabs dashboard
3. **Get your credentials**:
   - API Key (found in Settings > API Keys)
   - Agent ID (found in your agent's settings)

---

## Step 2: Add Credentials to Database

Run the provided Python script to add your ElevenLabs credentials to the Five Star tenant configuration.

```bash
# Edit the script with your credentials
nano scripts/add_elevenlabs_credentials.py

# Add your credentials:
ELEVENLABS_API_KEY = "your_api_key_here"
ELEVENLABS_AGENT_ID = "your_agent_id_here"

# Run the script
python3 scripts/add_elevenlabs_credentials.py
```

**Alternative: Via Python Console**
```python
from core.database.base import SessionLocal
from core.database.models import Tenant

db = SessionLocal()
tenant = db.query(Tenant).filter(Tenant.slug == "fivestar").first()

if tenant:
    config = tenant.config or {}
    config["elevenlabs"] = {
        "api_key": "your_api_key_here",
        "agent_id": "your_agent_id_here"
    }
    tenant.config = config
    db.commit()
    print("ElevenLabs credentials added!")

db.close()
```

---

## Step 3: Configure ElevenLabs Webhooks

In your ElevenLabs agent settings, configure the following webhooks:

### Knowledge Base Webhook
**Purpose**: Allows the voice agent to retrieve information from your knowledge base during calls.

- **URL**: `https://YOUR-DOMAIN.com/api/fivestar/voice/knowledge`
- **Method**: `POST`
- **Trigger**: When agent needs information

**Request Format**:
```json
{
  "query": "What are your check-in times?",
  "conversation_id": "conv_abc123",
  "caller_phone": "+15555555555"
}
```

**Response Format**:
```json
{
  "response": "Check-in time is 4:00 PM and check-out time is 10:00 AM...",
  "metadata": {
    "query": "What are your check-in times?",
    "confidence": 0.95,
    "documents_used": 3,
    "source": "agenteva_knowledge_base"
  }
}
```

### Conversation Logging Webhook
**Purpose**: Logs call transcripts to your dashboard after calls end.

- **URL**: `https://YOUR-DOMAIN.com/api/fivestar/voice/transcript`
- **Method**: `POST`
- **Trigger**: When call ends

**Request Format**:
```json
{
  "conversation_id": "conv_abc123",
  "caller_phone": "+15555555555",
  "duration_seconds": 180,
  "messages": [
    {
      "role": "user",
      "content": "What are your check-in times?",
      "timestamp": "2025-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Check-in time is 4:00 PM...",
      "timestamp": "2025-01-15T10:30:05Z"
    }
  ]
}
```

**Response Format**:
```json
{
  "success": true,
  "conversation_id": "uuid-here",
  "messages_saved": 12
}
```

---

## Step 4: Configure Your Phone Number

You have two options for phone integration:

### Option A: ElevenLabs Phone Number
- Purchase a phone number directly through ElevenLabs
- Connect it to your Conversational AI agent
- ElevenLabs handles all call routing

### Option B: Twilio + ElevenLabs
- Use your existing Twilio phone number
- Forward calls to ElevenLabs via TwiML
- More control over call flow

**For local testing**, use ngrok:
```bash
ngrok http 8000
# Use the ngrok URL in your webhook configuration
```

---

## Step 5: Test the Integration

### Test Flow:

1. **Call your phone number**
2. **Speak with the AI agent**:
   - "What are your check-in times?"
   - "Do you allow pets?"
   - "What's included in the rental?"
   - "I need to speak with someone" (triggers escalation)

3. **Verify knowledge base integration**:
   - Agent should access your knowledge base in real-time
   - Responses should be accurate and based on your documents

4. **Check the dashboard** at http://YOUR-DOMAIN.com/dashboard/
   - Conversation should appear with `channel="voice"`
   - Full transcript should be logged
   - Escalation status should be tracked

---

## How It Works

1. **Guest calls your number** → ElevenLabs receives call
2. **AI agent answers** → Begins conversation
3. **Agent needs information** → Calls your knowledge base webhook:
   - AgentEva retrieves relevant documents from Pinecone
   - Generates AI response using GPT-4
   - Returns answer in JSON format
4. **Agent speaks response** → Guest hears natural voice
5. **Call ends** → ElevenLabs sends transcript to your logging webhook:
   - AgentEva creates conversation with `channel="voice"`
   - Saves all messages to database
   - Updates dashboard in real-time
6. **Dashboard shows conversation** → Your staff can review calls

---

## Features

✅ **Real-Time Knowledge Access** - Agent retrieves information during calls
✅ **Natural Voice Conversation** - ElevenLabs' advanced voice AI
✅ **Full Transcript Logging** - All calls saved to dashboard
✅ **Multi-Channel Dashboard** - Voice calls appear alongside SMS and web chat
✅ **Escalation Detection** - Automatically flags calls needing human attention
✅ **Conversation History** - Complete call transcripts with timestamps

---

## ElevenLabs Pricing

- **Conversational AI**: Starting at $99/month
- **Voice Generation**: ~$0.30 per 1,000 characters
- **Phone Number** (optional): ~$1/month + per-minute rates
- **Example**: 100 calls averaging 3 minutes = ~$30-50/month

---

## Security Best Practices

⚠️ **Secure your API keys!** Never commit them to git or share publicly.
⚠️ **Use HTTPS** for all webhook URLs (required by ElevenLabs)
⚠️ **Validate webhook requests** in production environments
⚠️ **Monitor usage** to prevent abuse or unexpected costs

---

## Troubleshooting

**Agent not accessing knowledge base?**
- Check webhook URL is correct and accessible
- Verify your server is reachable (use ngrok for local testing)
- Check logs: `tail -f logs/app.log`

**Conversations not appearing in dashboard?**
- Verify transcript webhook is configured
- Check that conversation_id and caller_phone are included in request
- Check database for new conversations with `channel="voice"`

**Agent responses are generic?**
- Ensure knowledge base is populated with documents
- Check that tenant credentials are configured correctly
- Verify ChatService is generating responses properly

**Need Help?**
- Email: support@agenteva.com
- View API logs for detailed error messages
- Test webhooks using curl or Postman

---

## Example Webhook Test (Knowledge Base)

```bash
curl -X POST http://127.0.0.1:8000/api/fivestar/voice/knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are your check-in times?",
    "conversation_id": "test_conv_123",
    "caller_phone": "+15555555555"
  }'
```

**Expected Response**:
```json
{
  "response": "Check-in time is 4:00 PM and check-out time is 10:00 AM...",
  "metadata": {
    "query": "What are your check-in times?",
    "confidence": 0.95,
    "documents_used": 3,
    "source": "agenteva_knowledge_base"
  }
}
```

---

## Example Webhook Test (Transcript Logging)

```bash
curl -X POST http://127.0.0.1:8000/api/fivestar/voice/transcript \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test_conv_123",
    "caller_phone": "+15555555555",
    "duration_seconds": 180,
    "messages": [
      {
        "role": "user",
        "content": "What are your check-in times?",
        "timestamp": "2025-01-15T10:30:00Z"
      },
      {
        "role": "assistant",
        "content": "Check-in time is 4:00 PM and check-out time is 10:00 AM.",
        "timestamp": "2025-01-15T10:30:05Z"
      }
    ]
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "conversation_id": "uuid-here",
  "messages_saved": 2
}
```

---

## Next Steps

Once voice integration is working:
1. ✅ Monitor voice conversations in dashboard
2. ✅ Train your ElevenLabs agent with common scenarios
3. ✅ Add more knowledge base documents for better responses
4. ⏭️ Add email integration (SendGrid)
5. ⏭️ Build analytics dashboard for call insights
6. ⏭️ Add SMS notifications for escalated calls
