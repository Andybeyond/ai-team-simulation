from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
import os
import re

class BaseAgent:
    def __init__(self, agent_type, system_message_content):
        self.agent_type = agent_type
        self.llm = ChatOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
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
            # Get chat history
            history = self.memory.chat_memory.messages
            
            # Construct a detailed prompt with context and history
            prompt = self._build_prompt(user_input, context, history)
            
            # Add the user input to memory
            self.memory.chat_memory.add_user_message(user_input)
            
            # Generate response using the complete context
            response = self.llm.predict(prompt)
            
            # Add response to memory
            self.memory.chat_memory.add_ai_message(response)
            
            # Parse response for collaboration needs and extract any specific requests
            needs_collaboration, collaboration_requests = self._analyze_collaboration_needs(response)
            
            # Get context summary from memory
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
                'needs_collaboration': False,
                'collaboration_requests': {},
                'agent_type': self.agent_type,
                'context_summary': None
            }
    
    def _build_prompt(self, user_input: str, context: dict = None, history: list = None) -> str:
        prompt = f"{self.system_message.content}\n\n"
        
        # Add conversation history context
        if history:
            prompt += "Previous conversation history:\n"
            for msg in history[-5:]:  # Only include last 5 messages for context
                if isinstance(msg, HumanMessage):
                    prompt += f"User: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    prompt += f"{self.agent_type.upper()}: {msg.content}\n"
            prompt += "\n"
        
        # Add inter-agent context if available
        if context:
            prompt += "Previous agent responses:\n"
            for agent_type, response in context.items():
                prompt += f"{agent_type.upper()}: {response}\n"
            prompt += "\nConsider the above context while formulating your response.\n"
            
        prompt += f"\nUser input: {user_input}\n"
        prompt += "\nIf you need input from other agents, clearly indicate what you need from them using tags like: "
        prompt += "[NEED_DEV: specify technical implementation details] "
        prompt += "[NEED_TEST: specify testing requirements] "
        prompt += "[NEED_DEVOPS: specify deployment needs] "
        prompt += "[NEED_PM: specify project management aspects] "
        prompt += "[NEED_BA: specify business analysis needs]"
        
        return prompt
    
    def _analyze_collaboration_needs(self, response: str) -> tuple:
        collaboration_keywords = {
            'dev': ['code', 'implementation', 'develop', 'technical', 'architecture', 'framework'],
            'tester': ['test', 'quality', 'verify', 'validation', 'coverage', 'scenario'],
            'devops': ['deploy', 'infrastructure', 'pipeline', 'monitoring', 'scaling', 'performance'],
            'pm': ['plan', 'coordinate', 'timeline', 'requirements', 'scope', 'milestone'],
            'ba': ['business requirements', 'stakeholder', 'process improvement', 'feasibility', 'specification']
        }
        
        # Check for explicit collaboration requests using tags
        need_patterns = {
            'dev': r'\[NEED_DEV:(.*?)\]',
            'tester': r'\[NEED_TEST:(.*?)\]',
            'devops': r'\[NEED_DEVOPS:(.*?)\]',
            'pm': r'\[NEED_PM:(.*?)\]',
            'ba': r'\[NEED_BA:(.*?)\]'
        }
        
        needed_agents = []
        collaboration_requests = {}
        response_lower = response.lower()
        
        # Check for explicit requests
        for agent, pattern in need_patterns.items():
            if agent != self.agent_type:
                matches = re.findall(pattern, response, re.IGNORECASE)
                if matches:
                    needed_agents.append(agent)
                    collaboration_requests[agent] = [req.strip() for req in matches]
        
        # Check for implicit mentions using keywords
        for agent, keywords in collaboration_keywords.items():
            if agent not in needed_agents and agent != self.agent_type:
                if any(keyword in response_lower for keyword in keywords):
                    needed_agents.append(agent)
                    if agent not in collaboration_requests:
                        collaboration_requests[agent] = ["Please provide input based on the context"]
        
        return needed_agents, collaboration_requests
    
    def _get_context_summary(self) -> str:
        """Get a summary of the conversation context"""
        try:
            history = self.memory.chat_memory.messages
            if not history:
                return "No previous context available."
            
            # Create a summary of the last few interactions
            summary = []
            for msg in history[-3:]:  # Last 3 messages
                if isinstance(msg, HumanMessage):
                    summary.append(f"User asked: {msg.content[:100]}...")
                elif isinstance(msg, AIMessage):
                    summary.append(f"Agent responded about: {msg.content[:100]}...")
            
            return "\n".join(summary)
        except Exception as e:
            return f"Error retrieving context: {str(e)}"
