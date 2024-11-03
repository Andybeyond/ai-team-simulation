document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const agentSelect = document.getElementById('agent-select');

    function addMessage(content, isUser = false, agentType = null) {
        console.log('Adding message:', { content, isUser, agentType });
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'agent-message'}`;

        if (!isUser && content.includes('\n\n')) {
            // Handle multi-agent responses
            const responses = content.split('\n\n');
            console.log('Processing multi-agent responses:', responses);
            responses.forEach(response => {
                if (response.trim()) {
                    const agentResponse = document.createElement('div');
                    agentResponse.className = 'agent-response';
                    
                    // Check if response has agent prefix
                    const agentMatch = response.match(/^(PM|DEVELOPER|TESTER|DEVOPS|BUSINESS ANALYST):/i);
                    if (agentMatch) {
                        console.log('Found agent match:', agentMatch);
                        const [fullMatch, agent] = agentMatch;
                        const agentLabel = document.createElement('div');
                        agentLabel.className = 'agent-label';
                        agentLabel.textContent = agent;
                        agentLabel.setAttribute('data-agent', agent);
                        agentResponse.setAttribute('data-agent', agent);
                        agentResponse.appendChild(agentLabel);
                        response = response.substring(fullMatch.length).trim();
                    }
                    
                    const responseText = document.createElement('div');
                    responseText.className = 'response-text';
                    responseText.textContent = response;
                    agentResponse.appendChild(responseText);
                    messageDiv.appendChild(agentResponse);
                }
            });
        } else {
            messageDiv.textContent = content;
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage(message, true);
        userInput.value = '';

        try {
            console.log('Sending message to server:', {
                message: message,
                agent: agentSelect.value
            });

            const response = await fetch('/interact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    agent: agentSelect.value
                })
            });

            const data = await response.json();
            console.log('Received response from server:', data);
            
            if (data.success) {
                addMessage(data.response);
            } else {
                addMessage(`Error: ${data.error}`);
            }
        } catch (error) {
            console.error('Error in sendMessage:', error);
            addMessage(`Error: ${error.message}`);
        }
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
