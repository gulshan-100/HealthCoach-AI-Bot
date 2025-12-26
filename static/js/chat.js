/**
 * AI Health Coach - Chat Interface JavaScript
 * 
 * Features:
 * - Streaming responses for real-time AI replies
 * - WhatsApp-style UI with typing indicators
 * - Auto-scrolling and message history loading
 * - Double-tick read receipts
 */

class ChatInterface {
    constructor() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messageForm = document.getElementById('messageForm');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.micButton = document.getElementById('micButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.loadingOlder = document.getElementById('loadingOlder');
        this.charCount = document.getElementById('charCount');
        
        this.messages = [];
        this.oldestMessageId = null;
        this.hasMoreMessages = true;
        this.isLoadingMessages = false;
        this.isSending = false;
        this.isRecording = false;
        this.isSpeaking = false;
        this.voiceMode = false;  // Track if user is in voice conversation mode
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.currentAudio = null;
        this.username = null;
        this.usernameModal = null;
        
        this.init();
    }
    
    init() {
        // Check for username
        this.checkUsername();
        
        // Set up event listeners
        this.messageForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.messageInput.addEventListener('input', () => this.handleInputChange());
        this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.messagesContainer.addEventListener('scroll', () => this.handleScroll());
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
        
        // Voice input
        if (this.micButton) {
            this.micButton.addEventListener('click', () => this.toggleVoiceInput());
        }
        
        // Initialize media recorder for voice input
        this.initMediaRecorder();
        
        // Username form
        const usernameForm = document.getElementById('usernameForm');
        if (usernameForm) {
            usernameForm.addEventListener('submit', (e) => this.handleUsernameSubmit(e));
        }
        
        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }
    }
    
    /**
     * Get headers with username for API requests
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.username) {
            headers['X-Username'] = this.username;
        }
        
        return headers;
    }
    
    /**
     * Check if username exists, show modal if not
     */
    checkUsername() {
        this.username = localStorage.getItem('ai_health_coach_username');
        
        if (!this.username) {
            // Show username modal
            const modalElement = document.getElementById('usernameModal');
            this.usernameModal = new bootstrap.Modal(modalElement);
            this.usernameModal.show();
            
            // Focus on username input
            modalElement.addEventListener('shown.bs.modal', () => {
                document.getElementById('usernameInput').focus();
            });
        } else {
            // Load messages if username exists
            this.loadMessages();
            this.updateUserDisplay();
            this.messageInput.focus();
        }
    }
    
    /**
     * Handle username form submission
     */
    handleUsernameSubmit(e) {
        e.preventDefault();
        
        const username = document.getElementById('usernameInput').value.trim();
        const name = document.getElementById('nameInput').value.trim();
        const ageInput = document.getElementById('ageInput').value;
        const age = ageInput ? parseInt(ageInput) : null;
        const gender = document.getElementById('genderInput').value;
        const goalsInput = document.getElementById('goalsInput').value.trim();
        
        // Validate required fields
        if (!username) {
            alert('Username is required');
            return;
        }
        
        if (!name) {
            alert('Name is required');
            return;
        }
        
        if (!age || age < 1 || age > 120) {
            alert('Please enter a valid age between 1 and 120');
            return;
        }
        
        // Parse health goals
        const health_goals = goalsInput ? goalsInput.split(',').map(g => g.trim()).filter(g => g) : [];
        
        // Create user data object
        const userData = {
            username,
            name,
            age,
            gender: gender || undefined,
            health_goals: health_goals.length > 0 ? health_goals : undefined
        };
        
        this.setUsername(userData);
    }
    
    /**
     * Send username to server
     */
    async setUsername(userData) {
        // Validate username
        const username = userData.username.toLowerCase();
        
        const usernamePattern = /^[a-z0-9_-]+$/;
        if (!username || !usernamePattern.test(username)) {
            alert('Username must contain only letters, numbers, hyphens and underscores');
            return;
        }
        
        if (username.length < 3) {
            alert('Username must be at least 3 characters long');
            return;
        }
        
        this.username = username;
        localStorage.setItem('ai_health_coach_username', username);
        
        try {
            // Send complete user data to backend
            await fetch('/api/profile/onboard', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(userData)
            });
            
            // Close modal and reload messages
            const modal = bootstrap.Modal.getInstance(document.getElementById('usernameModal'));
            if (modal) {
                modal.hide();
            }
            
            // Clear existing messages and load new user's messages
            this.messages = [];
            this.messagesContainer.innerHTML = '';
            this.hasMoreMessages = true;
            this.oldestMessageId = null;
            
            this.updateUserDisplay();
            this.loadMessages();
        } catch (error) {
            console.error('Error setting username:', error);
            alert('Failed to create account. Please try again.');
            return;
        }
    }
    
    /**
     * Logout and allow username change
     */
    logout() {
        if (confirm('Are you sure you want to logout? This will clear your current session and allow you to login with a different username.')) {
            // Clear username from localStorage
            localStorage.removeItem('ai_health_coach_username');
            this.username = null;
            
            // Clear all messages from UI
            this.messages = [];
            this.messagesContainer.innerHTML = '';
            this.hasMoreMessages = true;
            this.oldestMessageId = null;
            
            // Clear username input
            document.getElementById('usernameInput').value = '';
            
            // Show username modal
            const usernameModal = new bootstrap.Modal(document.getElementById('usernameModal'));
            usernameModal.show();
        }
    }
    
    /**
     * Update user display in header
     */
    updateUserDisplay() {
        const userNameDisplay = document.getElementById('userNameDisplay');
        if (userNameDisplay && this.username) {
            userNameDisplay.textContent = this.username;
        }
    }
    
    /**
     * Load messages from the server
     */
    async loadMessages(beforeId = null) {
        if (this.isLoadingMessages || (!this.hasMoreMessages && beforeId)) {
            return;
        }
        
        this.isLoadingMessages = true;
        
        if (beforeId) {
            this.loadingOlder.classList.remove('d-none');
        }
        
        try {
            const url = beforeId 
                ? `/api/messages?limit=20&before_id=${beforeId}`
                : '/api/messages?limit=20';
            
            const headers = {};
            if (this.username) {
                headers['X-Username'] = this.username;
            }
            
            const response = await fetch(url, { headers });
            const data = await response.json();
            
            if (data.success) {
                const newMessages = data.data.messages;
                this.hasMoreMessages = data.data.has_more;
                
                if (newMessages.length > 0) {
                    if (beforeId) {
                        // Prepend older messages
                        this.messages = [...newMessages, ...this.messages];
                        this.renderOlderMessages(newMessages);
                    } else {
                        // Initial load
                        this.messages = newMessages;
                        this.renderMessages();
                        this.scrollToBottom(false);
                    }
                    
                    // Update oldest message ID
                    this.oldestMessageId = newMessages[0].message_id;
                }
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        } finally {
            this.isLoadingMessages = false;
            this.loadingOlder.classList.add('d-none');
        }
    }
    
    /**
     * Render all messages
     */
    renderMessages() {
        this.messagesContainer.innerHTML = '';
        this.messages.forEach(msg => this.addMessageToDOM(msg, false));
    }
    
    /**
     * Render older messages (prepend)
     */
    renderOlderMessages(messages) {
        const scrollHeightBefore = this.messagesContainer.scrollHeight;
        const scrollTopBefore = this.messagesContainer.scrollTop;
        
        const fragment = document.createDocumentFragment();
        messages.forEach(msg => {
            const messageEl = this.createMessageElement(msg);
            fragment.appendChild(messageEl);
        });
        
        this.messagesContainer.insertBefore(fragment, this.messagesContainer.firstChild);
        
        // Maintain scroll position
        const scrollHeightAfter = this.messagesContainer.scrollHeight;
        this.messagesContainer.scrollTop = scrollTopBefore + (scrollHeightAfter - scrollHeightBefore);
    }
    
    /**
     * Create a message element
     */
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;
        messageDiv.dataset.messageId = message.message_id;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        // Format message content
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = this.formatMessage(message.content);
        bubble.appendChild(content);
        
        // Add timestamp with ticks
        const meta = document.createElement('div');
        meta.className = 'message-meta';
        meta.innerHTML = `
            <span class="message-time">${this.formatTime(message.created_at)}</span>
            ${message.role === 'user' ? '<span class="message-ticks">✓✓</span>' : ''}
        `;
        bubble.appendChild(meta);
        
        messageDiv.appendChild(bubble);
        
        return messageDiv;
    }
    
    /**
     * Create an empty assistant message element for streaming
     */
    createStreamingMessageElement() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        messageDiv.id = 'streaming-message';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.id = 'streaming-content';
        bubble.appendChild(content);
        
        const meta = document.createElement('div');
        meta.className = 'message-meta';
        meta.innerHTML = `<span class="message-time">${this.formatTime(new Date().toISOString())}</span>`;
        bubble.appendChild(meta);
        
        messageDiv.appendChild(bubble);
        
        return messageDiv;
    }
    
    /**
     * Add message to DOM
     */
    addMessageToDOM(message, animate = true) {
        const messageEl = this.createMessageElement(message);
        
        if (!animate) {
            messageEl.style.animation = 'none';
        }
        
        this.messagesContainer.appendChild(messageEl);
    }
    
    /**
     * Format message content
     */
    formatMessage(content) {
        if (!content) return '';
        
        // Escape HTML
        const div = document.createElement('div');
        div.textContent = content;
        let formatted = div.innerHTML;
        
        // Convert newlines to <br>
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Convert **bold** to <strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert bullet points
        formatted = formatted.replace(/^- (.+)$/gm, '• $1');
        
        return formatted;
    }
    
    /**
     * Format timestamp
     */
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        // If today, show time
        if (diff < 24 * 60 * 60 * 1000 && date.getDate() === now.getDate()) {
            return date.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit',
                hour12: true 
            });
        }
        
        // If yesterday
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        if (date.getDate() === yesterday.getDate() && 
            date.getMonth() === yesterday.getMonth() &&
            date.getFullYear() === yesterday.getFullYear()) {
            return 'Yesterday ' + date.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit',
                hour12: true 
            });
        }
        
        // Otherwise show date
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }
    
    /**
     * Handle form submission with streaming
     */
    async handleSubmit(e) {
        e.preventDefault();
        
        const content = this.messageInput.value.trim();
        
        if (!content || this.isSending) {
            return;
        }
        
        // Clear input immediately
        const messageContent = content;
        this.messageInput.value = '';
        this.updateCharCount();
        this.autoResizeTextarea();
        
        this.isSending = true;
        this.sendButton.disabled = true;
        
        // Add user message immediately
        const userMessage = {
            message_id: 'temp-' + Date.now(),
            role: 'user',
            content: messageContent,
            created_at: new Date().toISOString()
        };
        this.messages.push(userMessage);
        this.addMessageToDOM(userMessage);
        this.scrollToBottom();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/messages/stream', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ content: messageContent })
            });
            
            if (!response.ok) {
                throw new Error('Failed to send message');
            }
            
            // Hide typing, show streaming message
            this.hideTypingIndicator();
            
            // Create streaming message element
            const streamingEl = this.createStreamingMessageElement();
            this.messagesContainer.appendChild(streamingEl);
            const contentEl = document.getElementById('streaming-content');
            
            // Read the stream - show text IMMEDIATELY as it arrives
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';
            let messageData = null;
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'chunk') {
                                fullContent += data.content;
                                // Update DOM immediately for every chunk
                                contentEl.innerHTML = this.formatMessage(fullContent) + '<span class="cursor">|</span>';
                                this.scrollToBottom();
                            } else if (data.type === 'done') {
                                messageData = data;
                                // Final update - remove cursor
                                contentEl.innerHTML = this.formatMessage(fullContent);
                            } else if (data.type === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (parseError) {
                            // Skip invalid JSON
                        }
                    }
                }
            }
            
            // Replace streaming element with final message
            const streamingMessage = document.getElementById('streaming-message');
            if (streamingMessage && messageData) {
                streamingMessage.remove();
                
                const finalMessage = {
                    message_id: messageData.message_id,
                    role: 'assistant',
                    content: fullContent,
                    created_at: messageData.created_at || new Date().toISOString()
                };
                this.messages.push(finalMessage);
                this.addMessageToDOM(finalMessage);
                
                // Speak the response if in voice mode
                if (this.voiceMode) {
                    this.speakText(fullContent);
                }
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            
            // Remove streaming element if exists
            const streamingMessage = document.getElementById('streaming-message');
            if (streamingMessage) streamingMessage.remove();
            
            // Show error message
            this.showError('Failed to get response. Please try again.');
        } finally {
            this.isSending = false;
            this.sendButton.disabled = false;
            this.messageInput.focus();
            this.scrollToBottom();
        }
    }
    
    /**
     * Handle input change
     */
    handleInputChange() {
        this.updateCharCount();
        
        // Enable/disable send button
        const hasContent = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasContent || this.isSending;
    }
    
    /**
     * Handle keyboard shortcuts
     */
    handleKeyDown(e) {
        // Submit on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleSubmit(e);
        }
    }
    
    /**
     * Handle scroll for loading older messages
     */
    handleScroll() {
        const scrollTop = this.messagesContainer.scrollTop;
        
        // If scrolled near top, load older messages
        if (scrollTop < 200 && this.hasMoreMessages && !this.isLoadingMessages) {
            this.loadMessages(this.oldestMessageId);
        }
    }
    
    /**
     * Auto-resize textarea
     */
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        const newHeight = Math.min(this.messageInput.scrollHeight, 120);
        this.messageInput.style.height = newHeight + 'px';
    }
    
    /**
     * Update character count
     */
    updateCharCount() {
        const count = this.messageInput.value.length;
        this.charCount.textContent = `${count}/2000`;
        
        if (count > 1900) {
            this.charCount.style.color = '#dc3545';
        } else {
            this.charCount.style.color = '#999';
        }
    }
    
    /**
     * Scroll to bottom of messages
     */
    scrollToBottom(smooth = true) {
        requestAnimationFrame(() => {
            this.messagesContainer.scrollTo({
                top: this.messagesContainer.scrollHeight,
                behavior: smooth ? 'smooth' : 'auto'
            });
        });
    }
    
    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        this.typingIndicator.classList.remove('d-none');
        this.scrollToBottom();
    }
    
    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        this.typingIndicator.classList.add('d-none');
    }
    
    /**
     * Show error message
     */
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message assistant';
        errorDiv.innerHTML = `
            <div class="message-bubble error-bubble">
                <div class="message-content">⚠️ ${message}</div>
            </div>
        `;
        
        this.messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();
    }
    
    /**
     * Initialize media recorder for voice input using OpenAI Whisper
     */
    async initMediaRecorder() {
        try {
            // Check for browser support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                console.log('Media recording not supported in this browser');
                if (this.micButton) {
                    this.micButton.style.display = 'none';
                }
                return;
            }
        } catch (error) {
            console.error('Error initializing media recorder:', error);
        }
    }
    
    /**
     * Toggle voice input recording
     */
    async toggleVoiceInput() {
        // If speaking, stop speech
        if (this.isSpeaking) {
            this.stopSpeaking();
            return;
        }

        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    /**
     * Start recording audio
     */
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.audioChunks = [];
            this.mediaRecorder = new MediaRecorder(stream);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = async () => {
                // Create audio blob
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
                
                // Send to server for transcription and response
                await this.processVoiceInput(audioBlob);
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            
            if (this.micButton) {
                this.micButton.classList.add('recording');
                this.micButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
            }
            this.messageInput.placeholder = '🎤 Listening...';
            
        } catch (error) {
            console.error('Error starting recording:', error);
            this.showError('Could not access microphone. Please check permissions.');
        }
    }
    
    /**
     * Stop voice recording
     */
    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
        
        this.isRecording = false;
        if (this.micButton) {
            this.micButton.classList.remove('recording');
            this.micButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
        }
        this.messageInput.placeholder = 'Message';
    }
    
    /**
     * Process voice input: transcribe and get AI response
     */
    async processVoiceInput(audioBlob) {
        try {
            // Show processing state
            if (this.micButton) {
                this.micButton.classList.add('speaking');
                this.micButton.innerHTML = '<i class="bi bi-hourglass-split"></i>';
            }
            
            // Create form data
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            
            // Add username header
            const headers = {};
            if (this.username) {
                headers['X-Username'] = this.username;
            }
            
            // Send to combined voice chat endpoint for lowest latency
            const response = await fetch('/api/voice/chat', {
                method: 'POST',
                headers: headers,
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Voice processing failed');
            }
            
            // Get transcript from headers and decode if MIME-encoded
            let transcript = response.headers.get('X-Transcript') || '';
            let responseText = response.headers.get('X-Response-Text') || '';
            
            // Decode MIME-encoded headers (RFC 2047)
            transcript = this.decodeMimeHeader(transcript);
            responseText = this.decodeMimeHeader(responseText);
            
            // Display transcript as user message
            if (transcript) {
                const userMessage = {
                    message_id: 'temp-' + Date.now(),
                    role: 'user',
                    content: transcript,
                    created_at: new Date().toISOString()
                };
                this.messages.push(userMessage);
                this.addMessageToDOM(userMessage);
                this.scrollToBottom();
            }
            
            // Display AI response text
            if (responseText) {
                const assistantMessage = {
                    message_id: 'temp-ai-' + Date.now(),
                    role: 'assistant',
                    content: responseText,
                    created_at: new Date().toISOString()
                };
                this.messages.push(assistantMessage);
                this.addMessageToDOM(assistantMessage);
                this.scrollToBottom();
            }
            
            // Get audio response
            const audioData = await response.blob();
            
            // Play audio response
            await this.playAudioResponse(audioData);
            
            // Enable voice mode for continued conversation
            this.voiceMode = true;
            
        } catch (error) {
            console.error('Error processing voice input:', error);
            this.showError('Failed to process voice input. Please try again.');
        } finally {
            if (this.micButton) {
                this.micButton.classList.remove('speaking');
                this.micButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
            }
        }
    }
    
    /**
     * Play audio response
     */
    async playAudioResponse(audioBlob) {
        return new Promise((resolve, reject) => {
            try {
                // Stop any current audio
                this.stopSpeaking();
                
                // Create audio element
                const audioUrl = URL.createObjectURL(audioBlob);
                this.currentAudio = new Audio(audioUrl);
                
                this.currentAudio.onplay = () => {
                    this.isSpeaking = true;
                    if (this.micButton) {
                        this.micButton.classList.add('speaking');
                        this.micButton.innerHTML = '<i class="bi bi-volume-up-fill"></i>';
                        this.micButton.title = 'Stop speaking';
                    }
                };
                
                this.currentAudio.onended = () => {
                    this.isSpeaking = false;
                    if (this.micButton) {
                        this.micButton.classList.remove('speaking');
                        this.micButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
                        this.micButton.title = 'Voice input';
                    }
                    URL.revokeObjectURL(audioUrl);
                    resolve();
                };
                
                this.currentAudio.onerror = (error) => {
                    console.error('Audio playback error:', error);
                    this.isSpeaking = false;
                    if (this.micButton) {
                        this.micButton.classList.remove('speaking');
                        this.micButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
                        this.micButton.title = 'Voice input';
                    }
                    URL.revokeObjectURL(audioUrl);
                    reject(error);
                };
                
                // Play audio
                this.currentAudio.play();
                
            } catch (error) {
                console.error('Error playing audio:', error);
                reject(error);
            }
        });
    }
    
    /**
     * Speak text using OpenAI TTS (called when not in voice mode)
     */
    async speakText(text) {
        try {
            // Generate speech using OpenAI TTS
            const response = await fetch('/api/voice/speak', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ text: text, speed: 1.1 })
            });
            
            if (!response.ok) {
                throw new Error('Speech generation failed');
            }
            
            const audioBlob = await response.blob();
            await this.playAudioResponse(audioBlob);
            
        } catch (error) {
            console.error('Error generating speech:', error);
        }
    }
    
    /**
     * Stop current speech
     */
    stopSpeaking() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }
        this.isSpeaking = false;
        if (this.micButton) {
            this.micButton.classList.remove('speaking');
            this.micButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
            this.micButton.title = 'Voice input';
        }
    }
    
    /**
     * Decode MIME-encoded header (RFC 2047 format)
     * Handles format: =?charset?encoding?encoded-text?=
     */
    decodeMimeHeader(str) {
        if (!str || !str.includes('=?')) {
            return str;
        }
        
        try {
            // Match MIME encoded-word pattern
            const pattern = /=\?([^?]+)\?([BQ])\?([^?]+)\?=/gi;
            
            return str.replace(pattern, (match, charset, encoding, encodedText) => {
                if (encoding.toUpperCase() === 'Q') {
                    // Quoted-printable encoding
                    let decoded = encodedText
                        .replace(/_/g, ' ')  // Underscores to spaces
                        .replace(/=([0-9A-F]{2})/gi, (m, hex) => {
                            return String.fromCharCode(parseInt(hex, 16));
                        });
                    return decoded;
                } else if (encoding.toUpperCase() === 'B') {
                    // Base64 encoding
                    return atob(encodedText);
                }
                return match;
            });
        } catch (error) {
            console.error('Error decoding MIME header:', error);
            return str;
        }
    }
}

// Initialize chat interface when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatInterface = new ChatInterface();
});
