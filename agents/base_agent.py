from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import (
    HumanMessage,
    SystemMessage,
    AIMessage
)
import re
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent:
    # Supported OpenAI models with capabilities and use cases
    SUPPORTED_MODELS = {
        "gpt-4": {
            "name": "GPT-4",
            "description": "Most capable model for complex tasks",
            "context_length": 8192,
            "max_tokens": 4096,
            "temperature": 0.7,
            "use_case": "Complex reasoning and analysis"
        },
        "gpt-3.5-turbo": {
            "name": "GPT-3.5 Turbo",
            "description": "Fast and efficient for standard tasks",
            "context_length": 4096,
            "max_tokens": 2048,
            "temperature": 0.7,
            "use_case": "General purpose interactions"
        },
        "o1-preview": {
            "name": "o1 Preview",
            "description": "Advanced reasoning model with internal chain of thought",
            "context_length": 128000,
            "max_output": 32768,
            "use_case": "Complex problem solving, deep analysis, research tasks"
        },
        "o1-mini": {
            "name": "o1 Mini",
            "description": "Specialized for code, math, and science tasks",
            "context_length": 128000,
            "max_output": 65536,
            "use_case": "Technical implementation, mathematical analysis, scientific research"
        }
    }

    def __init__(self, agent_type: str, system_message: str, model="gpt-4"):
        """Initialize the agent with enhanced error handling and logging."""
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("Agent type must be a non-empty string")
            
        if not system_message or not isinstance(system_message, str):
            raise ValueError("System message must be a non-empty string")
            
        try:
            self.agent_type = agent_type
            self.system_message = SystemMessage(content=system_message)
            
            # Configure model with optimal settings based on role
            try:
                if not os.environ.get('OPENAI_API_KEY'):
                    raise ValueError("OpenAI API key is not set in environment variables")
                    
                # Configure model based on agent type and role
                temperature = 0.7 if agent_type in ['pm', 'ba', 'uxd'] else 0.2
                
                # Use enhanced configuration with proper error handling
                self.llm = ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    max_tokens=self.SUPPORTED_MODELS[model]['max_tokens'],
                    request_timeout=90,
                    max_retries=3,
                    model_kwargs={
                        'response_format': {"type": "text"}
                    }
                )
            except ValueError as e:
                raise ValueError(f"Configuration error: {str(e)}")
            except Exception as e:
                raise ValueError(f"Failed to initialize ChatGPT model: {str(e)}. Please check your API key and network connection.")

            self.memory = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
            logger.info(f"Successfully initialized {agent_type} agent")
            
        except Exception as e:
            error_msg = f"Failed to initialize {agent_type} agent: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def process_input(self, user_input: str, context: dict = None) -> dict:
        """
        Process user input with enhanced context management and error handling.
        
        Args:
            user_input: The user's message
            context: Optional context dictionary
            
        Returns:
            dict containing response and collaboration information
        """
        try:
            if not user_input or not user_input.strip():
                raise ValueError("User input cannot be empty")

            logger.info(f"Processing input for {self.agent_type} agent")
            
            # Get complete chat history with enhanced logging
            history = self.memory.chat_memory.messages
            logger.debug(f"Retrieved {len(history)} message(s) from memory")
            
            # Construct a detailed prompt with full context and history
            prompt = self._build_prompt(user_input, context, history)
            logger.debug(f"Built prompt with context: {bool(context)}")
            
            # Add the user input to memory with validation
            if isinstance(user_input, str) and user_input.strip():
                self.memory.chat_memory.add_user_message(user_input)
                logger.debug("Added user message to memory")
            
            try:
                # Generate response with enhanced error handling and logging
                logger.info("Generating response from ChatGPT")
                response = self.llm.invoke(prompt).content
                
                # Enhanced response validation
                if not response or not isinstance(response, str):
                    raise ValueError("Invalid response format from ChatGPT")
                
                if len(response.strip()) < 10:
                    raise ValueError("Response too short or empty")
                
                # Log successful response generation
                logger.info("Successfully generated response")
                logger.debug(f"Response length: {len(response)}")
                    
            except ValueError as e:
                logger.error(f"Response validation error: {str(e)}")
                raise
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error generating response: {error_msg}")
                
                # Enhanced error classification
                if any(err in error_msg.lower() for err in ["rate limit", "quota"]):
                    raise ValueError("API rate limit exceeded. Please try again in a few moments.")
                elif "invalid api key" in error_msg.lower():
                    raise ValueError("Invalid API key. Please check your OpenAI API key configuration.")
                elif any(err in error_msg.lower() for err in ["timeout", "timed out"]):
                    raise ValueError("Request timed out. Please try again.")
                else:
                    raise ValueError(f"Failed to generate response: {error_msg}")
            
            # Add response to memory
            self.memory.chat_memory.add_ai_message(response)
            
            # Analyze collaboration needs
            needs_collaboration, collaboration_requests = self._analyze_collaboration_needs(response)
            
            # Get context summary
            context_summary = self._get_context_summary()
            
            return {
                'response': response,
                'needs_collaboration': needs_collaboration,
                'collaboration_requests': collaboration_requests,
                'agent_type': self.agent_type,
                'context_summary': context_summary
            }
            
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            raise

    def _get_relevant_history(self, history: list, max_messages: int = 10) -> list:
        """
        Select relevant messages from conversation history.
        
        Args:
            history: Complete conversation history
            max_messages: Maximum number of messages to include
            
        Returns:
            List of relevant messages for context
        """
        if not history:
            return []
            
        # Start with the most recent messages
        recent_history = history[-max_messages:]
        
        # Filter out system messages and empty content
        filtered_history = [
            msg for msg in recent_history
            if (isinstance(msg, (HumanMessage, AIMessage)) and 
                hasattr(msg, 'content') and 
                msg.content.strip())
        ]
        
        return filtered_history
    
    def _build_prompt(self, user_input: str, context: dict = None, history: list = None) -> str:
        """Build a comprehensive prompt with enhanced context management."""
        prompt = f"{self.system_message.content}\n\n"
        
        # Add curated conversation history with context preservation
        if history:
            prompt += "Previous conversation history:\n"
            # Filter and format relevant history
            relevant_history = self._get_relevant_history(history)
            for msg in relevant_history:
                if isinstance(msg, HumanMessage):
                    prompt += f"User: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    prompt += f"{self.agent_type.upper()}: {msg.content}\n"
            prompt += "\n"
        
        # Enhanced context integration
        if context:
            # Project context with structured formatting
            if context.get('project'):
                prompt += "Project Context:\n"
                project_data = context['project']
                # Prioritize key project information
                key_fields = ['name', 'description', 'status']
                for field in key_fields:
                    if field in project_data:
                        prompt += f"{field.title()}: {project_data[field]}\n"
                # Add any additional project context
                for key, value in project_data.items():
                    if key not in key_fields:
                        prompt += f"{key}: {value}\n"
                prompt += "\n"
            
            # Previous agent responses with improved formatting
            if context.get('previous_responses'):
                prompt += "Previous agent responses:\n"
                for agent_type, response in context['previous_responses'].items():
                    prompt += f"{agent_type.upper()}: {response}\n"
                prompt += "\n"
            
            # Structured request handling
            if context.get('requests'):
                prompt += "Specific requests:\n"
                if isinstance(context['requests'], list):
                    for request in context['requests']:
                        prompt += f"- {request}\n"
                elif isinstance(context['requests'], str):
                    prompt += f"- {context['requests']}\n"
                prompt += "\n"
        
        prompt += f"User input: {user_input}\n\n"
        prompt += "If you need input from other agents, use [NEED_AGENT_TYPE: message] format:\n"
        prompt += "[NEED_DEV: technical implementation details]\n"
        prompt += "[NEED_TEST: testing requirements]\n"
        prompt += "[NEED_DEVOPS: deployment needs]\n"
        prompt += "[NEED_PM: project management aspects]\n"
        prompt += "[NEED_BA: business analysis needs]\n"
        prompt += "[NEED_UX: design requirements]"
        
        return prompt
    
    def _analyze_collaboration_needs(self, response: str) -> tuple:
        agent_display_names = {
            'dev': 'Developer',
            'tester': 'Tester',
            'devops': 'DevOps',
            'pm': 'PM',
            'ba': 'Business Analyst',
            'uxd': 'UX Designer'
        }
        
        need_patterns = {
            'dev': r'Developer\s*->\s*Task for Developer\s*\[(.*?)\]',
            'tester': r'Tester\s*->\s*Task for Tester\s*\[(.*?)\]',
            'devops': r'DevOps\s*->\s*Task for DevOps\s*\[(.*?)\]',
            'pm': r'PM\s*->\s*Task for PM\s*\[(.*?)\]',
            'ba': r'Business Analyst\s*->\s*Task for Business Analyst\s*\[(.*?)\]',
            'uxd': r'UX Designer\s*->\s*Task for UX Designer\s*\[(.*?)\]'
        }
        
        needed_agents = []
        collaboration_requests = {}
        
        # Convert old format to new format
        old_patterns = {
            'dev': r'\[NEED_DEV:(.*?)\]',
            'tester': r'\[NEED_TEST:(.*?)\]',
            'devops': r'\[NEED_DEVOPS:(.*?)\]',
            'pm': r'\[NEED_PM:(.*?)\]',
            'ba': r'\[NEED_BA:(.*?)\]'
        }
        
        modified_response = response
        
        # Replace old format with new format
        for agent, pattern in old_patterns.items():
            matches = re.findall(pattern, modified_response, re.IGNORECASE | re.DOTALL)
            for match in matches:
                old_text = f'[NEED_{agent.upper()}:{match}]'
                new_text = f'{agent_display_names[agent]} -> Task for {agent_display_names[agent]} [{match.strip()}]'
                modified_response = modified_response.replace(old_text, new_text)
        
        # Check for collaboration requests using enhanced pattern matching
        for agent, pattern in need_patterns.items():
            if agent != self.agent_type:
                matches = re.findall(pattern, modified_response, re.IGNORECASE | re.DOTALL)
                if matches:
                    needed_agents.append(agent)
                    collaboration_requests[agent] = [req.strip() for req in matches]
        
        return needed_agents, collaboration_requests
    
    def _get_context_summary(self) -> str:
        """Store conversation history for memory but don't display in UI"""
        try:
            history = self.memory.chat_memory.messages
            if not history:
                return None
            
            # Store context but don't format for display
            message_pairs = {}
            current_user_msg = None
            
            for msg in history:
                if not hasattr(msg, 'content'):
                    continue
                    
                msg_content = msg.content.strip()
                if not msg_content:
                    continue
                    
                is_user = isinstance(msg, HumanMessage)
                
                if is_user:
                    current_user_msg = msg_content
                elif current_user_msg is not None:
                    msg_hash = hash(f"{current_user_msg}:{msg_content}")
                    if msg_hash not in message_pairs:
                        message_pairs[msg_hash] = {
                            'user': current_user_msg,
                            'agent': msg_content,
                            'timestamp': len(message_pairs)
                        }
                    current_user_msg = None
                    
            # Return None to hide context from UI while keeping it in memory
            return None
            
        except Exception as e:
            return None