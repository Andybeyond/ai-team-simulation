import os
from github import Github, GithubException, InputGitTreeElement, RateLimitExceededException
from typing import Dict, Union, Optional, Mapping
import base64
from pathlib import Path
import time

class GitHubIntegration:
    def __init__(self):
        """Initialize GitHub integration with token validation."""
        self.token = os.environ.get('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is not set")
        
        try:
            self.github = Github(self.token)
            self.user = self.github.get_user()
            # Validate token by attempting to get user information
            self.user.login
        except GithubException as e:
            if e.status == 401:
                raise ValueError("Invalid GitHub token: Authentication failed")
            elif e.status == 403:
                raise ValueError("GitHub token has insufficient permissions")
            else:
                raise ValueError(f"GitHub token validation failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to initialize GitHub integration: {str(e)}")

    def _check_rate_limit(self) -> bool:
        """Check and handle GitHub API rate limits."""
        try:
            rate_limit = self.github.get_rate_limit()
            core_remaining = rate_limit.core.remaining
            
            if core_remaining < 10:  # Buffer of 10 requests
                reset_timestamp = rate_limit.core.reset.timestamp()
                current_timestamp = time.time()
                sleep_time = reset_timestamp - current_timestamp + 1
                
                if sleep_time > 0:
                    print(f"\nRate limit approaching, waiting {int(sleep_time)} seconds...")
                    time.sleep(sleep_time)
                    return True
            return False
        except Exception as e:
            print(f"Warning: Rate limit check failed - {str(e)}")
            return False

    def _handle_github_error(self, e: Exception) -> Mapping[str, Union[bool, str]]:
        """Handle GitHub-related errors with user-friendly messages."""
        if isinstance(e, RateLimitExceededException):
            reset_time = self.github.rate_limiting_resettime
            wait_time = reset_time - int(time.time())
            return {
                'success': False,
                'error': f'Rate limit exceeded. Reset in {wait_time} seconds.',
                'error_code': 'RATE_LIMIT'
            }
        elif isinstance(e, GithubException):
            if e.status == 401:
                return {
                    'success': False,
                    'error': 'Authentication failed. Please check your GitHub token.',
                    'error_code': 'AUTH_FAILED'
                }
            elif e.status == 403:
                return {
                    'success': False,
                    'error': 'Permission denied. Your token might not have the required permissions.',
                    'error_code': 'PERMISSION_DENIED'
                }
            elif e.status == 422:
                return {
                    'success': False,
                    'error': 'Repository already exists or invalid repository name.',
                    'error_code': 'INVALID_REPO'
                }
            else:
                return {
                    'success': False,
                    'error': f'GitHub API error ({e.status}): {str(e)}',
                    'error_code': 'API_ERROR'
                }
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'error_code': 'UNEXPECTED_ERROR'
        }

    def _serialize_repo_info(self, repo) -> Mapping[str, Union[str, bool, None]]:
        """Serialize repository information into a JSON-friendly format."""
        return {
            'name': str(repo.name),
            'full_name': str(repo.full_name),
            'description': str(repo.description) if repo.description else '',
            'html_url': str(repo.html_url),
            'clone_url': str(repo.clone_url),
            'ssh_url': str(repo.ssh_url),
            'default_branch': str(repo.default_branch),
            'private': bool(repo.private),
            'created_at': repo.created_at.isoformat() if repo.created_at else None,
            'updated_at': repo.updated_at.isoformat() if repo.updated_at else None
        }

    def create_repository(self, name: str, description: Optional[str] = None, private: bool = False) -> Mapping[str, Union[bool, str, Mapping]]:
        """Create a new GitHub repository with enhanced error handling."""
        try:
            self._check_rate_limit()
            
            if not name or not name.strip():
                return {
                    'success': False,
                    'error': 'Repository name cannot be empty',
                    'error_code': 'INVALID_NAME'
                }

            # Create repository
            repo = self.user.create_repository(
                name=name,
                description=description or "AI Team Simulation using LangChain-powered agents",
                private=private,
                has_issues=True,
                has_wiki=True,
                has_downloads=True,
                auto_init=True
            )
            
            repo_info = self._serialize_repo_info(repo)
            return {
                'success': True,
                'repo_info': repo_info,
                'repo_url': str(repo.html_url),
                'clone_url': str(repo.clone_url),
                'message': 'Repository created successfully'
            }
        except Exception as e:
            return self._handle_github_error(e)

    def get_repository(self, name: str) -> Mapping[str, Union[bool, str, Mapping]]:
        """Get repository information with enhanced error handling."""
        try:
            self._check_rate_limit()
            
            if not name or not name.strip():
                return {
                    'success': False,
                    'error': 'Repository name cannot be empty',
                    'error_code': 'INVALID_NAME'
                }

            repo = self.user.get_repo(name)
            repo_info = self._serialize_repo_info(repo)
            
            return {
                'success': True,
                'repo_info': repo_info,
                'repo_url': str(repo.html_url),
                'clone_url': str(repo.clone_url),
                'message': 'Repository found successfully'
            }
        except Exception as e:
            return self._handle_github_error(e)

    def initialize_repository(self, name: str, description: Optional[str] = None) -> Mapping[str, Union[bool, str, Mapping]]:
        """Initialize or get existing repository with enhanced error handling."""
        if not name or not name.strip():
            return {
                'success': False,
                'error': 'Repository name cannot be empty',
                'error_code': 'INVALID_NAME'
            }

        existing_repo = self.get_repository(name)
        if existing_repo['success']:
            return {
                'success': True,
                'repo_info': existing_repo['repo_info'],
                'repo_url': existing_repo['repo_url'],
                'clone_url': existing_repo['clone_url'],
                'message': 'Using existing repository'
            }
        return self.create_repository(name, description)

    def commit_files(self, repo_name: str, files: list, commit_message: str = "Initial commit") -> Mapping[str, Union[bool, str, list]]:
        """Commit multiple files to the repository with improved error handling and progress tracking."""
        try:
            self._check_rate_limit()
            
            # Get repository
            repo_info = self.get_repository(repo_name)
            if not repo_info['success']:
                return repo_info
            
            repo = self.user.get_repo(repo_name)
            processed_files = []
            
            try:
                # Get the latest commit
                ref = repo.get_git_ref('heads/main')
                commit = repo.get_git_commit(ref.object.sha)
                base_tree = commit.tree
            except GithubException:
                # If ref doesn't exist, try master branch
                try:
                    ref = repo.get_git_ref('heads/master')
                    commit = repo.get_git_commit(ref.object.sha)
                    base_tree = commit.tree
                except GithubException:
                    return {
                        'success': False,
                        'error': 'Could not find main or master branch',
                        'error_code': 'BRANCH_NOT_FOUND'
                    }

            # Create tree elements with detailed error handling
            element_list = []
            for file_info in files:
                try:
                    file_path = Path(file_info['path'])
                    if not file_path.exists():
                        print(f"Warning: File not found - {file_path}")
                        continue
                        
                    # Skip files larger than GitHub's limit (100MB)
                    if file_path.stat().st_size > 100 * 1024 * 1024:
                        print(f"Warning: Skipping {file_path} - exceeds GitHub's 100MB limit")
                        continue
                        
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        
                        # Skip empty files
                        if not content.strip():
                            print(f"Warning: Skipping empty file - {file_path}")
                            continue
                        
                        # Check rate limit before creating blob
                        if self._check_rate_limit():
                            print("Resumed after rate limit wait")
                        
                        try:
                            # Create blob with retries
                            max_retries = 3
                            retry_count = 0
                            while retry_count < max_retries:
                                try:
                                    blob = repo.create_git_blob(base64.b64encode(content).decode(), 'base64')
                                    break
                                except GithubException as e:
                                    retry_count += 1
                                    if retry_count == max_retries:
                                        raise e
                                    print(f"Retrying blob creation for {file_path} (attempt {retry_count + 1})")
                                    time.sleep(2)
                            
                            element = InputGitTreeElement(
                                path=str(file_path),
                                mode='100644',
                                type='blob',
                                sha=blob.sha
                            )
                            element_list.append(element)
                            processed_files.append(str(file_path))
                            print(f"Successfully processed: {file_path}")
                        except GithubException as e:
                            print(f"Error creating blob for {file_path}: {str(e)}")
                            continue
                            
                except Exception as e:
                    print(f"Error processing file {file_info['path']}: {str(e)}")
                    continue

            if not element_list:
                return {
                    'success': False,
                    'error': 'No valid files to commit',
                    'error_code': 'NO_FILES'
                }

            # Create tree and commit with error handling
            try:
                # Check rate limit before creating tree
                if self._check_rate_limit():
                    print("Resumed after rate limit wait")
                    
                tree = repo.create_git_tree(element_list, base_tree)
                
                # Check rate limit before creating commit
                if self._check_rate_limit():
                    print("Resumed after rate limit wait")
                    
                parent = [commit]
                commit = repo.create_git_commit(commit_message, tree, parent)
                
                # Check rate limit before updating reference
                if self._check_rate_limit():
                    print("Resumed after rate limit wait")
                    
                ref.edit(commit.sha)
            except GithubException as e:
                return self._handle_github_error(e)

            return {
                'success': True,
                'message': f'Successfully committed {len(element_list)} files',
                'commit_sha': str(commit.sha),
                'processed_files': processed_files
            }

        except Exception as e:
            return self._handle_github_error(e)
