from github_integration import GitHubIntegration
from pathlib import Path
import sys
import time

def get_all_project_files():
    """Get all project files including source, templates, static, and documentation."""
    print("\nScanning project files...")
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
    
    print("\nValidating files...")
    total_size = 0
    for file_path in all_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            total_size += size
            
            # Skip files larger than 50MB (GitHub's limit)
            if size > 50 * 1024 * 1024:
                print(f"Warning: Skipping {file_path} - file size ({size / 1024 / 1024:.2f}MB) exceeds GitHub's limit")
                continue
                
            files.append({
                'path': file_path,
                'type': path.suffix[1:] if path.suffix else 'txt',
                'size': size
            })
        else:
            print(f"Warning: File not found - {file_path}")
    
    print(f"\nTotal files found: {len(files)}")
    print(f"Total size: {total_size / 1024 / 1024:.2f}MB")
    return files

def print_progress(current, total, message=""):
    """Print progress bar with message."""
    bar_length = 50
    progress = float(current) / total
    filled = int(bar_length * progress)
    bar = '=' * filled + '-' * (bar_length - filled)
    sys.stdout.write(f'\r[{bar}] {int(progress * 100)}% {message}')
    sys.stdout.flush()

def push_batch(github, repo_name, files, batch_num, total_batches):
    """Push a batch of files with retries and detailed progress tracking."""
    max_retries = 3
    retry_delay = 10  # Increased initial delay
    
    print(f"\nPreparing batch {batch_num}/{total_batches}")
    print("Files in this batch:")
    batch_size = sum(f.get('size', 0) for f in files) / 1024 / 1024
    for file_info in files:
        print(f"- {file_info['path']} ({file_info.get('size', 0) / 1024:.2f}KB)")
    print(f"Batch size: {batch_size:.2f}MB")
    
    for attempt in range(max_retries):
        try:
            print(f"\nPushing batch {batch_num}/{total_batches} (Attempt {attempt + 1}/{max_retries})")
            
            commit_result = github.commit_files(
                repo_name=repo_name,
                files=files,
                commit_message=f"Update project files (batch {batch_num}/{total_batches})"
            )
            
            if commit_result['success']:
                print(f"\nBatch {batch_num} successfully pushed!")
                return commit_result
            
            print(f"\nError in batch {batch_num}: {commit_result.get('error', 'Unknown error')}")
            if attempt < max_retries - 1:
                print(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            
        except Exception as e:
            print(f"\nError in batch {batch_num}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                retry_delay *= 2
    
    return None

def main():
    """Main function to push files to GitHub repository."""
    try:
        print("\nInitializing GitHub integration...")
        github = GitHubIntegration()
        repo_name = 'ai-team-simulation'
        
        print("\nGathering project files...")
        files = get_all_project_files()
        total_files = len(files)
        
        if not files:
            print("\nNo files found to push!")
            return False
        
        print("\nInitializing repository...")
        init_result = github.initialize_repository(repo_name)
        if not init_result['success']:
            print(f"\nFailed to initialize repository: {init_result.get('error', 'Unknown error')}")
            return False
        
        print(f"\nRepository initialized: {init_result['repo_url']}")
        
        # Further reduced batch size and improved progress tracking
        batch_size = 2  # Reduced from 3 to 2 files per batch
        total_batches = (total_files + batch_size - 1) // batch_size
        processed_files = []
        failed_batches = []
        
        print(f"\nPreparing to push {total_files} files in {total_batches} batches")
        print(f"Batch size: {batch_size} files per batch")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_files)
            batch_files = files[start_idx:end_idx]
            
            result = push_batch(github, repo_name, batch_files, batch_num + 1, total_batches)
            
            if result and result['success']:
                processed_files.extend(result.get('processed_files', []))
                print_progress(len(processed_files), total_files, 
                             f" - {len(processed_files)}/{total_files} files pushed")
            else:
                print(f"\nBatch {batch_num + 1} failed after all retries")
                failed_batches.append((batch_num + 1, batch_files))
            
            # Increased delay between batches
            if batch_num < total_batches - 1:
                delay = 10  # Increased from 5 to 10 seconds
                print(f"\nWaiting {delay} seconds before next batch...")
                time.sleep(delay)
        
        # Report results
        print("\n\nRepository Push Summary")
        print("=" * 50)
        print(f"Total files processed: {len(processed_files)}/{total_files}")
        print(f"Repository URL: {init_result['repo_url']}")
        
        if failed_batches:
            print("\nFailed Batches:")
            print("=" * 50)
            for batch_num, failed_files in failed_batches:
                print(f"\nBatch {batch_num}:")
                for file_info in failed_files:
                    print(f"- {file_info['path']}")
            return False
            
        print("\nPush completed successfully!")
        return True
            
    except Exception as e:
        print(f"\nError during GitHub push: {str(e)}")
        return False

if __name__ == '__main__':
    main()
