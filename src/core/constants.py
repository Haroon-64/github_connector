"""Centralized constants for the application."""

# GitHub OAuth Scopes
# user:email - Access primary email address
# repo - Full control of private and public repositories
# read:user - Read access to user profile data
GITHUB_SCOPES = ["user:email", "repo", "read:user"]

# Mapping of endpoints to their required scopes for documentation and future.
ENDPOINT_SCOPE_MAPPING = {
    "list_repos": ["repo"],
    "create_issue": ["repo"],
    "list_issues": ["repo"],
    "create_pull_request": ["repo"],
    "get_commits": ["repo"],
    "get_me": ["read:user", "user:email"],
}
