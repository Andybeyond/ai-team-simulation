from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
import os
import re

class BaseAgent:
    def __init__(self, agent_type, system_message_content):
        self.agent_type = agent_type
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7
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
        prompt += "If you need input from other agents, clearly indicate what you need from them using tags like:\n"
        prompt += "[NEED_DEV: specify technical implementation details]\n"
        prompt += "[NEED_TEST: specify testing requirements]\n"
        prompt += "[NEED_DEVOPS: specify deployment needs]\n"
        prompt += "[NEED_PM: specify project management aspects]\n"
        prompt += "[NEED_BA: specify business analysis needs]"
        
        return prompt
    
    def _analyze_collaboration_needs(self, response: str) -> tuple:
        need_patterns = {
            'dev': r'\[NEED_DEV:(.*?)\]',
            'tester': r'\[NEED_TEST:(.*?)\]',
            'devops': r'\[NEED_DEVOPS:(.*?)\]',
            'pm': r'\[NEED_PM:(.*?)\]',
            'ba': r'\[NEED_BA:(.*?)\]'
        }
        
        needed_agents = []
        collaboration_requests = {}
        
        # Check for collaboration requests using enhanced pattern matching
        for agent, pattern in need_patterns.items():
            if agent != self.agent_type:
                matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
                if matches:
                    needed_agents.append(agent)
                    collaboration_requests[agent] = [req.strip() for req in matches]
        
        return needed_agents, collaboration_requests

    def _get_context_summary(self) -> str:
        """Get complete conversation history with preserved formatting"""
        try:
            history = self.memory.chat_memory.messages
            if not history:
                return None
            
            conversations = []
            current_conversation = []
            
            # Process complete conversation history
            for msg in history:
                if isinstance(msg, HumanMessage):
                    # Start new conversation group
                    if current_conversation:
                        conversations.append("\n".join(current_conversation))
                        current_conversation = []
                    current_conversation.append(f"User asked:\n{msg.content}")
                elif isinstance(msg, AIMessage):
                    current_conversation.append(f"Agent responded:\n{msg.content}")
            
            # Add the last conversation if exists
            if current_conversation:
                conversations.append("\n".join(current_conversation))
            
            # Join conversations with clear separation while preserving formatting
            return "\n\n---\n\n".join(conversations) if conversations else None
            
        except Exception as e:
            return f"Error retrieving context: {str(e)}"
