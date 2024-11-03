import os
from github import Github, GithubException, InputGitTreeElement
from typing import Dict, Union, Optional
import base64
from pathlib import Path

class GitHubIntegration:
    def __init__(self):
        """Initialize GitHub integration with token validation."""
        self.token = os.environ.get('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is not set")
        
        try:
            # Validate token by attempting to get user information
            self.github = Github(self.token)
            self.user = self.github.get_user()
            # Try to access user data to validate token
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

    def _handle_github_error(self, e: Exception) -> Dict[str, Union[bool, str]]:
        """Handle GitHub-related errors with user-friendly messages."""
        if isinstance(e, GithubException):
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
                    'error': f'GitHub API error: {str(e)}',
                    'error_code': 'API_ERROR'
                }
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'error_code': 'UNEXPECTED_ERROR'
        }

    def create_repository(self, name: str, description: Optional[str] = None, private: bool = False) -> Dict[str, Union[bool, str]]:
        """Create a new GitHub repository with enhanced error handling."""
        try:
            # Validate repository name
            if not name or not name.strip():
                return {
                    'success': False,
                    'error': 'Repository name cannot be empty',
                    'error_code': 'INVALID_NAME'
                }

            repo = self.user.create_repo(
                name=name,
                description=description or "AI Team Simulation using LangChain-powered agents",
                private=private,
                has_issues=True,
                has_wiki=True,
                has_downloads=True,
                auto_init=True
            )
            return {
                'success': True,
                'repo_url': repo.html_url,
                'clone_url': repo.clone_url,
                'message': 'Repository created successfully'
            }
        except Exception as e:
            return self._handle_github_error(e)

    def get_repository(self, name: str) -> Dict[str, Union[bool, str]]:
        """Get repository information with enhanced error handling."""
        try:
            if not name or not name.strip():
                return {
                    'success': False,
                    'error': 'Repository name cannot be empty',
                    'error_code': 'INVALID_NAME'
                }

            repo = self.user.get_repo(name)
            return {
                'success': True,
                'repo': repo,
                'repo_url': repo.html_url,
                'clone_url': repo.clone_url,
                'message': 'Repository found successfully'
            }
        except Exception as e:
            return self._handle_github_error(e)

    def initialize_repository(self, name: str, description: Optional[str] = None) -> Dict[str, Union[bool, str]]:
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
                **existing_repo,
                'message': 'Using existing repository'
            }
        return self.create_repository(name, description)

    def commit_files(self, repo_name: str, files: list, commit_message: str = "Initial commit") -> Dict[str, Union[bool, str]]:
        """Commit multiple files to the repository."""
        try:
            # Get repository
            repo_info = self.get_repository(repo_name)
            if not repo_info['success']:
                return repo_info
            
            repo = repo_info['repo']
            
            # Get the latest commit
            ref = repo.get_git_ref('heads/main')
            commit = repo.get_git_commit(ref.object.sha)
            base_tree = commit.tree

            # Create tree elements
            element_list = []
            for file_info in files:
                try:
                    with open(file_info['path'], 'rb') as f:
                        content = f.read()
                        # Create blob
                        blob = repo.create_git_blob(base64.b64encode(content).decode(), 'base64')
                        element = InputGitTreeElement(
                            path=file_info['path'],
                            mode='100644',
                            type='blob',
                            sha=blob.sha
                        )
                        element_list.append(element)
                except Exception as e:
                    print(f"Error processing file {file_info['path']}: {str(e)}")
                    continue

            # Create tree
            tree = repo.create_git_tree(element_list, base_tree)
            
            # Create commit
            parent = [commit]
            commit = repo.create_git_commit(commit_message, tree, parent)
            
            # Update reference
            ref.edit(commit.sha)

            return {
                'success': True,
                'message': f'Successfully committed {len(element_list)} files',
                'commit_sha': commit.sha
            }

        except Exception as e:
            return self._handle_github_error(e)
