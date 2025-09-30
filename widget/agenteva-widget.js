/**
 * AgentEva Chat Widget
 * Embeddable AI-powered chat widget for customer support
 *
 * Usage:
 * <script src="https://your-domain.com/widget/agenteva-widget.js"></script>
 * <script>
 *   AgentEva.init({
 *     apiUrl: 'https://your-api.com',
 *     tenantId: 'your-tenant-slug',
 *     apiKey: 'your-api-key'
 *   });
 * </script>
 */

(function() {
  'use strict';

  // Widget configuration
  let config = {
    apiUrl: '',
    tenantId: '',
    apiKey: '',
    position: 'bottom-right',
    primaryColor: '#2563eb',
    welcomeMessage: 'Hi! How can we help you today?'
  };

  let sessionId = null;
  let isOpen = false;
  let isLoading = false;
  let conversationHistory = [];

  // Generate or retrieve session ID
  function getSessionId() {
    if (sessionId) return sessionId;

    const stored = localStorage.getItem('agenteva_session_id');
    if (stored) {
      sessionId = stored;
      return sessionId;
    }

    sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('agenteva_session_id', sessionId);
    return sessionId;
  }

  // Create widget HTML
  function createWidget() {
    const widgetHTML = `
      <style>
        #agenteva-widget * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }

        #agenteva-widget {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          position: fixed;
          ${config.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
          ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
          z-index: 999999;
        }

        #agenteva-button {
          width: 60px;
          height: 60px;
          border-radius: 30px;
          background: ${config.primaryColor};
          border: none;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }

        #agenteva-button:hover {
          transform: scale(1.05);
          box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }

        #agenteva-button svg {
          width: 28px;
          height: 28px;
          fill: white;
        }

        #agenteva-chat {
          display: none;
          position: fixed;
          ${config.position.includes('bottom') ? 'bottom: 90px;' : 'top: 90px;'}
          ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
          width: 380px;
          height: 600px;
          max-height: calc(100vh - 120px);
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.12);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        #agenteva-chat.open {
          display: flex;
        }

        #agenteva-header {
          background: ${config.primaryColor};
          color: white;
          padding: 16px 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        #agenteva-header h3 {
          font-size: 16px;
          font-weight: 600;
          margin: 0;
        }

        #agenteva-close {
          background: none;
          border: none;
          color: white;
          font-size: 24px;
          cursor: pointer;
          padding: 0;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        #agenteva-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          background: #f9fafb;
        }

        .agenteva-message {
          margin-bottom: 16px;
          animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .agenteva-message-user {
          text-align: right;
        }

        .agenteva-message-bubble {
          display: inline-block;
          padding: 10px 14px;
          border-radius: 12px;
          max-width: 80%;
          word-wrap: break-word;
        }

        .agenteva-message-user .agenteva-message-bubble {
          background: ${config.primaryColor};
          color: white;
        }

        .agenteva-message-assistant .agenteva-message-bubble {
          background: white;
          color: #1f2937;
          box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .agenteva-welcome {
          text-align: center;
          padding: 20px;
          color: #6b7280;
        }

        #agenteva-input-container {
          padding: 16px;
          background: white;
          border-top: 1px solid #e5e7eb;
          display: flex;
          gap: 8px;
        }

        #agenteva-input {
          flex: 1;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          padding: 10px 12px;
          font-size: 14px;
          outline: none;
          font-family: inherit;
        }

        #agenteva-input:focus {
          border-color: ${config.primaryColor};
        }

        #agenteva-send {
          background: ${config.primaryColor};
          color: white;
          border: none;
          border-radius: 8px;
          padding: 10px 16px;
          cursor: pointer;
          font-weight: 500;
          transition: opacity 0.2s;
        }

        #agenteva-send:hover:not(:disabled) {
          opacity: 0.9;
        }

        #agenteva-send:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .agenteva-typing {
          display: inline-block;
          padding: 10px 14px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .agenteva-typing span {
          display: inline-block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #9ca3af;
          margin: 0 2px;
          animation: typing 1.4s infinite;
        }

        .agenteva-typing span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .agenteva-typing span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
          }
          30% {
            transform: translateY(-10px);
          }
        }

        @media (max-width: 480px) {
          #agenteva-chat {
            width: calc(100vw - 40px);
            height: calc(100vh - 120px);
          }
        }
      </style>

      <div id="agenteva-widget">
        <button id="agenteva-button" aria-label="Open chat">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 3 .97 4.29L2 22l5.71-.97C9 21.64 10.46 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm0 18c-1.38 0-2.68-.28-3.87-.78l-.28-.12-2.89.49.49-2.89-.12-.28C4.78 14.68 4.5 13.38 4.5 12c0-4.14 3.36-7.5 7.5-7.5s7.5 3.36 7.5 7.5-3.36 7.5-7.5 7.5z"/>
          </svg>
        </button>

        <div id="agenteva-chat">
          <div id="agenteva-header">
            <h3>Chat with us</h3>
            <button id="agenteva-close" aria-label="Close chat">&times;</button>
          </div>

          <div id="agenteva-messages">
            <div class="agenteva-welcome">
              <p>${config.welcomeMessage}</p>
            </div>
          </div>

          <div id="agenteva-input-container">
            <input
              type="text"
              id="agenteva-input"
              placeholder="Type your message..."
              autocomplete="off"
            />
            <button id="agenteva-send">Send</button>
          </div>
        </div>
      </div>
    `;

    const container = document.createElement('div');
    container.innerHTML = widgetHTML;
    document.body.appendChild(container.firstElementChild);

    attachEventListeners();
  }

  // Attach event listeners
  function attachEventListeners() {
    const button = document.getElementById('agenteva-button');
    const closeBtn = document.getElementById('agenteva-close');
    const sendBtn = document.getElementById('agenteva-send');
    const input = document.getElementById('agenteva-input');

    button.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);
    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // Toggle chat window
  function toggleChat() {
    isOpen = !isOpen;
    const chat = document.getElementById('agenteva-chat');
    const button = document.getElementById('agenteva-button');

    if (isOpen) {
      chat.classList.add('open');
      button.style.display = 'none';
      document.getElementById('agenteva-input').focus();
    } else {
      chat.classList.remove('open');
      button.style.display = 'flex';
    }
  }

  // Send message
  async function sendMessage() {
    const input = document.getElementById('agenteva-input');
    const message = input.value.trim();

    if (!message || isLoading) return;

    // Add user message to UI
    addMessage(message, 'user');
    input.value = '';

    // Show typing indicator
    showTyping();
    isLoading = true;
    document.getElementById('agenteva-send').disabled = true;

    try {
      const response = await fetch(`${config.apiUrl}/api/${config.tenantId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': config.apiKey
        },
        body: JSON.stringify({
          message: message,
          session_id: getSessionId()
        })
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();

      // Remove typing indicator
      hideTyping();

      // Add assistant response
      addMessage(data.message, 'assistant');

    } catch (error) {
      console.error('AgentEva Error:', error);
      hideTyping();
      addMessage('Sorry, I\'m having trouble connecting. Please try again.', 'assistant');
    } finally {
      isLoading = false;
      document.getElementById('agenteva-send').disabled = false;
      input.focus();
    }
  }

  // Add message to chat
  function addMessage(text, role) {
    const messagesContainer = document.getElementById('agenteva-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `agenteva-message agenteva-message-${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'agenteva-message-bubble';
    bubble.textContent = text;

    messageDiv.appendChild(bubble);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Store in history
    conversationHistory.push({ role, text });
  }

  // Show typing indicator
  function showTyping() {
    const messagesContainer = document.getElementById('agenteva-messages');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'agenteva-typing';
    typingDiv.className = 'agenteva-message agenteva-message-assistant';
    typingDiv.innerHTML = '<div class="agenteva-typing"><span></span><span></span><span></span></div>';
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Hide typing indicator
  function hideTyping() {
    const typing = document.getElementById('agenteva-typing');
    if (typing) typing.remove();
  }

  // Load widget configuration from API
  async function loadConfig() {
    try {
      const response = await fetch(`${config.apiUrl}/api/${config.tenantId}/widget/config`, {
        headers: {
          'x-api-key': config.apiKey
        }
      });

      if (response.ok) {
        const data = await response.json();

        // Update config with branding
        if (data.branding) {
          config.primaryColor = data.branding.primary_color || config.primaryColor;
          config.welcomeMessage = data.branding.welcome_message || config.welcomeMessage;
          config.position = data.branding.widget_position || config.position;
        }
      }
    } catch (error) {
      console.warn('AgentEva: Could not load widget config, using defaults');
    }
  }

  // Initialize widget
  async function init(options) {
    if (!options.apiUrl || !options.tenantId || !options.apiKey) {
      console.error('AgentEva: Missing required configuration');
      return;
    }

    config = { ...config, ...options };

    // Load branding config
    await loadConfig();

    // Create widget when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', createWidget);
    } else {
      createWidget();
    }
  }

  // Export public API
  window.AgentEva = {
    init: init
  };
})();
