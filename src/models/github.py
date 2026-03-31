from typing import Any, List, Optional

from pydantic import BaseModel, Field


class UserShort(BaseModel):
    """Simplified GitHub user representation."""

    login: str
    id: int
    avatar_url: str
    html_url: str
    type: str


class GitHubBaseModel(BaseModel):
    """Base model for GitHub objects with common fields."""

    id: int
    url: Optional[str] = None
    html_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RepositoryResponse(GitHubBaseModel):
    name: str
    full_name: str
    private: bool
    owner: UserShort
    description: Optional[str] = None
    fork: bool
    pushed_at: Optional[str] = None


class IssueRequest(BaseModel):
    title: str = Field(..., description="The title of the issue")
    body: str = Field("", description="The description or body contents of the issue")
    assignees: List[str] = Field(
        [], description="List of GitHub usernames to assign to the issue"
    )
    labels: List[str] = Field(
        [], description="List of label names to add to the issue"
    )


class IssueResponse(GitHubBaseModel):
    number: int
    title: str
    state: str
    user: UserShort
    body: Optional[str] = None
    pull_request: Optional[dict[str, Any]] = None


class PRRequest(BaseModel):
    title: str = Field("", description="The title of the pull request")
    head: str = Field(
        "newbranch",
        description="The name of the branch where your changes are implemented",
    )
    base: str = Field(
        "master",
        description="The name of the branch you want your changes pulled into",
    )
    body: str = Field("", description="The contents or description of the pull request")


class PRResponse(GitHubBaseModel):
    number: int
    title: str
    state: str
    body: Optional[str] = None
    user: UserShort
    head: dict[str, Any]
    base: dict[str, Any]


class CommitResponse(BaseModel):
    sha: str
    commit: dict[str, Any]
    author: Optional[UserShort] = None
    html_url: str
    url: Optional[str] = None
