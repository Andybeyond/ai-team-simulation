from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
import os
import re

class BaseAgent:
    # Supported OpenAI models with capabilities and use cases
    SUPPORTED_MODELS = {
        "gpt-4o": {
            "name": "GPT-4o (Flagship)",
            "description": "Most capable model for complex tasks, 2x faster, 50% cheaper than GPT-4 Turbo",
            "context_length": 128000,
            "max_output": 16384,
            "use_case": "Complex multi-step reasoning, project management, technical analysis"
        },
        "gpt-4o-mini": {
            "name": "GPT-4o Mini",
            "description": "Fast and efficient model for lightweight tasks",
            "context_length": 128000,
            "max_output": 16384,
            "use_case": "Quick analysis, rapid prototyping, efficient processing"
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

    def __init__(self, agent_type, system_message_content, model="gpt-4o"):
        self.agent_type = agent_type
        
        # Validate model selection
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model. Please choose from: {', '.join(self.SUPPORTED_MODELS.keys())}")
            
        self.model = model
        model_config = self.SUPPORTED_MODELS[model]
        
        # Configure model with optimal settings based on role
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0.7 if agent_type in ['pm', 'ba', 'uxd'] else 0.2,  # Lower temperature for technical roles
            max_tokens=model_config['max_output'],
            model_kwargs={
                'context_length': model_config['context_length'],
                'response_format': {"type": "text"}
            }
        )
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            human_prefix="User",
            ai_prefix=f"AI_{agent_type.upper()}"
        )
        self.system_message = SystemMessage(content=system_message_content)
        
    def process_input(self, user_input: str, context: dict = None) -> dict:
        try:
            # Get complete chat history without truncation
            history = self.memory.chat_memory.messages
            
            # Construct a detailed prompt with full context and history
            prompt = self._build_prompt(user_input, context, history)
            
            # Add the user input to memory
            self.memory.chat_memory.add_user_message(user_input)
            
            # Generate response using the complete context
            response = self.llm.invoke(prompt).content
            
            # Add response to memory
            self.memory.chat_memory.add_ai_message(response)
            
            # Parse response for collaboration needs and extract any specific requests
            needs_collaboration, collaboration_requests = self._analyze_collaboration_needs(response)
            
            # Get complete context summary from memory
            context_summary = self._get_context_summary()
            
            return {
                'response': response,
                'needs_collaboration': needs_collaboration,
                'collaboration_requests': collaboration_requests,
                'agent_type': self.agent_type,
                'context_summary': context_summary
            }
        except Exception as e:
            return {
                'response': f"Error processing request: {str(e)}",
                'needs_collaboration': [],
                'collaboration_requests': {},
                'agent_type': self.agent_type,
                'context_summary': None
            }
    
    def _build_prompt(self, user_input: str, context: dict = None, history: list = None) -> str:
        prompt = f"{self.system_message.content}\n\n"
        
        # Add complete conversation history without truncation
        if history:
            prompt += "Previous conversation history:\n"
            for msg in history:
                if isinstance(msg, HumanMessage):
                    prompt += f"User: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    prompt += f"{self.agent_type.upper()}: {msg.content}\n"
            prompt += "\n"
        
        # Add complete context if available
        if context:
            if context.get('project'):
                prompt += "Project Context:\n"
                for key, value in context['project'].items():
                    prompt += f"{key}: {value}\n"
                prompt += "\n"
            
            if context.get('previous_responses'):
                prompt += "Previous agent responses:\n"
                for agent_type, response in context['previous_responses'].items():
                    prompt += f"{agent_type.upper()}: {response}\n"
                prompt += "\n"
            
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
