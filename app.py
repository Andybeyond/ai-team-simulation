import os
import sys
from flask import Flask, render_template, jsonify, request
from database import db, init_db, Project, ChatMessage
from agents import (
    ProjectManagerAgent, DeveloperAgent, TesterAgent, 
    DevOpsAgent, BusinessAnalystAgent, UXDesignerAgent
)
from config import get_config

app = Flask(__name__)

# Initialize agents
agents = {
    'pm': (ProjectManagerAgent(), 'PM'),
    'dev': (DeveloperAgent(), 'DEVELOPER'),
    'tester': (TesterAgent(), 'TESTER'),
    'devops': (DevOpsAgent(), 'DEVOPS'),
    'ba': (BusinessAnalystAgent(), 'BUSINESS ANALYST'),
    'uxd': (UXDesignerAgent(), 'UX DESIGNER')
}

# Initialize database
init_db(app)

@app.route('/')
def index():
    projects = {}
    try:
        all_projects = Project.query.all()
        for project in all_projects:
            projects[project.id] = {
                'name': project.name,
                'description': project.description,
                'status': project.status
            }
    except Exception as e:
        print(f"Error loading projects: {e}")
    
    return render_template('index.html', projects=projects)

@app.route('/relationships')
def agent_relationships():
    return render_template('agent_relationships.html')

@app.route('/api/projects', methods=['GET', 'POST'])
def handle_projects():
    if request.method == 'POST':
        try:
            data = request.get_json()
            project = Project(
                id=data['id'],
                name=data['name'],
                description=data.get('description', '')
            )
            db.session.add(project)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Project created successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    else:  # GET
        try:
            projects = {}
            all_projects = Project.query.all()
            for project in all_projects:
                projects[project.id] = {
                    'name': project.name,
                    'description': project.description,
                    'status': project.status
                }
            return jsonify({
                'success': True,
                'projects': projects
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/api/project/<project_id>/context')
def get_project_context(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
            
        context = {
            'welcome_message': f'Hello! How can I assist you with the {project.name} project today?'
        }
            
        return jsonify({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status
            },
            'context': context
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/interact', methods=['POST'])
def interact():
    try:
        data = request.get_json()
        message = data.get('message')
        agent_type = data.get('agent', 'pm')
        project_id = data.get('project')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400
            
        # Get project context if project_id is provided
        project = None
        project_context = None
        if project_id:
            project = Project.query.get(project_id)
            if project:
                project_context = {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'status': project.status
                }
        
        # Store user message if project exists
        if project:
            user_message = ChatMessage(
                project_id=project_id,
                agent_type=agent_type,
                message_type='user',
                content=message
            )
            db.session.add(user_message)
            db.session.commit()
        
        # Get initial agent response
        agent, display_name = agents.get(agent_type, (None, None))
        if not agent:
            return jsonify({
                'success': False,
                'error': f'Invalid agent type: {agent_type}'
            }), 400
            
        # Process message with context
        result = agent.process_input(message, {'project': project_context} if project_context else None)
        
        # Store agent response if project exists
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
        
        # Format initial response
        response = result['response']
        
        # Track collaboration context
        collaboration_context = {
            agent_type: {
                'response': result['response'],
                'display_name': display_name,
                'requests': result.get('collaboration_requests', {}),
                'context_summary': result.get('context_summary')
            }
        }
        
        # Handle collaboration needs
        if result.get('needs_collaboration'):
            collaboration_queue = [(agent_type, collab_type) for collab_type in result['needs_collaboration']]
            used_agents = {agent_type}
            
            while collaboration_queue:
                parent_type, collab_type = collaboration_queue.pop(0)
                
                # Process each collaboration request
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
                    collab_result = collab_agent.process_input(message, collab_context)
                    
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
    config = get_config()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=config.DEBUG)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)