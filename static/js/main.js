document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const projectSelect = document.getElementById('project-select');
    const createProjectBtn = document.getElementById('create-project-btn');
    const newProjectForm = document.getElementById('new-project-form');
    const newProjectModal = document.getElementById('newProjectModal');
    let currentProject = null;

    // Agent configuration with display names and welcome message routing
    const agentConfig = {
        'pm': { displayName: 'PM', receiveWelcome: true },
        'dev': { displayName: 'DEVELOPER', receiveWelcome: true },
        'tester': { displayName: 'TESTER', receiveWelcome: true },
        'devops': { displayName: 'DEVOPS', receiveWelcome: true },
        'ba': { displayName: 'BUSINESS ANALYST', receiveWelcome: true },
        'uxd': { displayName: 'UX DESIGNER', receiveWelcome: true }
    };

    // Get current active tab's agent
    function getCurrentAgent() {
        const activeTab = document.querySelector('.nav-link.active');
        return activeTab.id.replace('-tab', '');
    }

    // Get chat container for specific agent
    function getChatContainer(agent) {
        return document.querySelector(`.chat-container[data-agent="${agent}"]`);
    }

    // Format context with improved error handling
    function formatContext(context) {
        if (!context) return '';
        
        try {
            const sections = context.split('---').map(section => section.trim());
            return sections.map(section => {
                const lines = section.split('\n').map(line => {
                    if (line.startsWith('User asked:')) {
                        return `<h6 class="context-header">👤 ${line}</h6>`;
                    } else if (line.startsWith('Agent responded:')) {
                        return `<h6 class="context-header">🤖 ${line}</h6>`;
                    }
                    return `<p>${line}</p>`;
                }).join('');
                return `<div class="context-section">${lines}</div>`;
            }).join('<hr class="context-separator">');
        } catch (error) {
            console.error('Error formatting context:', error);
            return `<div class="context-section"><p>Error displaying context: ${error.message}</p></div>`;
        }
    }

    // Create message element with improved structure
    function createMessageElement(content, isUser = false, agent = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'agent-message'}`;

        if (isUser) {
            const textContent = document.createElement('div');
            textContent.className = 'response-text';
            textContent.innerHTML = content.split('\n').map(line => `<p>${line}</p>`).join('');
            messageDiv.appendChild(textContent);
        } else {
            const agentResponse = document.createElement('div');
            agentResponse.className = 'agent-response';
            if (agent) {
                agentResponse.setAttribute('data-agent', agent);
            }
            
            const agentLabel = document.createElement('div');
            agentLabel.className = 'agent-label';
            const displayName = agent ? agentConfig[agent]?.displayName || agent.toUpperCase() : 'AGENT';
            agentLabel.setAttribute('data-agent', displayName);
            
            const labelContent = document.createElement('span');
            labelContent.textContent = displayName;
            agentLabel.appendChild(labelContent);
            
            const textContent = document.createElement('div');
            textContent.className = 'response-text';
            textContent.innerHTML = content.split('\n').map(line => `<p>${line}</p>`).join('');
            
            agentResponse.appendChild(agentLabel);
            agentResponse.appendChild(textContent);
            messageDiv.appendChild(agentResponse);
        }

        return messageDiv;
    }

    // Add message to chat with improved error handling
    function addMessage(content, isUser = false, agent = null) {
        try {
            if (isUser) {
                const targetAgent = getCurrentAgent();
                const chatContainer = getChatContainer(targetAgent);
                
                if (!chatContainer) {
                    console.error(`Chat container not found for agent: ${targetAgent}`);
                    return;
                }
                
                const messageDiv = createMessageElement(content, true);
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                const responses = content.includes('\n\n') ? content.split('\n\n') : [content];
                
                responses.forEach(response => {
                    if (!response.trim()) return;

                    const agentMatch = response.match(/^((?:PM|DEVELOPER|TESTER|DEVOPS|BUSINESS ANALYST|UX DESIGNER))(?:\s+\((?:with context from:)?([\s\S]*?)\))?\s*([\s\S]*)$/);
                    
                    if (agentMatch) {
                        const [_, agentName, context, message] = agentMatch;
                        const targetAgent = Object.entries(agentConfig).find(([_, config]) => 
                            config.displayName === agentName
                        )?.[0] || agent;

                        if (!targetAgent) {
                            console.error(`Invalid agent name: ${agentName}`);
                            return;
                        }

                        const chatContainer = getChatContainer(targetAgent);
                        if (!chatContainer) {
                            console.error(`Chat container not found for agent: ${targetAgent}`);
                            return;
                        }

                        const messageDiv = document.createElement('div');
                        messageDiv.className = 'message agent-message';
                        const agentResponse = document.createElement('div');
                        agentResponse.className = 'agent-response';
                        agentResponse.setAttribute('data-agent', targetAgent);

                        // Create agent label with context
                        const agentLabel = document.createElement('div');
                        agentLabel.className = 'agent-label';
                        agentLabel.setAttribute('data-agent', agentName);
                        
                        const labelContent = document.createElement('span');
                        labelContent.textContent = agentName;
                        agentLabel.appendChild(labelContent);

                        if (context) {
                            const contextButton = document.createElement('button');
                            contextButton.className = 'context-toggle';
                            contextButton.textContent = 'Show Context';
                            contextButton.onclick = function() {
                                const contextInfo = this.parentElement.nextElementSibling;
                                const isShowing = contextInfo.classList.toggle('show');
                                this.textContent = isShowing ? 'Hide Context' : 'Show Context';
                            };
                            agentLabel.appendChild(contextButton);

                            const contextInfo = document.createElement('div');
                            contextInfo.className = 'context-info';
                            contextInfo.innerHTML = formatContext(context);
                            agentResponse.appendChild(contextInfo);
                        }

                        agentResponse.appendChild(agentLabel);

                        if (message) {
                            const responseText = document.createElement('div');
                            responseText.className = 'response-text';
                            responseText.innerHTML = message.split('\n').map(line => `<p>${line}</p>`).join('');
                            agentResponse.appendChild(responseText);
                        }

                        messageDiv.appendChild(agentResponse);
                        chatContainer.appendChild(messageDiv);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    } else {
                        // Handle plain messages
                        const targetAgent = agent || getCurrentAgent();
                        const chatContainer = getChatContainer(targetAgent);
                        
                        if (!chatContainer) {
                            console.error(`Chat container not found for agent: ${targetAgent}`);
                            return;
                        }

                        const messageDiv = createMessageElement(response, false, targetAgent);
                        chatContainer.appendChild(messageDiv);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                });
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
                            addMessage(data.response, false, agentId);
                        }
                    }
                });
            } else {
                console.error('Failed to send welcome message:', data.error);
                addMessage(`Error: ${data.error}`, false, 'pm');
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
