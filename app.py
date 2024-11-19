import os
import shutil
from flask import Flask, render_template, request, jsonify, session, Response
from flask_cors import CORS
from agents.project_manager import ProjectManagerAgent
from agents.developer import DeveloperAgent
from agents.tester import TesterAgent
from agents.devops import DevOpsAgent
from agents.business_analyst import BusinessAnalystAgent
from agents.ux_designer import UXDesignerAgent
from github_integration import GitHubIntegration
from database import db, Project, ChatMessage, init_db
import json
from pathlib import Path
from typing import Union, Tuple, Optional
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Initialize database
init_db(app)

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

def create_project_structure(project_id: str) -> None:
    """Create the project directory structure with documentation templates."""
    project_base = Path(f'projects/{project_id}')
    
    # Create main project directories
    directories = [
        'docs/api',
        'docs/architecture',
        'docs/meetings',
        'docs/requirements',
        'docs/technical',
        'docs/templates',
        'docs/testing',
        'docs/user_guides',
        'src',
        'tests'
    ]
    
    for directory in directories:
        (project_base / directory).mkdir(parents=True, exist_ok=True)
    
    # Copy template files from existing project
    template_source = Path('projects/stock_trading_ai/docs')
    if template_source.exists():
        for item in template_source.glob('**/*'):
            if item.is_file():
                relative_path = item.relative_to(template_source)
                destination = project_base / 'docs' / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)

@app.route('/')
def index() -> Union[str, Tuple[Response, int]]:
    try:
        projects = {str(p.id): {
            'name': p.name,
            'description': p.description,
            'status': p.status,
            'docs_path': p.docs_path
        } for p in Project.query.all()}
        return render_template('index.html', projects=projects)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to load index page',
            'details': str(e)
        }), 500

@app.route('/api/projects', methods=['GET', 'POST'])
def handle_projects() -> Union[Response, Tuple[Response, int]]:
    """Handle project listing and creation."""
    if request.method == 'GET':
        try:
            projects = {str(p.id): {
                'name': p.name,
                'description': p.description,
                'status': p.status,
                'docs_path': p.docs_path
            } for p in Project.query.all()}
            return jsonify({
                'success': True,
                'projects': projects
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    elif request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }), 400

            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Request body is empty'
                }), 400

            project_id = data.get('id')
            project_name = data.get('name')
            project_description = data.get('description')
            
            # Validate required fields
            if not all([project_id, project_name, project_description]):
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields'
                }), 400
                
            # Validate project ID format
            if not project_id.replace('-', '').replace('_', '').isalnum():
                return jsonify({
                    'success': False,
                    'error': 'Invalid project ID format'
                }), 400
                
            # Check if project ID already exists
            if Project.query.get(project_id):
                return jsonify({
                    'success': False,
                    'error': 'Project ID already exists'
                }), 400
                
            # Create project structure
            create_project_structure(project_id)
            
            # Create project in database
            new_project = Project(
                id=project_id,
                name=project_name,
                description=project_description,
                status='New',
                docs_path=f'/projects/{project_id}/docs'
            )
            db.session.add(new_project)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Project "{project_name}" created successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/api/project/<project_id>/context', methods=['GET'])
