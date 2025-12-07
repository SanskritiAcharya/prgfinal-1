// Socket.IO connection
let socket;
let isConnected = false;

// Initialize socket connection if user is authenticated
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated (chat widget exists)
    const chatWidget = document.getElementById('chatWidget');
    if (chatWidget) {
        // Initialize Socket.IO connection with reconnection
        socket = io({
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5
        });
        
        socket.on('connect', function() {
            console.log('Connected to server');
            isConnected = true;
            // Don't add welcome message here, wait for server confirmation
        });
        
        socket.on('connected', function(data) {
            console.log('Server connection confirmed:', data);
            if (document.getElementById('chatMessages').children.length === 0) {
                addChatMessage('bot', 'Hello! I\'m your Ecotrack assistant. How can I help you today?');
            }
        });
        
        socket.on('chat_response', function(data) {
            addChatMessage('user', data.message);
            setTimeout(function() {
                addChatMessage('bot', data.response);
            }, 300);
        });
        
        socket.on('error', function(data) {
            addChatMessage('bot', 'Error: ' + data.message);
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
            isConnected = false;
        });
        
        socket.on('reconnect', function() {
            console.log('Reconnected to server');
            isConnected = true;
        });
    }
});

// Chat functionality
function toggleChat() {
    const chatBody = document.getElementById('chatBody');
    const chatToggle = document.querySelector('.chat-toggle');
    
    if (chatBody.classList.contains('hidden')) {
        chatBody.classList.remove('hidden');
        chatToggle.textContent = '−';
    } else {
        chatBody.classList.add('hidden');
        chatToggle.textContent = '+';
    }
}

function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) {
        return;
    }
    
    if (!socket || !isConnected) {
        addChatMessage('bot', 'Connecting to server... Please wait a moment and try again.');
        return;
    }
    
    // Show user message immediately
    addChatMessage('user', message);
    input.value = '';
    
    // Send to server
    socket.emit('chat_message', { 
        message: message,
        user_id: getUserIdFromPage() // Try to get user ID from page
    });
}

function getUserIdFromPage() {
    // Try to extract user ID from page if available
    // This is a fallback - the server should get it from session
    const userData = document.querySelector('[data-user-id]');
    return userData ? userData.getAttribute('data-user-id') : null;
}

function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

function addChatMessage(type, message) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.textContent = message;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.3s';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });
    
    // Check for notifications
    checkNotifications();
    
    // Check notifications every 30 seconds
    setInterval(checkNotifications, 30000);
});

// Check for unread notifications
function checkNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('notificationBadge');
            if (badge && data.length > 0) {
                badge.style.display = 'inline-block';
                badge.textContent = data.length > 9 ? '9+' : data.length;
            } else if (badge) {
                badge.style.display = 'none';
            }
        })
        .catch(error => console.error('Error checking notifications:', error));
}

// Mobile menu toggle
function toggleMobileMenu() {
    const navMenu = document.getElementById('navMenu');
    if (navMenu) {
        navMenu.classList.toggle('active');
    }
}

// Close mobile menu when clicking outside
document.addEventListener('click', function(event) {
    const navMenu = document.getElementById('navMenu');
    const navToggle = document.querySelector('.nav-toggle');
    
    if (navMenu && navToggle && 
        !navMenu.contains(event.target) && 
        !navToggle.contains(event.target) &&
        navMenu.classList.contains('active')) {
        navMenu.classList.remove('active');
    }
});

// Close mobile menu when clicking on a link
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-menu a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            const navMenu = document.getElementById('navMenu');
            if (navMenu && window.innerWidth <= 768) {
                navMenu.classList.remove('active');
            }
        });
    });
});

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = 'var(--danger-color)';
                } else {
                    field.style.borderColor = 'var(--border-color)';
                }
            });
            
            if (!isValid) {
                event.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });
});

// API helper functions
async function fetchRecyclingCenters(lat, lng) {
    try {
        const url = `/api/recycling-centers${lat && lng ? `?lat=${lat}&lng=${lng}` : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching recycling centers:', error);
        return [];
    }
}

async function fetchPickupSchedules(area) {
    try {
        const url = `/api/pickup-schedules${area ? `?area=${encodeURIComponent(area)}` : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching pickup schedules:', error);
        return [];
    }
}

async function addWasteEntry(wasteType, weightKg, description) {
    try {
        const response = await fetch('/api/waste-entries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                waste_type: wasteType,
                weight_kg: weightKg,
                description: description
            })
        });
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error adding waste entry:', error);
        return null;
    }
}

