# AgentEva Chat Widget

Embeddable AI-powered customer support widget for your website.

## Quick Start

Add this single line to your website's HTML:

```html
<script src="http://127.0.0.1:8000/widget/widget.js"
        data-tenant="demo"
        data-api-key="dem_live_nUw5urvXzJvOuquM0cOh_NE8z1BzXTvJ_AcV_X-RDBA"></script>
```

That's it! The chat bubble will appear in the bottom-right corner.

## View Demo

Open the demo page to see the widget in action:

```bash
# From the widget directory
open demo.html
# Or visit: file:///path/to/widget/demo.html
```

Or serve it via Python:

```bash
cd widget
python3 -m http.server 3000
# Visit: http://localhost:3000/demo.html
```

## Configuration Options

### Required Parameters

- `data-tenant`: Your tenant slug (e.g., "demo", "acme")
- `data-api-key`: Your API key for authentication

### Optional Parameters

- `data-position`: Widget position - `bottom-right` (default), `bottom-left`, `top-right`, `top-left`
- `data-api-url`: API base URL (default: `http://127.0.0.1:8000/api`)

### Example

```html
<script src="http://127.0.0.1:8000/widget/widget.js"
        data-tenant="acme"
        data-api-key="acm_live_..."
        data-position="bottom-left"
        data-api-url="https://api.yourdomain.com/api"></script>
```

## Features

- **🎨 Automatic Branding**: Pulls colors, logo, and welcome message from your tenant config
- **💬 Real-time Chat**: Instant AI responses powered by GPT-4
- **📚 Knowledge Base**: Automatically retrieves relevant context from your docs
- **📱 Mobile Responsive**: Works perfectly on all devices
- **🔒 Secure**: API key authentication and rate limiting
- **💾 Session Persistence**: Conversation history saved in browser localStorage

## Customizing Branding

Update your tenant branding via API or database:

```json
{
  "branding": {
    "primary_color": "#667eea",
    "secondary_color": "#764ba2",
    "company_name": "Your Company",
    "welcome_message": "Hi! How can we help?",
    "logo_url": "https://your-domain.com/logo.png",
    "widget_position": "bottom-right"
  }
}
```

The widget automatically fetches these settings from `GET /api/{tenant}/widget/config`.

## Files

- `widget.js` - Main widget code (self-contained, no dependencies)
- `demo.html` - Demo page showing integration
- `README.md` - This file

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Production Deployment

### 1. Update API URL

Change the default API URL in your script tag:

```html
<script src="https://your-domain.com/widget/widget.js"
        data-tenant="your-tenant"
        data-api-key="your_api_key"
        data-api-url="https://your-domain.com/api"></script>
```

### 2. Enable CORS

Make sure your backend allows requests from client domains:

```python
# In core/backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://client1.com", "https://client2.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Serve widget.js

The widget is automatically served at `/widget/widget.js` by the FastAPI backend.

## Troubleshooting

### Widget doesn't appear

1. Check browser console for errors (F12)
2. Verify API key is correct
3. Ensure backend is running and accessible
4. Check CORS settings

### Can't send messages

1. Verify tenant_id exists in database
2. Check API key authentication
3. Ensure knowledge base has documents
4. Check backend logs for errors

## API Endpoints Used

- `GET /api/{tenant}/widget/config` - Fetch branding config
- `POST /api/{tenant}/chat` - Send chat messages

## Next Steps

- Add file upload support
- Implement typing indicators
- Add conversation export
- Create mobile app SDK
- Add webhook notifications