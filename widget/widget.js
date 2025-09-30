/**
 * AgentEva Embeddable Chat Widget
 *
 * Usage:
 * <script src="https://yourdomain.com/widget.js"
 *         data-tenant="your-tenant-slug"
 *         data-api-key="your-api-key"></script>
 */

(function() {
    'use strict';

    // Configuration from script tag attributes
    const script = document.currentScript || document.querySelector('script[src*="widget.js"]');
    const config = {
        tenant: script.getAttribute('data-tenant') || 'demo',
        apiKey: script.getAttribute('data-api-key') || '',
        apiUrl: script.getAttribute('data-api-url') || 'http://127.0.0.1:8000/api',
        position: script.getAttribute('data-position') || 'bottom-right', // bottom-right, bottom-left, top-right, top-left
    };

    // Session management
    const SESSION_KEY = `agenteva_session_${config.tenant}`;
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
        sessionId = 'web_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem(SESSION_KEY, sessionId);
    }

    // State
    let isOpen = false;
    let isLoading = false;
    let messages = [];
    let widgetConfig = null;

    // Fetch widget configuration
    async function fetchWidgetConfig() {
        try {
            const response = await fetch(`${config.apiUrl}/${config.tenant}/widget/config`, {
                headers: {
                    'x-api-key': config.apiKey
                }
            });
            if (response.ok) {
                widgetConfig = await response.json();
                return widgetConfig;
            }
        } catch (error) {
            console.error('Failed to load widget config:', error);
        }
        // Return defaults if fetch fails
        return {
            branding: {
                primary_color: '#667eea',
                secondary_color: '#764ba2',
                company_name: 'Support',
                welcome_message: 'Hi! How can we help you today?',
                logo_url: ''
            }
        };
    }

    // API call helper
    async function sendMessage(message) {
        const response = await fetch(`${config.apiUrl}/${config.tenant}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': config.apiKey
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                context: { channel: 'widget' }
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    }

    // Create widget HTML
    function createWidget() {
        const cfg = widgetConfig || {};
        const branding = cfg.branding || {};
        const primaryColor = branding.primary_color || '#667eea';
        const companyName = branding.company_name || 'Support';
        const welcomeMessage = branding.welcome_message || 'Hi! How can we help you today?';

        const container = document.createElement('div');
        container.id = 'agenteva-widget';
        container.innerHTML = `
            <style>
                #agenteva-widget {
                    position: fixed;
                    ${config.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
                    ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                }

                #agenteva-widget * {
                    box-sizing: border-box;
                }

                .agenteva-button {
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, ${primaryColor} 0%, ${branding.secondary_color || '#764ba2'} 100%);
                    border: none;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: transform 0.2s, box-shadow 0.2s;
                }

                .agenteva-button:hover {
                    transform: scale(1.05);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
                }

                .agenteva-button svg {
                    width: 28px;
                    height: 28px;
                    fill: white;
                }

                .agenteva-chat-window {
                    position: absolute;
                    ${config.position.includes('bottom') ? 'bottom: 80px;' : 'top: 80px;'}
                    ${config.position.includes('right') ? 'right: 0;' : 'left: 0;'}
                    width: 380px;
                    height: 600px;
                    max-height: calc(100vh - 120px);
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
                    display: none;
                    flex-direction: column;
                    overflow: hidden;
                    animation: slideUp 0.3s ease-out;
                }

                @keyframes slideUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .agenteva-chat-window.open {
                    display: flex;
                }

                .agenteva-header {
                    background: linear-gradient(135deg, ${primaryColor} 0%, ${branding.secondary_color || '#764ba2'} 100%);
                    color: white;
                    padding: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }

                .agenteva-header-title {
                    font-size: 18px;
                    font-weight: 600;
                }

                .agenteva-close-btn {
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                    font-size: 24px;
                    line-height: 1;
                    padding: 0;
                    width: 24px;
                    height: 24px;
                }

                .agenteva-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    background: #f7f9fc;
                }

                .agenteva-message {
                    margin-bottom: 16px;
                    display: flex;
                    gap: 8px;
                    animation: messageSlide 0.3s ease-out;
                }

                @keyframes messageSlide {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .agenteva-message.user {
                    flex-direction: row-reverse;
                }

                .agenteva-message-bubble {
                    max-width: 75%;
                    padding: 12px 16px;
                    border-radius: 18px;
                    font-size: 14px;
                    line-height: 1.5;
                }

                .agenteva-message.assistant .agenteva-message-bubble {
                    background: white;
                    color: #333;
                    border-bottom-left-radius: 4px;
                }

                .agenteva-message.user .agenteva-message-bubble {
                    background: ${primaryColor};
                    color: white;
                    border-bottom-right-radius: 4px;
                }

                .agenteva-welcome {
                    background: white;
                    padding: 12px 16px;
                    border-radius: 18px;
                    border-bottom-left-radius: 4px;
                    font-size: 14px;
                    line-height: 1.5;
                    color: #333;
                    margin-bottom: 16px;
                    max-width: 75%;
                }

                .agenteva-input-container {
                    padding: 16px;
                    background: white;
                    border-top: 1px solid #e5e7eb;
                    display: flex;
                    gap: 8px;
                }

                .agenteva-input {
                    flex: 1;
                    border: 1px solid #e5e7eb;
                    border-radius: 24px;
                    padding: 10px 16px;
                    font-size: 14px;
                    outline: none;
                    transition: border-color 0.2s;
                }

                .agenteva-input:focus {
                    border-color: ${primaryColor};
                }

                .agenteva-send-btn {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: ${primaryColor};
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: opacity 0.2s;
                }

                .agenteva-send-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .agenteva-send-btn svg {
                    width: 20px;
                    height: 20px;
                    fill: white;
                }

                .agenteva-loading {
                    display: flex;
                    gap: 4px;
                    padding: 12px 16px;
                }

                .agenteva-loading-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #999;
                    animation: bounce 1.4s infinite ease-in-out both;
                }

                .agenteva-loading-dot:nth-child(1) {
                    animation-delay: -0.32s;
                }

                .agenteva-loading-dot:nth-child(2) {
                    animation-delay: -0.16s;
                }

                @keyframes bounce {
                    0%, 80%, 100% {
                        transform: scale(0);
                    }
                    40% {
                        transform: scale(1);
                    }
                }

                @media (max-width: 480px) {
                    .agenteva-chat-window {
                        width: calc(100vw - 40px);
                        height: calc(100vh - 120px);
                    }
                }
            </style>

            <button class="agenteva-button" id="agenteva-toggle">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
                </svg>
            </button>

            <div class="agenteva-chat-window" id="agenteva-chat">
                <div class="agenteva-header">
                    <div class="agenteva-header-title">${companyName}</div>
                    <button class="agenteva-close-btn" id="agenteva-close">&times;</button>
                </div>
                <div class="agenteva-messages" id="agenteva-messages">
                    <div class="agenteva-welcome">${welcomeMessage}</div>
                </div>
                <div class="agenteva-input-container">
                    <input
                        type="text"
                        class="agenteva-input"
                        id="agenteva-input"
                        placeholder="Type your message..."
                        autocomplete="off"
                    />
                    <button class="agenteva-send-btn" id="agenteva-send">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(container);

        // Event listeners
        document.getElementById('agenteva-toggle').addEventListener('click', toggleChat);
        document.getElementById('agenteva-close').addEventListener('click', toggleChat);
        document.getElementById('agenteva-send').addEventListener('click', handleSend);
        document.getElementById('agenteva-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleSend();
        });
    }

    function toggleChat() {
        isOpen = !isOpen;
        const chatWindow = document.getElementById('agenteva-chat');
        chatWindow.classList.toggle('open', isOpen);

        if (isOpen) {
            document.getElementById('agenteva-input').focus();
        }
    }

    function addMessage(role, content) {
        const messagesContainer = document.getElementById('agenteva-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `agenteva-message ${role}`;
        messageDiv.innerHTML = `
            <div class="agenteva-message-bubble">${escapeHtml(content)}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function showLoading() {
        const messagesContainer = document.getElementById('agenteva-messages');
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'agenteva-message assistant';
        loadingDiv.id = 'agenteva-loading-indicator';
        loadingDiv.innerHTML = `
            <div class="agenteva-loading">
                <div class="agenteva-loading-dot"></div>
                <div class="agenteva-loading-dot"></div>
                <div class="agenteva-loading-dot"></div>
            </div>
        `;
        messagesContainer.appendChild(loadingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function hideLoading() {
        const loadingIndicator = document.getElementById('agenteva-loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }

    async function handleSend() {
        const input = document.getElementById('agenteva-input');
        const message = input.value.trim();

        if (!message || isLoading) return;

        // Add user message
        addMessage('user', message);
        input.value = '';

        // Disable input while loading
        isLoading = true;
        input.disabled = true;
        document.getElementById('agenteva-send').disabled = true;

        showLoading();

        try {
            const response = await sendMessage(message);
            hideLoading();
            addMessage('assistant', response.message || response.response);
        } catch (error) {
            hideLoading();
            addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
            console.error('Chat error:', error);
        } finally {
            isLoading = false;
            input.disabled = false;
            document.getElementById('agenteva-send').disabled = false;
            input.focus();
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize widget when DOM is ready
    async function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // Fetch configuration
        await fetchWidgetConfig();

        // Create widget
        createWidget();

        console.log('AgentEva widget initialized for tenant:', config.tenant);
    }

    init();
})();