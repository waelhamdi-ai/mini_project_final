let selectedRecipient = null;
let lastMessageTimestamp = 0;

document.addEventListener('DOMContentLoaded', function() {
    const userItems = document.querySelectorAll('.user-item');
    const chatBox = document.getElementById('chat-box');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message');
    const selectedUserInfo = document.querySelector('.selected-user .user-info');
    const selectedUserAvatar = document.querySelector('.selected-user .user-avatar img');

    // Handle user selection
    userItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remove active class from all users
            userItems.forEach(u => u.classList.remove('active'));
            // Add active class to selected user
            this.classList.add('active');

            // Update selected recipient
            selectedRecipient = this.dataset.email;
            
            // Update header with selected user info
            const userName = this.querySelector('.user-info h4').textContent;
            const userEmail = this.querySelector('.user-info p').textContent;
            const userAvatar = this.querySelector('.user-avatar img').src;
            
            selectedUserInfo.innerHTML = `
                <h4>${userName}</h4>
                <p class="user-status-text">Online</p>
            `;
            selectedUserAvatar.src = userAvatar;

            // Load messages
            loadMessages(selectedRecipient);
            // Start polling for new messages
            startPolling();
        });
    });

    // Handle message submission
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
});

function startPolling() {
    // Poll for new messages every 3 seconds
    setInterval(() => {
        if (selectedRecipient) {
            loadMessages(selectedRecipient);
        }
    }, 3000);
}

function loadMessages(recipientEmail) {
    fetch(`/get_messages?recipient=${recipientEmail}&after=${lastMessageTimestamp}`)
        .then(response => response.json())
        .then(messages => {
            if (messages.length > 0) {
                const chatBox = document.getElementById('chat-box');
                messages.forEach(message => {
                    appendMessage(message);
                    lastMessageTimestamp = Math.max(lastMessageTimestamp, message.timestamp);
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
            // Immediately append the sent message
            appendMessage({
                sender_email: currentUserEmail,
                sender_profile_picture: document.querySelector('.user-avatar img').src,
                message: message,
                timestamp: Date.now()
            });
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
    // Check if message already exists to avoid duplicates
    const existingMessage = chatBox.querySelector(`[data-timestamp="${message.timestamp}"]`);
    if (existingMessage) {
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.sender_email === currentUserEmail ? 'sent' : 'received'}`;
    messageDiv.setAttribute('data-timestamp', message.timestamp); // Add timestamp as data attribute
    
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