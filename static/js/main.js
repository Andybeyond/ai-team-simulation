document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const projectSelect = document.getElementById('project-select');
    const createProjectBtn = document.getElementById('create-project-btn');
    const newProjectForm = document.getElementById('new-project-form');
    const newProjectModal = document.getElementById('newProjectModal');
    let currentProject = null;
    let messageCache = new Map();
    let isLoadingMessages = false;
    let hasMoreMessages = true;

    // Agent configuration with display names, colors, and welcome message routing
    const agentConfig = {
        'pm': { 
            displayName: 'PM', 
            receiveWelcome: true,
            color: 'var(--agent-pm-color)'
        },
        'dev': { 
            displayName: 'DEVELOPER', 
            receiveWelcome: true,
            color: 'var(--agent-dev-color)'
        },
        'tester': { 
            displayName: 'TESTER', 
            receiveWelcome: true,
            color: 'var(--agent-tester-color)'
        },
        'devops': { 
            displayName: 'DEVOPS', 
            receiveWelcome: true,
            color: 'var(--agent-devops-color)'
        },
        'ba': { 
            displayName: 'BUSINESS ANALYST', 
            receiveWelcome: true,
            color: 'var(--agent-ba-color)'
        },
        'uxd': { 
            displayName: 'UX DESIGNER', 
            receiveWelcome: true,
            color: 'var(--agent-uxd-color)'
        }
    };

    // Get current active tab's agent
    function getCurrentAgent() {
        const activeTab = document.querySelector('.mui-tab.active');
        return activeTab.getAttribute('data-agent-type');
    }

    // Get chat container for specific agent
    function getChatContainer(agent) {
        return document.querySelector(`.chat-container[data-agent="${agent}"]`);
    }

    // Handle tab switching
    document.querySelectorAll('.mui-tab').forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all tabs and hide all panes
            document.querySelectorAll('.mui-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => {
                p.classList.remove('show', 'active');
            });
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Show corresponding pane
            const targetId = this.getAttribute('aria-controls');
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add('show', 'active');
            }
        });
    });

    // Format context with enhanced readability and styling
    function formatContext(context) {
        if (!context) return '';
        
        try {
            // Split sections using the new separator
            const sections = context.split('━━━━━━━━━━').map(section => section.trim()).filter(Boolean);
            
            return sections.map(section => {
                // Split into message pairs and process
                const messages = section.split('\n\n').reduce((acc, block) => {
                    const lineContent = block.trim();
                    if (!lineContent) return acc;
                    
                    // Enhanced message detection with emojis
                    if (lineContent.startsWith('👤')) {
                        acc.push({
                            type: 'user',
                            content: lineContent.replace('👤', '').trim()
                        });
                    } else if (lineContent.startsWith('🤖')) {
                        acc.push({
                            type: 'agent',
                            content: lineContent.replace('🤖', '').trim()
                        });
                    }
                    return acc;
                }, []);
                
                // Create enhanced HTML structure for messages
                const messagesHTML = messages.map(msg => `
                    <div class="context-message ${msg.type}-context">
                        <div class="message-content">
                            <div class="message-icon">${msg.type === 'user' ? '👤' : '🤖'}</div>
                            <div class="message-text">
                                ${msg.content.split('\n').map(line => 
                                    `<p class="mb-1">${line.trim()}</p>`
                                ).join('')}
                            </div>
                        </div>
                    </div>
                `).join('');
                
                return messagesHTML ? `
                    <div class="context-section">
                        ${messagesHTML}
                    </div>
                ` : '';
            }).filter(Boolean).join('<div class="context-separator"></div>') || 
            '<div class="context-section"><p class="text-muted">No previous context available</p></div>';
            
        } catch (error) {
            console.error('Error formatting context:', error);
            return `<div class="context-section"><p class="text-danger">Error displaying context: ${error.message}</p></div>`;
        }
    }

    // Create message element with ChatGPT-like structure
    function createMessageElement(content, isUser = false, agent = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'agent-message'}`;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        // Create message icon
        const messageIcon = document.createElement('div');
        messageIcon.className = 'message-icon';
        messageIcon.innerHTML = isUser ? '<i class="material-icons">person</i>' : '<i class="material-icons">smart_toy</i>';

        // Create message text container
        const textContainer = document.createElement('div');
        textContainer.className = 'message-text';

        // Add role label for agents
        if (!isUser) {
            const roleLabel = document.createElement('div');
            roleLabel.className = 'message-role';
            roleLabel.textContent = agent ? agentConfig[agent]?.displayName || agent.toUpperCase() : 'AGENT';
            textContainer.appendChild(roleLabel);
        }

        // Add message content
        const messageText = document.createElement('div');
        messageText.innerHTML = content.split('\n').map(line => `<p>${line}</p>`).join('');
        textContainer.appendChild(messageText);

        messageContent.appendChild(messageIcon);
        messageContent.appendChild(textContainer);
        messageDiv.appendChild(messageContent);

        return messageDiv;
    }

    // Add message to chat with improved error handling
    // Keep track of last messages to prevent duplicates
    const lastMessages = new Map();
    
    function addMessage(content, isUser = false, agent = null) {
        try {
            if (isUser) {
                const targetAgent = getCurrentAgent();
                const chatContainer = getChatContainer(targetAgent);
                
                if (!chatContainer) {
                    console.error(`Chat container not found for agent: ${targetAgent}`);
                    return;
                }

                // Check for duplicate user messages
                const lastUserMessage = lastMessages.get(`user-${targetAgent}`);
                if (lastUserMessage === content) {
                    console.log('Duplicate user message prevented');
                    return;
                }
                
                const messageDiv = createMessageElement(content, true);
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                // Store this message as the last user message for this agent
                lastMessages.set(`user-${targetAgent}`, content);
            } else {
                const targetAgent = agent || getCurrentAgent();
                const chatContainer = getChatContainer(targetAgent);
                
                if (!chatContainer) {
                    console.error(`Chat container not found for agent: ${targetAgent}`);
                    return;
                }

                // Check for duplicate agent messages
                const lastAgentMessage = lastMessages.get(`agent-${targetAgent}`);
                if (lastAgentMessage === content) {
                    console.log('Duplicate agent message prevented');
                    return;
                }

                // Create message element with consistent styling for all agent messages
                const messageDiv = createMessageElement(content.trim(), false, targetAgent);
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                // Store this message as the last agent message
                lastMessages.set(`agent-${targetAgent}`, content);
            }
        } catch (error) {
            console.error('Error adding message:', error);
        }
    }

    // Load and update projects
    async function loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();
            if (data.success) {
                updateProjectSelect(data.projects);
                return data.projects;
            }
            console.error('Failed to load projects:', data.error);
            return null;
        } catch (error) {
            console.error('Error loading projects:', error);
            return null;
        }
    }

    function updateProjectSelect(projects) {
        projectSelect.innerHTML = '<option value="">Select Project</option>';
        Object.entries(projects).forEach(([id, project]) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = project.name;
            projectSelect.appendChild(option);
        });
    }

    function clearAllChats() {
        document.querySelectorAll('.chat-container').forEach(container => {
            container.innerHTML = '';
        });
    }

    // Enhanced project context loading
    async function loadProjectContext(projectId) {
        if (!projectId) return null;
        try {
            const response = await fetch(`/api/project/${projectId}/context`);
            const data = await response.json();
            if (data.success) {
                currentProject = projectId;
                return data;
            }
            console.error('Failed to load project context:', data.error);
            return null;
        } catch (error) {
            console.error('Error loading project context:', error);
            return null;
        }
    }

    // Enhanced welcome message handling
    async function sendWelcomeMessage(welcomeMessage) {
        if (!currentProject || !welcomeMessage) {
            console.error('Project or welcome message not set');
            return;
        }

        try {
            const response = await fetch('/interact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: welcomeMessage,
                    agent: 'pm',
                    project: currentProject
                })
            });

            const data = await response.json();
            if (data.success) {
                // Route welcome message to all agent tabs that should receive it
                Object.entries(agentConfig).forEach(([agentId, config]) => {
                    if (config.receiveWelcome) {
                        const chatContainer = getChatContainer(agentId);
                        if (chatContainer) {
                            // Use createMessageElement for consistent styling
                            const messageDiv = createMessageElement(data.response, false, agentId);
                            chatContainer.appendChild(messageDiv);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    }
                });
            } else {
                console.error('Failed to send welcome message:', data.error);
                const errorMessageDiv = createMessageElement(`Error: ${data.error}`, false, 'pm');
                getChatContainer('pm').appendChild(errorMessageDiv);
            }
        } catch (error) {
            console.error('Error sending welcome message:', error);
            addMessage(`Error: ${error.message}`, false, 'pm');
        }
    }

    // Enhanced project creation
    async function createNewProject(projectData) {
        let modal = null;
        try {
            modal = bootstrap.Modal.getInstance(newProjectModal);
            if (!modal) {
                modal = new bootstrap.Modal(newProjectModal);
            }

            const response = await fetch('/api/projects', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(projectData)
            });

            const data = await response.json();
            if (data.success) {
                modal.hide();
                await new Promise(resolve => {
                    newProjectModal.addEventListener('hidden.bs.modal', resolve, { once: true });
                });

                newProjectForm.reset();
                await loadProjects();
                projectSelect.value = projectData.id;
                const projectContext = await loadProjectContext(projectData.id);
                
                if (projectContext) {
                    clearAllChats();
                    addMessage(`Project "${projectData.name}" created successfully!`, false, 'pm');
                    
                    if (projectContext.context?.welcome_message) {
                        await sendWelcomeMessage(projectContext.context.welcome_message);
                    }
                }
                return true;
            } else {
                addMessage(`Error: ${data.error}`, false, 'pm');
                return false;
            }
        } catch (error) {
            console.error('Error creating project:', error);
            addMessage(`Error: ${error.message}`, false, 'pm');
            return false;
        }
    }

    // Event Listeners
    createProjectBtn.addEventListener('click', async function() {
        const projectId = document.getElementById('project-id').value.trim();
        const projectName = document.getElementById('project-name').value.trim();
        const projectDescription = document.getElementById('project-description').value.trim();

        if (!projectId || !projectName || !projectDescription) {
            alert('Please fill in all fields');
            return;
        }

        const projectData = {
            id: projectId,
            name: projectName,
            description: projectDescription
        };

        await createNewProject(projectData);
    });

    // Enhanced project selection handling
    projectSelect.addEventListener('change', async function() {
        const selectedProject = this.value;
        clearAllChats();

        if (selectedProject) {
            const context = await loadProjectContext(selectedProject);
            if (context) {
                addMessage(`Switched to project: ${context.project.name}`, false, 'pm');
                
                if (context.context?.welcome_message) {
                    await sendWelcomeMessage(context.context.welcome_message);
                }
            } else {
                addMessage('Error loading project context. Please try again.', false, 'pm');
            }
        } else {
            currentProject = null;
            addMessage('Please select a project to continue.', false, 'pm');
        }
    });

    // Message sending functionality
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        if (!currentProject) {
            addMessage('Please select a project before sending messages.', false, 'pm');
            return;
        }

        const currentAgent = getCurrentAgent();
        addMessage(message, true, currentAgent);
        userInput.value = '';

        try {
            const response = await fetch('/interact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    agent: currentAgent,
                    project: currentProject
                })
            });

            const data = await response.json();
            if (data.success) {
                addMessage(data.response, false, currentAgent);
            } else {
                addMessage(`Error: ${data.error}`, false, currentAgent);
            }
        } catch (error) {
            console.error('Error in sendMessage:', error);
            addMessage(`Error: ${error.message}`, false, currentAgent);
        }
    }

    // Initialize event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Load initial projects
    loadProjects().then(() => {
        console.log('Projects loaded successfully');
    }).catch(error => {
        console.error('Error loading initial projects:', error);
    });
});
