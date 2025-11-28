/**
 * Floating Chatbot Widget - AI Health Insurance Assistant
 * Loads on every page and provides instant help
 */

(function() {
    'use strict';
    
    // Configuration
    const CONFIG = {
        API_ENDPOINT: '/api/chat/query',
        FEEDBACK_ENDPOINT: '/api/chat/feedback',
        STATUS_ENDPOINT: '/api/chat/status',
        MAX_MESSAGES: 50,
        QUICK_REPLIES: [
            '💊 What are pre-existing conditions?',
            '📄 How do I file a claim?',
            '🏥 Network hospitals?',
            '💰 Compare plans?'
        ]
    };
    
    let conversationContext = [];
    let isOpen = false;
    
    // Create widget HTML
    function createWidget() {
        const widget = document.createElement('div');
        widget.className = 'chatbot-widget';
        widget.innerHTML = `
            <!-- Chat Button -->
            <button class="chatbot-button" id="chatbotToggle" aria-label="Open AI Assistant">
                <i class="fas fa-comments"></i>
            </button>
            
            <!-- Chat Window -->
            <div class="chatbot-window" id="chatbotWindow">
                <!-- Header -->
                <div class="chatbot-header">
                    <div class="chatbot-header-info">
                        <div class="chatbot-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div>
                            <div class="chatbot-title">AI Assistant</div>
                            <div class="chatbot-status">● Online</div>
                        </div>
                    </div>
                    <button class="chatbot-close" id="chatbotClose" aria-label="Close chat">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <!-- Quick Replies -->
                <div class="chatbot-quick-replies" id="chatbotQuickReplies"></div>
                
                <!-- Messages -->
                <div class="chatbot-messages" id="chatbotMessages">
                    <div class="chatbot-message assistant">
                        <div class="chatbot-message-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="chatbot-message-content">
                            👋 Hi! I'm your AI health insurance assistant. Ask me about:
                            <br><br>
                            • Insurance plans & coverage<br>
                            • Filing claims<br>
                            • Pre-existing conditions<br>
                            • Network hospitals<br>
                            <br>
                            <strong>How can I help you today?</strong>
                        </div>
                    </div>
                </div>
                
                <!-- Typing Indicator -->
                <div class="chatbot-typing" id="chatbotTyping">
                    <div class="chatbot-typing-dot"></div>
                    <div class="chatbot-typing-dot"></div>
                    <div class="chatbot-typing-dot"></div>
                </div>
                
                <!-- Input Area -->
                <div class="chatbot-input-area">
                    <div class="chatbot-input-wrapper">
                        <textarea 
                            id="chatbotInput" 
                            class="chatbot-input" 
                            placeholder="Ask a question..."
                            rows="1"
                        ></textarea>
                        <button id="chatbotSend" class="chatbot-send" aria-label="Send message">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(widget);
        initializeWidget();
    }
    
    // Initialize widget functionality
    function initializeWidget() {
        const toggle = document.getElementById('chatbotToggle');
        const close = document.getElementById('chatbotClose');
        const window = document.getElementById('chatbotWindow');
        const input = document.getElementById('chatbotInput');
        const send = document.getElementById('chatbotSend');
        const quickRepliesContainer = document.getElementById('chatbotQuickReplies');
        
        // Toggle chat window
        toggle.addEventListener('click', () => {
            isOpen = !isOpen;
            window.classList.toggle('active', isOpen);
            toggle.classList.toggle('active', isOpen);
            if (isOpen) {
                input.focus();
                loadQuickReplies();
            }
        });
        
        close.addEventListener('click', () => {
            isOpen = false;
            window.classList.remove('active');
            toggle.classList.remove('active');
        });
        
        // Auto-resize textarea
        input.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 80) + 'px';
        });
        
        // Send on Enter (Shift+Enter for new line)
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        send.addEventListener('click', sendMessage);
        
        // Load status
        checkStatus();
    }
    
    // Load quick reply buttons
    function loadQuickReplies() {
        const container = document.getElementById('chatbotQuickReplies');
        container.innerHTML = '';
        
        CONFIG.QUICK_REPLIES.forEach(text => {
            const btn = document.createElement('button');
            btn.className = 'chatbot-quick-reply';
            btn.textContent = text;
            btn.addEventListener('click', () => {
                document.getElementById('chatbotInput').value = text.replace(/^[^\s]+\s/, ''); // Remove emoji
                sendMessage();
            });
            container.appendChild(btn);
        });
    }
    
    // Check chatbot status
    async function checkStatus() {
        try {
            const resp = await fetch(CONFIG.STATUS_ENDPOINT);
            const data = await resp.json();
            
            if (data.status === 'operational' && data.index.total_docs > 0) {
                updateStatus('● Online', 'green');
            } else {
                updateStatus('● Limited', 'orange');
            }
        } catch (e) {
            console.warn('Chatbot status check failed:', e);
            updateStatus('● Offline', 'red');
        }
    }
    
    function updateStatus(text, color) {
        const statusEl = document.querySelector('.chatbot-status');
        if (statusEl) {
            statusEl.textContent = text;
            statusEl.style.color = color;
        }
    }
    
    // Add message to chat
    function addMessage(role, content, sources = null) {
        const messagesContainer = document.getElementById('chatbotMessages');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chatbot-message ${role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'chatbot-message-avatar';
        avatar.innerHTML = role === 'user' 
            ? '<i class="fas fa-user"></i>' 
            : '<i class="fas fa-robot"></i>';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'chatbot-message-content';
        
        // Format content (preserve line breaks, bold text)
        let formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        
        contentDiv.innerHTML = formattedContent;
        
        // Add sources if present
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'chatbot-sources';
            sourcesDiv.innerHTML = '<strong>📚 Sources:</strong>';
            
            sources.slice(0, 3).forEach(src => {
                const sourceItem = document.createElement('div');
                sourceItem.className = 'chatbot-source';
                sourceItem.innerHTML = `
                    <i class="fas fa-link"></i>
                    <span>${truncate(src.id, 30)}</span>
                    <span style="margin-left: auto; font-weight: 600;">${(src.score * 100).toFixed(0)}%</span>
                `;
                sourcesDiv.appendChild(sourceItem);
            });
            
            contentDiv.appendChild(sourcesDiv);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Limit message history
        const messages = messagesContainer.querySelectorAll('.chatbot-message');
        if (messages.length > CONFIG.MAX_MESSAGES) {
            messages[0].remove();
        }
    }
    
    // Send message
    async function sendMessage() {
        const input = document.getElementById('chatbotInput');
        const send = document.getElementById('chatbotSend');
        const typing = document.getElementById('chatbotTyping');
        
        const query = input.value.trim();
        if (!query) return;
        
        // Add user message
        addMessage('user', query);
        conversationContext.push({ role: 'user', text: query });
        
        // Clear input
        input.value = '';
        input.style.height = 'auto';
        
        // Show typing indicator
        typing.classList.add('active');
        send.disabled = true;
        
        try {
            // Detect page context from URL
            const path = window.location.pathname;
            let pageContext = null;
            if (path.includes('bill-buster')) pageContext = 'bill-buster';
            else if (path.includes('get-quote')) pageContext = 'get-quote';
            else if (path.includes('dashboard')) pageContext = 'dashboard';
            else if (path === '/') pageContext = 'home';
            
            // Get user ID if available (from session/cookie)
            let userId = null;
            try {
                // Try to get user ID from data attribute or meta tag
                const userIdEl = document.querySelector('[data-user-id]');
                if (userIdEl) userId = userIdEl.getAttribute('data-user-id');
            } catch (e) {
                // User not logged in, that's fine
            }
            
            const resp = await fetch(CONFIG.API_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    context: conversationContext.slice(-6),
                    page_context: pageContext,
                    user_id: userId,
                    top_k: 5
                })
            });
            
            if (!resp.ok) {
                throw new Error(`Server error: ${resp.status}`);
            }
            
            const data = await resp.json();
            
            // Add assistant response
            addMessage('assistant', data.answer, data.sources);
            conversationContext.push({ role: 'assistant', text: data.answer });
            
            // Show suggestions if provided
            if (data.suggestions && data.suggestions.length > 0) {
                showSuggestions(data.suggestions);
            }
            
        } catch (error) {
            console.error('Chat query failed:', error);
            addMessage('assistant', 
                `❌ Sorry, I encountered an error: ${error.message}. Please try again or contact support.`);
        } finally {
            typing.classList.remove('active');
            send.disabled = false;
            input.focus();
        }
    }
    
    // Show suggested questions
    function showSuggestions(suggestions) {
        const container = document.getElementById('chatbotQuickReplies');
        container.innerHTML = '<strong style="font-size: 12px; color: #666;">Suggested questions:</strong>';
        
        suggestions.slice(0, 4).forEach(text => {
            const btn = document.createElement('button');
            btn.className = 'chatbot-quick-reply';
            btn.textContent = text;
            btn.addEventListener('click', () => {
                document.getElementById('chatbotInput').value = text;
                sendMessage();
            });
            container.appendChild(btn);
        });
    }
    
    // Utility: Truncate text
    function truncate(text, maxLen) {
        return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
    }
    
    // Auto-open chatbot on certain pages (optional)
    function autoOpenOnPages() {
        const currentPath = window.location.pathname;
        const autoOpenPaths = ['/get-quote', '/dashboard'];
        
        if (autoOpenPaths.some(path => currentPath.includes(path))) {
            // Auto-open after 3 seconds on specific pages
            setTimeout(() => {
                if (!isOpen && !sessionStorage.getItem('chatbot_seen')) {
                    document.getElementById('chatbotToggle').click();
                    sessionStorage.setItem('chatbot_seen', 'true');
                }
            }, 3000);
        }
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            createWidget();
            autoOpenOnPages();
        });
    } else {
        createWidget();
        autoOpenOnPages();
    }
    
})();
