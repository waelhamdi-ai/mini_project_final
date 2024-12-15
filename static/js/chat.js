let selectedRecipient = null;
let lastMessageTimestamp = 0;
let pollingInterval = null;
let processedMessages = new Set();

document.addEventListener('DOMContentLoaded', function() {
    const userItems = document.querySelectorAll('.user-item');
    const chatBox = document.getElementById('chat-box');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message');
    const selectedUserInfo = document.querySelector('.selected-user .user-info');
    const selectedUserAvatar = document.querySelector('.selected-user .user-avatar img');

    function startPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        loadMessages(selectedRecipient);
        pollingInterval = setInterval(() => {
            if (selectedRecipient) {
                loadMessages(selectedRecipient);
            }
        }, 3000);
    }

    userItems.forEach(item => {
        item.addEventListener('click', function() {
            userItems.forEach(u => u.classList.remove('active'));
            this.classList.add('active');
            
            selectedRecipient = this.dataset.email;
            const userName = this.querySelector('.user-info h4').textContent;
            const userAvatar = this.querySelector('.user-avatar img').src;
            
            selectedUserInfo.innerHTML = `
                <h4>${userName}</h4>
                <p class="user-status-text">Online</p>
            `;
            selectedUserAvatar.src = userAvatar;

            resetChat();
            startPolling();
        });
    });

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        if (!selectedRecipient) {
            alert('Please select a user to chat with');
            return;
        }

        const message = messageInput.value.trim();
        if (message) {
            sendMessage(message);
            messageInput.value = '';
        }
    });

    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
    });
});

function loadMessages(recipientEmail) {
    if (!recipientEmail) return;
    
    fetch(`/get_messages?recipient=${recipientEmail}&after=${lastMessageTimestamp}`)
        .then(response => response.json())
        .then(messages => {
            if (messages.length > 0) {
                const chatBox = document.getElementById('chat-box');
                messages.forEach(message => {
                    const messageId = message.id || `${message.timestamp}-${message.sender_email}-${message.message}`;
                    if (!processedMessages.has(messageId)) {
                        appendMessage(message);
                        processedMessages.add(messageId);
                        lastMessageTimestamp = Math.max(lastMessageTimestamp, message.timestamp);
                    }
                });
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        })
        .catch(error => console.error('Error loading messages:', error));
}

function sendMessage(message) {
    const submitButton = document.querySelector('#chat-form button[type="submit"]');
    submitButton.disabled = true;

    fetch('/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            recipient: selectedRecipient,
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Wait for the next poll to show the message
            setTimeout(() => loadMessages(selectedRecipient), 500);
        } else {
            alert('Failed to send message: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
        alert('Error sending message');
    })
    .finally(() => {
        submitButton.disabled = false;
    });
}

function appendMessage(message) {
    const chatBox = document.getElementById('chat-box');
    const messageId = message.id || `${message.timestamp}-${message.sender_email}-${message.message}`;
    
    if (document.querySelector(`[data-message-id="${messageId}"]`)) {
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.sender_email === currentUserEmail ? 'sent' : 'received'}`;
    messageDiv.setAttribute('data-message-id', messageId);
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'user-avatar';
    avatarDiv.innerHTML = `
        <img src="${message.sender_profile_picture || '/static/images/default_profile.jpg'}" alt="Profile">
    `;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.textContent = message.message;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatBox.appendChild(messageDiv);
    
    // Scroll to bottom after adding message
    chatBox.scrollTop = chatBox.scrollHeight;
}

function resetChat() {
    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML = '';
    lastMessageTimestamp = 0;
    processedMessages.clear();
}