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
            self.github = Github(self.token, timeout=60, retry=5)  # Increased timeout and retries
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
        """Check and handle GitHub API rate limits with improved error handling."""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                rate_limit = self.github.get_rate_limit()
                core_remaining = rate_limit.core.remaining
                core_limit = rate_limit.core.limit
                
                print(f"\nGitHub API Rate Limit Status:")
                print(f"Remaining requests: {core_remaining}/{core_limit}")
                
                if core_remaining < 20:  # Increased buffer from 10 to 20
                    reset_timestamp = rate_limit.core.reset.timestamp()
                    current_timestamp = time.time()
                    sleep_time = reset_timestamp - current_timestamp + 2  # Added 2 second buffer
                    
                    if sleep_time > 0:
                        print(f"\nRate limit approaching. Waiting {int(sleep_time)} seconds for reset...")
                        time.sleep(sleep_time)
                        print("Rate limit reset complete. Resuming operations...")
                        return True
                return False
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"\nWarning: Rate limit check failed after {max_retries} attempts - {str(e)}")
                    return False
                    
                wait_time = retry_delay * (2 ** attempt)
                print(f"\nRate limit check failed, retrying in {wait_time} seconds...")
                print(f"Error details: {str(e)}")
                time.sleep(wait_time)
        return False

    def _retry_operation(self, operation, max_retries=5, delay=5, operation_name="Operation"):
        """Retry an operation with exponential backoff and improved error handling."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                print(f"\nAttempting {operation_name}... (Attempt {attempt + 1}/{max_retries})")
                result = operation()
                print(f"{operation_name} completed successfully!")
                return result
                
            except RateLimitExceededException as e:
                print(f"\nRate limit exceeded during {operation_name}")
                if self._check_rate_limit():
                    continue
                last_error = e
                break
                
            except GithubException as e:
                if attempt == max_retries - 1:
                    print(f"\nFailed {operation_name} after all retries. Error: {str(e)}")
                    last_error = e
                    break
                    
                wait_time = delay * (2 ** attempt)
                print(f"\n{operation_name} failed, retrying in {wait_time} seconds...")
                print(f"Error details: {str(e)}")
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"\nUnexpected error in {operation_name}: {str(e)}")
                if attempt == max_retries - 1:
                    last_error = e
                    break
                    
                wait_time = delay * (2 ** attempt)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        if last_error:
            raise last_error
        return None

    def _handle_github_error(self, e: Exception) -> Mapping[str, Union[bool, str]]:
        """Handle GitHub-related errors with improved error reporting."""
        error_info = {
            'success': False,
            'error': str(e),
            'error_code': 'UNKNOWN_ERROR'
        }
        
        if isinstance(e, RateLimitExceededException):
            try:
                reset_time = self.github.rate_limiting_resettime
                wait_time = max(0, reset_time - int(time.time()))
                error_info.update({
                    'error': f'Rate limit exceeded. Reset in {wait_time} seconds.',
                    'error_code': 'RATE_LIMIT',
                    'reset_time': reset_time
                })
            except:
                error_info.update({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'error_code': 'RATE_LIMIT'
                })
                
        elif isinstance(e, GithubException):
            error_codes = {
                401: ('AUTH_FAILED', 'Authentication failed. Please check your GitHub token.'),
                403: ('PERMISSION_DENIED', 'Permission denied. Your token might not have the required permissions.'),
                404: ('NOT_FOUND', 'Resource not found. Please check the repository name and permissions.'),
                422: ('INVALID_REQUEST', 'Invalid request. Repository might already exist or name is invalid.'),
                500: ('GITHUB_ERROR', 'GitHub server error. Please try again later.'),
                503: ('SERVICE_UNAVAILABLE', 'GitHub service unavailable. Please try again later.')
            }
            
            error_code, error_message = error_codes.get(
                e.status, 
                ('API_ERROR', f'GitHub API error ({e.status}): {str(e)}')
            )
            
            error_info.update({
                'error': error_message,
                'error_code': error_code,
                'status_code': e.status
            })
            
        return error_info

    def commit_files(self, repo_name: str, files: list, commit_message: str = "Initial commit") -> Mapping[str, Union[bool, str, list]]:
        """Commit multiple files to the repository with improved error handling and timeout settings."""
        try:
            print("\nInitiating commit process...")
            print(f"Total files to process: {len(files)}")
            
            self._check_rate_limit()
            
            print("\nValidating repository access...")
            repo_info = self.get_repository(repo_name)
            if not repo_info['success']:
                return repo_info
            
            repo = self.user.get_repo(repo_name)
            processed_files = []
            
            print("\nFetching latest commit information...")
            try:
                ref = repo.get_git_ref('heads/main')
                commit = repo.get_git_commit(ref.object.sha)
                base_tree = commit.tree
                print("Using 'main' branch")
            except GithubException:
                try:
                    ref = repo.get_git_ref('heads/master')
                    commit = repo.get_git_commit(ref.object.sha)
                    base_tree = commit.tree
                    print("Using 'master' branch")
                except GithubException:
                    return {
                        'success': False,
                        'error': 'Could not find main or master branch',
                        'error_code': 'BRANCH_NOT_FOUND'
                    }
            
            element_list = []
            total_files = len(files)
            
            for index, file_info in enumerate(files, 1):
                try:
                    file_path = Path(file_info['path'])
                    print(f"\nProcessing file {index}/{total_files}: {file_path}")
                    
                    if not file_path.exists():
                        print(f"Warning: File not found - {file_path}")
                        continue
                    
                    file_size = file_path.stat().st_size
                    print(f"File size: {file_size / 1024:.2f}KB")
                    
                    if file_size > 50 * 1024 * 1024:
                        print(f"Warning: Skipping {file_path} - exceeds GitHub's 50MB limit")
                        continue
                    
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        
                        if not content.strip():
                            print(f"Warning: Skipping empty file - {file_path}")
                            continue
                        
                        print(f"Creating blob for {file_path}...")
                        blob = self._retry_operation(
                            lambda: repo.create_git_blob(base64.b64encode(content).decode(), 'base64'),
                            operation_name=f"Blob creation for {file_path}",
                            max_retries=5,
                            delay=10
                        )
                        
                        if blob:
                            element = InputGitTreeElement(
                                path=str(file_path),
                                mode='100644',
                                type='blob',
                                sha=blob.sha
                            )
                            element_list.append(element)
                            processed_files.append(str(file_path))
                            print(f"Successfully processed: {file_path}")
                        else:
                            print(f"Failed to create blob for {file_path}")
                            
                except Exception as e:
                    print(f"Error processing file {file_info['path']}: {str(e)}")
                    continue
            
            if not element_list:
                return {
                    'success': False,
                    'error': 'No valid files to commit',
                    'error_code': 'NO_FILES'
                }
            
            print("\nCreating Git tree...")
            tree = self._retry_operation(
                lambda: repo.create_git_tree(element_list, base_tree),
                operation_name="Tree creation",
                max_retries=5,
                delay=10
            )
            
            if not tree:
                return {
                    'success': False,
                    'error': 'Failed to create tree after multiple attempts',
                    'error_code': 'TREE_CREATE_FAILED'
                }
            
            print("\nCreating commit...")
            new_commit = self._retry_operation(
                lambda: repo.create_git_commit(commit_message, tree, [commit]),
                operation_name="Commit creation",
                max_retries=5,
                delay=10
            )
            
            if not new_commit:
                return {
                    'success': False,
                    'error': 'Failed to create commit after multiple attempts',
                    'error_code': 'COMMIT_CREATE_FAILED'
                }
            
            print("\nUpdating repository reference...")
            if not self._retry_operation(
                lambda: ref.edit(new_commit.sha),
                operation_name="Reference update",
                max_retries=5,
                delay=10
            ):
                return {
                    'success': False,
                    'error': 'Failed to update reference after multiple attempts',
                    'error_code': 'REF_UPDATE_FAILED'
                }
            
            return {
                'success': True,
                'message': f'Successfully committed {len(processed_files)} files',
                'commit_sha': str(new_commit.sha),
                'processed_files': processed_files
            }
        
        except Exception as e:
            return self._handle_github_error(e)

    def get_repository(self, name: str) -> Mapping[str, Union[bool, str, Mapping]]:
        """Get repository information with improved error handling."""
        try:
            self._check_rate_limit()
            
            if not name or not name.strip():
                return {
                    'success': False,
                    'error': 'Repository name cannot be empty',
                    'error_code': 'INVALID_NAME'
                }
            
            repo = self._retry_operation(
                lambda: self.user.get_repo(name),
                operation_name="Repository fetch",
                max_retries=5,
                delay=5
            )
            
            if not repo:
                return {
                    'success': False,
                    'error': 'Failed to get repository after multiple attempts',
                    'error_code': 'GET_REPO_FAILED'
                }
            
            repo_info = {
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
        """Initialize or get existing repository with improved error handling."""
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
            
        try:
            repo = self._retry_operation(
                lambda: self.user.create_repo(
                    name=name,
                    description=description or "AI Team Simulation using LangChain-powered agents",
                    private=False,
                    has_issues=True,
                    has_wiki=True,
                    has_downloads=True,
                    auto_init=True
                ),
                operation_name="Repository creation",
                max_retries=5,
                delay=5
            )
            
            if not repo:
                return {
                    'success': False,
                    'error': 'Failed to create repository after multiple attempts',
                    'error_code': 'CREATE_FAILED'
                }
            
            repo_info = {
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
            
            return {
                'success': True,
                'repo_info': repo_info,
                'repo_url': str(repo.html_url),
                'clone_url': str(repo.clone_url),
                'message': 'Repository created successfully'
            }
            
        except Exception as e:
            return self._handle_github_error(e)
