from github_integration import GitHubIntegration
from pathlib import Path

def get_all_project_files():
    """Get all relevant project files."""
    files = []
    
    # Python files
    python_files = [
        'main.py', 'app.py', 'github_integration.py', 
        'test_github_integration.py'
    ]
    
    # Agent files
    agent_files = [
        'agents/__init__.py', 'agents/base_agent.py',
        'agents/project_manager.py', 'agents/developer.py',
        'agents/tester.py', 'agents/devops.py',
        'agents/business_analyst.py', 'agents/ux_designer.py'
    ]
    
    # Template files
    template_files = [
        'templates/index.html', 'templates/agent_relationships.html',
        'templates/github_init.html'
    ]
    
    # Static files
    static_files = [
        'static/css/custom.css',
        'static/js/main.js',
        'static/js/agent_graph.js'
    ]
    
    # Configuration files
    config_files = [
        '.replit', 'replit.nix', 'pyproject.toml', 'uv.lock'
    ]
    
    all_files = python_files + agent_files + template_files + static_files + config_files
    
    for file_path in all_files:
        if Path(file_path).exists():
            files.append({
                'path': file_path,
                'type': Path(file_path).suffix[1:]  # Get file extension without dot
            })
    
    return files

def main():
    """Main function to populate the repository."""
    github = GitHubIntegration()
    repo_name = 'ai-team-simulation'
    
    # Get all project files
    files = get_all_project_files()
    
    # Initialize repository
    init_result = github.initialize_repository(repo_name)
    if not init_result['success']:
        print(f"Failed to initialize repository: {init_result['error']}")
        return False
    
    # Commit files
    commit_result = github.commit_files(
        repo_name=repo_name,
        files=files,
        commit_message="Initial commit: Add all project files"
    )
    
    if commit_result['success']:
        print(f"Successfully populated repository: {init_result['repo_url']}")
        print(f"Committed {len(files)} files")
        return True
    else:
        print(f"Failed to commit files: {commit_result['error']}")
        return False

if __name__ == '__main__':
    main()
