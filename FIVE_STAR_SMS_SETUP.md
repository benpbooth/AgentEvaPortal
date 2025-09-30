# Five Star Gulf Rentals - SMS Integration Setup

## Overview
Your AgentEva AI assistant can now handle SMS messages via Twilio! Guests can text your business number and receive instant AI-powered responses.

---

## Step 1: Get Twilio Account Credentials

1. **Sign up for Twilio**: https://www.twilio.com/try-twilio
2. **Get your credentials** from the Twilio Console:
   - Account SID (starts with `AC...`)
   - Auth Token
   - Phone Number (e.g., `+15555555555`)

---

## Step 2: Configure Twilio Webhook

In your Twilio Console:

1. Go to **Phone Numbers** > **Manage** > **Active Numbers**
2. Click on your phone number
3. Scroll to **Messaging Configuration**
4. Under **A MESSAGE COMES IN**, configure:
   - **Webhook**: `https://YOUR-DOMAIN.com/api/fivestar/sms/webhook`
   - **HTTP Method**: `POST`
5. Click **Save**

**Important:** Replace `YOUR-DOMAIN.com` with your actual domain. For local testing, use ngrok:
```bash
ngrok http 8000
# Use the ngrok URL: https://abc123.ngrok.io/api/fivestar/sms/webhook
```

---

## Step 3: Add Twilio Credentials to Database

You need to add your Twilio credentials to the Five Star tenant configuration.

**Option A: Via Python Script** (Recommended)
```python
from core.database.base import SessionLocal
from core.database.models import Tenant

db = SessionLocal()
tenant = db.query(Tenant).filter(Tenant.slug == "fivestar").first()

# Update config with Twilio credentials
if tenant:
    config = tenant.config or {}
    config["twilio"] = {
        "account_sid": "AC...",  # Your Twilio Account SID
        "auth_token": "your_auth_token",  # Your Twilio Auth Token
        "phone_number": "+15555555555"  # Your Twilio Phone Number
    }
    tenant.config = config
    db.commit()
    print("Twilio credentials added!")

db.close()
```

**Option B: Via SQL**
```sql
UPDATE tenants
SET config = json_set(
    COALESCE(config, '{}'),
    '$.twilio',
    json_object(
        'account_sid', 'AC...',
        'auth_token', 'your_auth_token',
        'phone_number', '+15555555555'
    )
)
WHERE slug = 'fivestar';
```

---

## Step 4: Test the Integration

### Test SMS Flow:

1. **Send a text to your Twilio number**:
   ```
   "What are your check-in times?"
   ```

2. **You should receive an AI response within seconds**:
   ```
   "Check-in time is 4:00 PM and check-out time is 10:00 AM.
   We offer keyless entry - you'll receive detailed arrival
   instructions via email 3 days before check-in..."
   ```

3. **Check the dashboard** at http://YOUR-DOMAIN.com/dashboard/
   - You'll see the SMS conversation appear with `channel="sms"`
   - View full conversation history
   - See if escalation was triggered

### Test Questions:
- "Do you allow pets?"
- "What are the cancellation policies?"
- "What's fun to do in Destin?"
- "I need to speak with someone" (triggers escalation)

---

## How It Works

1. **Guest sends SMS** → Twilio receives it
2. **Twilio sends webhook** → Your AgentEva API
3. **AgentEva processes**:
   - Retrieves relevant knowledge from your docs
   - Generates AI response using GPT-4
   - Checks for escalation keywords
   - Saves conversation to database
4. **AI responds via TwiML** → Twilio sends SMS to guest
5. **Conversation appears in dashboard** → Your staff can monitor

---

## Features

✅ **Instant AI Responses** - Guests get answers 24/7
✅ **Knowledge Base Integration** - AI uses your policies, amenities, local info
✅ **Escalation Detection** - Automatically flags complex inquiries
✅ **Conversation History** - All SMS threads saved in dashboard
✅ **Multi-Channel** - SMS conversations appear alongside web chat

---

## Pricing (Twilio)

- **Phone Number**: ~$1/month
- **SMS**: $0.0075 per message sent/received (US)
- **Example**: 1,000 SMS conversations = ~$15/month

---

## Security Notes

⚠️ **Keep your Auth Token secure!** Never commit it to git or share publicly.
⚠️ **Use HTTPS** for your webhook URL (required by Twilio)
⚠️ **Consider adding Twilio signature validation** for production

---

## Troubleshooting

**Not receiving SMS responses?**
- Check Twilio webhook is configured correctly
- Verify your server is accessible (use ngrok for local testing)
- Check logs: `tail -f logs/app.log`

**AI responses are generic?**
- Ensure your knowledge base is populated
- Check tenant configuration

**Need Help?**
- Email: support@agenteva.com
- View logs: Check FastAPI logs for errors
- Test webhook: Use Twilio's webhook testing tool

---

## Next Steps

Once SMS is working:
1. ✅ Monitor conversations in dashboard
2. ✅ Add more knowledge base documents
3. ✅ Train staff on escalation workflow
4. ⏭️ Add voice integration (Vapi)
5. ⏭️ Add email integration (SendGrid)
