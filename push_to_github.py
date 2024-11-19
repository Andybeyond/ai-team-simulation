from github_integration import GitHubIntegration
from pathlib import Path
import sys
import time

def get_all_project_files():
    """Get all project files including source, templates, static, and documentation."""
    files = []
    
    # Python source files
    python_files = [
        'main.py', 'app.py', 'github_integration.py', 
        'test_github_integration.py', 'populate_repository.py',
        'push_to_github.py'
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
    
    # Documentation files
    doc_files = [
        'docs/README.md',
        'docs/api/README.md',
        'docs/architecture/README.md',
        'docs/meetings/README.md',
        'docs/requirements/README.md',
        'docs/technical/README.md',
        'docs/templates/meeting_notes.md',
        'docs/templates/technical_doc.md',
        'docs/testing/README.md',
        'docs/user_guides/README.md',
        'docs/.gitkeep'
    ]
    
    # Project documentation files
    project_doc_files = [
        'projects/README.md',
        'projects/stock_trading_ai/README.md',
        'projects/stock_trading_ai/docs/README.md',
        'projects/stock_trading_ai/docs/api/README.md',
        'projects/stock_trading_ai/docs/architecture/README.md',
        'projects/stock_trading_ai/docs/requirements/README.md',
        'projects/stock_trading_ai/docs/technical/README.md',
        'projects/stock_trading_ai/docs/testing/README.md',
        'projects/stock_trading_ai/docs/user_guides/README.md'
    ]
    
    # Configuration files
    config_files = [
        '.replit', 'replit.nix', 'requirements.txt',
        'pyproject.toml', '.gitignore',
        'README.md'
    ]
    
    all_files = (python_files + agent_files + template_files + 
                static_files + doc_files + project_doc_files + config_files)
    
    for file_path in all_files:
        path = Path(file_path)
        if path.exists():
            # Skip files larger than 50MB (GitHub's limit)
            if path.stat().st_size > 50 * 1024 * 1024:
                print(f"Warning: Skipping {file_path} - file size exceeds GitHub's limit")
                continue
                
            files.append({
                'path': file_path,
                'type': path.suffix[1:] if path.suffix else 'txt'
            })
        else:
            print(f"Warning: File not found - {file_path}")
    
    return files

def print_progress(current, total, message=""):
    """Print progress bar with message."""
    bar_length = 50
    progress = float(current) / total
    filled = int(bar_length * progress)
    bar = '=' * filled + '-' * (bar_length - filled)
    sys.stdout.write(f'\r[{bar}] {int(progress * 100)}% {message}')
    sys.stdout.flush()

def main():
    """Main function to push files to GitHub repository."""
    try:
        github = GitHubIntegration()
        repo_name = 'ai-team-simulation'
        
        # Get all project files
        print("Gathering project files...")
        files = get_all_project_files()
        total_files = len(files)
        
        if not files:
            print("No files found to push!")
            return False
            
        print(f"Found {total_files} files to push")
        
        # Initialize repository
        print("\nInitializing repository...")
        init_result = github.initialize_repository(repo_name)
        if not init_result['success']:
            print(f"Failed to initialize repository: {init_result.get('error', 'Unknown error')}")
            return False
        
        print(f"Repository initialized: {init_result['repo_url']}")
        
        # Commit files in smaller batches to avoid timeout
        batch_size = 10
        total_batches = (total_files + batch_size - 1) // batch_size
        processed_files = []
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_files)
            batch_files = files[start_idx:end_idx]
            
            print(f"\nPushing batch {batch_num + 1}/{total_batches} ({len(batch_files)} files)...")
            
            commit_result = github.commit_files(
                repo_name=repo_name,
                files=batch_files,
                commit_message=f"Update project files (batch {batch_num + 1}/{total_batches})"
            )
            
            if commit_result['success']:
                processed_files.extend(commit_result.get('processed_files', []))
                print_progress(len(processed_files), total_files, 
                             f" - {len(processed_files)}/{total_files} files pushed")
            else:
                print(f"\nError in batch {batch_num + 1}: {commit_result.get('error', 'Unknown error')}")
                continue
            
            # Small delay between batches to avoid rate limiting
            if batch_num < total_batches - 1:
                time.sleep(2)
        
        if processed_files:
            print("\n\nRepository push completed successfully!")
            print(f"Total files pushed: {len(processed_files)}/{total_files}")
            print(f"Repository URL: {init_result['repo_url']}")
            return True
        else:
            print("\nNo files were successfully pushed")
            return False
            
    except Exception as e:
        print(f"\nError during GitHub push: {str(e)}")
        return False

if __name__ == '__main__':
    main()
