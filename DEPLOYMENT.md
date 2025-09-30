# AgentEva - Railway Deployment Guide

## Deploy to alphaworxsystems.com in 10 minutes

This guide will help you deploy AgentEva to Railway with PostgreSQL database and custom domain.

---

## Step 1: Push Code to GitHub

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

---

## Step 2: Create Railway Account

1. Go to https://railway.app/
2. Click "Login with GitHub"
3. Authorize Railway to access your GitHub repos

---

## Step 3: Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose `benpbooth/AgentEvaPortal`
4. Railway will start building automatically

---

## Step 4: Add PostgreSQL Database

1. In your Railway project dashboard, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will create a Postgres instance
4. **Important**: Copy the `DATABASE_URL` from the "Connect" tab

---

## Step 5: Configure Environment Variables

Click on your web service → "Variables" tab → Add these variables:

```bash
# Database (already provided by Railway)
DATABASE_URL=<automatically set by Railway>

# OpenAI
OPENAI_API_KEY=<your OpenAI API key>

# Pinecone
PINECONE_API_KEY=<your Pinecone API key>
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=agenteva-knowledge

# JWT Security (generate a random string)
JWT_SECRET=<generate random 32+ character string>

# Environment
ENVIRONMENT=production

# CORS
CORS_ORIGINS=https://alphaworxsystems.com,https://api.alphaworxsystems.com

# Server
HOST=0.0.0.0
PORT=$PORT
LOG_LEVEL=INFO
```

**To generate JWT_SECRET:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Step 6: Initialize Database

Once deployed, run this command in Railway's terminal:

1. Click on your service → "Deployments" tab
2. Click latest deployment → "View Logs"
3. Find the database connection and create tables

**Or run locally against Railway database:**

```bash
# Export Railway DATABASE_URL
export DATABASE_URL="<your railway postgres url>"

# Run database init script
python3 scripts/init_db.py
```

---

## Step 7: Configure Custom Domain

### Option A: Full domain (recommended)

1. In Railway, click your service → "Settings" → "Domains"
2. Click "Custom Domain"
3. Enter: `api.alphaworxsystems.com`
4. Railway will show DNS records to add

**Add to your DNS provider:**
```
Type: CNAME
Name: api
Value: <railway-provided-value>
```

5. Wait 5-10 minutes for DNS propagation
6. Railway will auto-provision SSL certificate

### Option B: Subdomain

Use Railway's auto-generated domain:
- `agenteva-portal-production.up.railway.app`

---

## Step 8: Deploy Dashboard

The dashboard is static HTML/JS/CSS, deploy it separately:

### Option A: Vercel (easiest)

1. Go to https://vercel.com/
2. Import the `dashboard/` folder
3. Set custom domain: `dashboard.alphaworxsystems.com`

### Option B: Railway Static Site

1. Create new Railway service
2. Set root directory to `dashboard/`
3. Add custom domain: `dashboard.alphaworxsystems.com`

### Update Dashboard Config

Edit `dashboard/dashboard.js`:

```javascript
const CONFIG = {
    apiUrl: 'https://api.alphaworxsystems.com',  // Your Railway API URL
    tenantId: 'fivestar',
    apiKey: 'fiv_live_5eVj2YdY7j6VY8l5Z0PijgiV6FwnGxQ9'
};
```

---

## Step 9: Test Deployment

### Test API Health

```bash
curl https://api.alphaworxsystems.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "production"
}
```

### Test Chat Endpoint

```bash
curl -X POST https://api.alphaworxsystems.com/api/fivestar/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: fiv_live_5eVj2YdY7j6VY8l5Z0PijgiV6FwnGxQ9" \
  -d '{
    "message": "What are your check-in times?",
    "session_id": "test-session"
  }'
```

### Test Dashboard

Visit: `https://dashboard.alphaworxsystems.com`

---

## Step 10: Configure Webhooks

### ElevenLabs Webhooks

Update your ElevenLabs agent with production URLs:

**Knowledge Base Webhook:**
```
https://api.alphaworxsystems.com/api/fivestar/voice/knowledge
```

**Transcript Logging Webhook:**
```
https://api.alphaworxsystems.com/api/fivestar/voice/transcript
```

### Twilio SMS Webhook (when ready)

```
https://api.alphaworxsystems.com/api/fivestar/sms/webhook
```

---

## Step 11: Embed Chat Widget

Add to your website (`alphaworxsystems.com`):

```html
<!-- Add before </body> -->
<div id="agenteva-widget"></div>
<script src="https://api.alphaworxsystems.com/widget/fivestar.js"></script>
<script>
  AgentEva.init({
    apiUrl: 'https://api.alphaworxsystems.com',
    tenantId: 'fivestar',
    position: 'bottom-right'
  });
</script>
```

---

## Monitoring & Logs

### View Logs in Railway

1. Go to your project dashboard
2. Click on service → "Deployments"
3. Click latest deployment → "View Logs"

### Monitor Performance

Railway provides:
- CPU usage
- Memory usage
- Request metrics
- Deployment history

---

## Cost Estimate

**Railway Free Trial:**
- $5 credit (good for ~1 month of testing)

**After trial (~$10-15/month):**
- Web Service: $5/month
- PostgreSQL: $5/month
- Bandwidth: ~$0-5/month

**External Services:**
- OpenAI API: Pay per use (~$10-50/month depending on usage)
- Pinecone: Free tier (100K vectors)
- ElevenLabs: Starting at $99/month

---

## Troubleshooting

### Build Fails

**Error: Missing requirements.txt**
- Make sure `requirements.txt` is committed to repo
- Check Railway build logs

### Database Connection Error

**Error: Could not connect to database**
- Verify `DATABASE_URL` is set correctly
- Check PostgreSQL service is running in Railway
- Make sure database tables are initialized

### CORS Errors

**Error: Blocked by CORS policy**
- Update `CORS_ORIGINS` environment variable
- Include all your domains (with https://)
- Redeploy after updating

### Widget Not Loading

**Error: Failed to load widget**
- Check API URL in widget code
- Verify tenant ID is correct
- Check browser console for errors

### Voice/SMS Webhooks Not Working

**Error: Webhook timeout**
- Check Railway service is running
- Verify webhook URLs use HTTPS
- Check logs for incoming requests

---

## Next Steps

Once deployed:

1. Test all endpoints (chat, voice, SMS)
2. Add Five Star's knowledge base documents
3. Configure Five Star's branding in dashboard
4. Share dashboard link with Five Star
5. Monitor usage and costs

---

## Migration to AgentEva.ai

When you're ready to move to production:

1. Export database from Railway:
   ```bash
   pg_dump $DATABASE_URL > backup.sql
   ```

2. Import to AgentEva.ai production database:
   ```bash
   psql $PRODUCTION_DATABASE_URL < backup.sql
   ```

3. Update all webhook URLs to agenteva.ai
4. Update widget embed code on client sites

---

## Support

- Railway Docs: https://docs.railway.app/
- Railway Discord: https://discord.gg/railway
- AgentEva Issues: Check logs in Railway dashboard