def get_project_context(project_id: str) -> Union[Response, Tuple[Response, int]]:
    """Get context for a specific project"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404

        # Load project documentation
        docs_path = project.docs_path.lstrip('/')
        
        # Get project README content
        readme_path = f"{docs_path}/README.md"
        try:
            with open(readme_path, 'r') as f:
                readme_content = f.read()
        except:
            readme_content = "Project documentation not available"

        # Get recent chat history
        recent_messages = ChatMessage.query.filter_by(project_id=project_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(10)\
            .all()
            
        chat_history = [{
            'agent_type': msg.agent_type,
            'message_type': msg.message_type,
            'content': msg.content,
            'context_summary': msg.context_summary,
            'timestamp': msg.created_at.isoformat()
        } for msg in reversed(recent_messages)]

        # Generate welcome message
        welcome_message = f"Welcome to Project {project.name}! I'm here to help with {project.description}"

        return jsonify({
            'success': True,
            'project': {
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'docs_path': project.docs_path
            },
            'context': {
                'readme': readme_content,
                'welcome_message': welcome_message,
                'chat_history': chat_history
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/interact', methods=['POST'])
def interact() -> Union[Response, Tuple[Response, int]]:
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is empty'
            }), 400

        user_input = data.get('message')
        agent_type = data.get('agent', 'pm')
        project_id = data.get('project')

        if not user_input:
            return jsonify({
                'success': False,
                'error': 'Message field is required'
            }), 400
        
        # Verify project exists
        project = Project.query.get(project_id) if project_id else None
        if project_id and not project:
            return jsonify({
                'success': False,
                'error': 'Invalid project ID'
            }), 400

        # Store user message
        if project:
            user_message = ChatMessage(
                project_id=project_id,
                agent_type=agent_type,
                message_type='user',
                content=user_input
            )
            db.session.add(user_message)
            db.session.commit()

        # Get project context
        project_context = None
        if project:
            project_context = {
                'project_name': project.name,
                'project_description': project.description,
                'project_status': project.status
            }

        # Map agent type to corresponding agent and their display names
        agents = {
            'pm': (project_manager, 'PM'),
            'dev': (developer, 'DEVELOPER'),
            'tester': (tester, 'TESTER'),
            'devops': (devops, 'DEVOPS'),
            'ba': (business_analyst, 'BUSINESS ANALYST'),
            'uxd': (ux_designer, 'UX DESIGNER')
        }

        selected_agent, display_name = agents.get(agent_type, (None, None))
        if not selected_agent:
            return jsonify({
                'success': False,
                'error': f'Invalid agent type: {agent_type}'
            }), 400

        # Track which agents have been used to prevent duplicates
        used_agents = set()
        
        # Process initial response with project context
        context = {'project': project_context} if project_context else None
        result = selected_agent.process_input(user_input, context)
        
        # Store agent response
        if project:
            agent_message = ChatMessage(
                project_id=project_id,
                agent_type=agent_type,
                message_type='agent',
                content=result['response'],
                context_summary=result.get('context_summary')
            )
            db.session.add(agent_message)
            db.session.commit()
        
        # Include context summary in response
        response = f"{display_name}: {result['response']}"
        if result.get('context_summary'):
            response = f"{display_name} (with context from: {result['context_summary']})\n{result['response']}"

        # Initialize collaboration tracking
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

        # Process collaboration chain
        if needs_collaboration:
            collaboration_queue = [(agent_type, collab_type) 
                               for collab_type in needs_collaboration]
            
            while collaboration_queue:
                parent_type, collab_type = collaboration_queue.pop(0)
                
                if collab_type in used_agents:
                    continue
                    
                collab_agent, collab_display_name = agents.get(collab_type, (None, None))
                if not collab_agent:
                    continue

                try:
                    # Prepare context with previous responses
                    collab_context = {
                        'previous_responses': {
                            agent_type: info['response']
                            for agent_type, info in collaboration_context.items()
                        }
                    }
                    
                    # Add project context
                    if project_context:
                        collab_context['project'] = project_context

                    # Add specific requests from parent agent
                    parent_requests = collaboration_context[parent_type].get('requests', {})
                    if collab_type in parent_requests:
                        collab_context['requests'] = parent_requests[collab_type]

                    # Get collaboration response
                    collab_result = collab_agent.process_input(user_input, collab_context)
                    
                    # Store collaborator response
                    if project:
                        collab_message = ChatMessage(
                            project_id=project_id,
                            agent_type=collab_type,
                            message_type='agent',
                            content=collab_result['response'],
                            context_summary=collab_result.get('context_summary')
                        )
                        db.session.add(collab_message)
                        db.session.commit()
                    
                    # Add to used agents
                    used_agents.add(collab_type)
                    
                    # Update collaboration context
                    collaboration_context[collab_type] = {
                        'response': collab_result['response'],
                        'display_name': collab_display_name,
                        'requests': collab_result.get('collaboration_requests', {}),
                        'context_summary': collab_result.get('context_summary')
                    }
                    
                    # Add formatted response
                    if collab_result.get('context_summary'):
                        response += f"\n\n{collab_display_name} (with context from: {collab_result['context_summary']})\n{collab_result['response']}"
                    else:
                        response += f"\n\n{collab_display_name}: {collab_result['response']}"

                    # Handle nested collaboration
                    nested_collaboration = collab_result.get('needs_collaboration', [])
                    if nested_collaboration:
                        for nested_type in nested_collaboration:
                            if nested_type not in used_agents:
                                collaboration_queue.append((collab_type, nested_type))

                except Exception as e:
                    continue

        return jsonify({
            'success': True,
            'response': response
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
