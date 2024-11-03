import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from agents.project_manager import ProjectManagerAgent
from agents.developer import DeveloperAgent
from agents.tester import TesterAgent
from agents.devops import DevOpsAgent
from agents.business_analyst import BusinessAnalystAgent
from agents.ux_designer import UXDesignerAgent
from github_integration import GitHubIntegration

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Validate OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Initialize agents
project_manager = ProjectManagerAgent()
developer = DeveloperAgent()
tester = TesterAgent()
devops = DevOpsAgent()
business_analyst = BusinessAnalystAgent()
ux_designer = UXDesignerAgent()

# Initialize GitHub integration
github = GitHubIntegration()

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to load index page',
            'details': str(e)
        }), 500

@app.route('/relationships')
def relationships():
    try:
        return render_template('agent_relationships.html')
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to load relationships page',
            'details': str(e)
        }), 500

@app.route('/github')
def github_page():
    try:
        return render_template('github_init.html')
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to load GitHub initialization page',
            'details': str(e)
        }), 500

@app.route('/github/init', methods=['POST'])
def init_github():
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400

        repo_name = request.json.get('repo_name', 'ai-team-simulation')
        description = request.json.get('description')
        result = github.initialize_repository(repo_name, description)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/interact', methods=['POST'])
def interact():
    try:
        # Validate request content type
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400

        # Parse request data
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is empty'
            }), 400

        user_input = data.get('message')
        agent_type = data.get('agent', 'pm')  # Default to project manager

        # Validate required fields
        if not user_input:
            return jsonify({
                'success': False,
                'error': 'Message field is required'
            }), 400

        # Map agent type to corresponding agent and their display names
        agents = {
            'pm': (project_manager, 'PM'),
            'dev': (developer, 'DEVELOPER'),
            'tester': (tester, 'TESTER'),
            'devops': (devops, 'DEVOPS'),
            'ba': (business_analyst, 'BUSINESS ANALYST'),
            'uxd': (ux_designer, 'UX DESIGNER')
        }

        print(f"\n[DEBUG] Starting interaction with agent type: {agent_type}")

        selected_agent, display_name = agents.get(agent_type, (None, None))
        if not selected_agent:
            return jsonify({
                'success': False,
                'error': f'Invalid agent type: {agent_type}'
            }), 400

        # Track which agents have been used to prevent duplicates
        used_agents = set()
        
        # Process initial response
        print(f"[DEBUG] Processing initial response from {display_name}")
        result = selected_agent.process_input(user_input)
        
        # Include context summary in response
        response = f"{display_name}: {result['response']}"
        if result.get('context_summary'):
            print(f"[DEBUG] Context summary available for {display_name}")
            response = f"{display_name} (with context from: {result['context_summary']})\n{result['response']}"

        # Initialize collaboration tracking with proper structure
        collaboration_context = {}
        
        # Add initial response to context
        collaboration_context[agent_type] = {
            'response': result['response'],
            'display_name': display_name,
            'requests': result.get('collaboration_requests', {}),
            'context_summary': result.get('context_summary')
        }
        used_agents.add(agent_type)

        needs_collaboration = result.get('needs_collaboration', [])
        print(f"[DEBUG] Initial agent needs collaboration with: {needs_collaboration}")

        # Process collaboration chain
        if needs_collaboration:
            collaboration_queue = [(agent_type, collab_type) 
                               for collab_type in needs_collaboration]
            
            print(f"[DEBUG] Initial collaboration queue: {collaboration_queue}")
            
            while collaboration_queue:
                parent_type, collab_type = collaboration_queue.pop(0)
                print(f"\n[DEBUG] Processing collaboration: {parent_type} -> {collab_type}")
                
                if collab_type in used_agents:
                    print(f"[DEBUG] Skipping {collab_type} - already processed")
                    continue
                    
                collab_agent, collab_display_name = agents.get(collab_type, (None, None))
                if not collab_agent:
                    print(f"[DEBUG] Invalid collaboration agent type: {collab_type}")
                    continue

                try:
                    # Prepare context with previous responses and memory
                    context = {
                        'previous_responses': {
                            agent_type: info['response']
                            for agent_type, info in collaboration_context.items()
                        }
                    }

                    # Add specific requests from parent agent if they exist
                    parent_requests = collaboration_context[parent_type].get('requests', {})
                    if collab_type in parent_requests:
                        context['requests'] = parent_requests[collab_type]
                        print(f"[DEBUG] Added specific requests for {collab_type}: {context['requests']}")

                    # Get collaboration response
                    print(f"[DEBUG] Getting response from {collab_display_name}")
                    collab_result = collab_agent.process_input(user_input, context)
                    
                    # Add to used agents to prevent duplicates
                    used_agents.add(collab_type)
                    
                    # Update collaboration context with memory information
                    collaboration_context[collab_type] = {
                        'response': collab_result['response'],
                        'display_name': collab_display_name,
                        'requests': collab_result.get('collaboration_requests', {}),
                        'context_summary': collab_result.get('context_summary')
                    }
                    
                    # Add formatted response with context if available
                    if collab_result.get('context_summary'):
                        response += f"\n\n{collab_display_name} (with context from: {collab_result['context_summary']})\n{collab_result['response']}"
                    else:
                        response += f"\n\n{collab_display_name}: {collab_result['response']}"
                    
                    print(f"[DEBUG] Added response from {collab_display_name}")

                    # Handle nested collaboration
                    nested_collaboration = collab_result.get('needs_collaboration', [])
                    if nested_collaboration:
                        print(f"[DEBUG] {collab_display_name} needs nested collaboration with: {nested_collaboration}")
                        for nested_type in nested_collaboration:
                            if nested_type not in used_agents:
                                collaboration_queue.append((collab_type, nested_type))
                                print(f"[DEBUG] Added to queue: {collab_type} -> {nested_type}")

                except Exception as e:
                    print(f"[DEBUG] Error in collaboration with {collab_type}: {str(e)}")
                    continue

        print("[DEBUG] Final collaboration context:", collaboration_context.keys())
        print("[DEBUG] Used agents:", used_agents)

        return jsonify({
            'success': True,
            'response': response
        })

    except Exception as e:
        print(f"[DEBUG] Error in /interact: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
