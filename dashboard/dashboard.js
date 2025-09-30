/**
 * Five Star Gulf Rentals - Agent Dashboard
 * Fetches and displays conversation data from the AgentEva API
 */

const CONFIG = {
    apiUrl: 'http://127.0.0.1:8000',
    tenantId: 'fivestar',
    apiKey: 'fiv_live_5eVj2YdY7j6VY8l5Z0PijgiV6FwnGxQ9'
};

let currentFilter = '';

// Initialize dashboard
async function init() {
    await Promise.all([
        loadStats(),
        loadConversations()
    ]);

    // Event listeners
    document.getElementById('status-filter').addEventListener('change', (e) => {
        currentFilter = e.target.value;
        loadConversations();
    });

    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadStats();
        loadConversations();
    });
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${CONFIG.apiUrl}/api/${CONFIG.tenantId}/dashboard/stats`, {
            headers: {
                'x-api-key': CONFIG.apiKey
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load stats');
        }

        const stats = await response.json();

        // Update stat cards
        document.getElementById('total-conversations').textContent = stats.total_conversations || 0;
        document.getElementById('active-conversations').textContent = stats.active_conversations || 0;
        document.getElementById('escalated-conversations').textContent = stats.escalated_conversations || 0;
        document.getElementById('resolved-conversations').textContent = stats.resolved_conversations || 0;
        document.getElementById('escalation-rate').textContent = `${(stats.escalation_rate * 100).toFixed(1)}%`;
        document.getElementById('total-messages').textContent = stats.total_messages || 0;

    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Failed to load statistics');
    }
}

// Load conversations list
async function loadConversations() {
    const list = document.getElementById('conversations-list');

    // Show loading
    list.innerHTML = '<div class="empty-state"><h3>Loading conversations...</h3></div>';

    try {
        const url = new URL(`${CONFIG.apiUrl}/api/${CONFIG.tenantId}/dashboard/conversations`);
        if (currentFilter) {
            url.searchParams.append('status', currentFilter);
        }

        const response = await fetch(url, {
            headers: {
                'x-api-key': CONFIG.apiKey
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load conversations');
        }

        const data = await response.json();
        const conversations = data.conversations || [];

        if (conversations.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <h3>No conversations found</h3>
                    <p>There are no conversations matching your filter.</p>
                </div>
            `;
            return;
        }

        // Render conversations
        list.innerHTML = conversations.map(conv => renderConversationCard(conv)).join('');

    } catch (error) {
        console.error('Error loading conversations:', error);
        list.innerHTML = `
            <div class="empty-state">
                <h3>Failed to load conversations</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Render conversation card
function renderConversationCard(conv) {
    const statusClass = conv.status.toLowerCase();
    const startedDate = new Date(conv.started_at).toLocaleString();

    return `
        <div class="conversation-card" onclick="viewConversation('${conv.id}')">
            <div class="conversation-header">
                <span class="conversation-id">Session: ${conv.session_id.substring(0, 8)}...</span>
                <span class="status-badge ${statusClass}">${conv.status}</span>
            </div>
            <div class="conversation-meta">
                <div class="meta-item">
                    <strong>Channel:</strong>
                    <span>${conv.channel}</span>
                </div>
                <div class="meta-item">
                    <strong>Messages:</strong>
                    <span>${conv.message_count}</span>
                </div>
                <div class="meta-item">
                    <strong>Started:</strong>
                    <span>${startedDate}</span>
                </div>
                ${conv.escalated ? '<div class="meta-item"><strong>ESCALATED</strong></div>' : ''}
            </div>
        </div>
    `;
}

// View conversation details
async function viewConversation(conversationId) {
    const modal = document.getElementById('conversation-modal');
    const messagesContainer = document.getElementById('modal-messages');

    // Show modal with loading
    modal.classList.add('active');
    messagesContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #6b7280;">Loading messages...</div>';

    try {
        const response = await fetch(`${CONFIG.apiUrl}/api/${CONFIG.tenantId}/dashboard/conversations/${conversationId}`, {
            headers: {
                'x-api-key': CONFIG.apiKey
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load conversation');
        }

        const conversation = await response.json();

        // Update modal header info
        document.getElementById('modal-session-id').textContent = conversation.session_id;
        document.getElementById('modal-channel').textContent = conversation.channel;

        const statusBadge = document.getElementById('modal-status');
        statusBadge.textContent = conversation.status;
        statusBadge.className = `status-badge ${conversation.status.toLowerCase()}`;

        document.getElementById('modal-started').textContent = new Date(conversation.started_at).toLocaleString();

        // Render messages
        if (conversation.messages && conversation.messages.length > 0) {
            messagesContainer.innerHTML = conversation.messages.map(msg => renderMessage(msg)).join('');
        } else {
            messagesContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #6b7280;">No messages in this conversation.</div>';
        }

    } catch (error) {
        console.error('Error loading conversation:', error);
        messagesContainer.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #ef4444;">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    }
}

// Render message
function renderMessage(msg) {
    const time = new Date(msg.created_at).toLocaleString();
    const metadataHtml = msg.metadata && Object.keys(msg.metadata).length > 0
        ? `<div class="message-metadata">
            ${Object.entries(msg.metadata).map(([key, value]) =>
                `<span><strong>${key}:</strong> ${JSON.stringify(value)}</span>`
            ).join(' &nbsp;•&nbsp; ')}
           </div>`
        : '';

    return `
        <div class="message ${msg.role}">
            <div class="message-header">
                <span class="message-role">${msg.role}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-content">${escapeHtml(msg.content)}</div>
            ${metadataHtml}
        </div>
    `;
}

// Close modal
function closeModal() {
    document.getElementById('conversation-modal').classList.remove('active');
}

// Helper: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper: Show error
function showError(message) {
    console.error(message);
    // Could add toast notification here
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('conversation-modal');
    if (e.target === modal) {
        closeModal();
    }
});

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
