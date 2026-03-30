from typing import Any, List, Optional

from pydantic import BaseModel


class RepositoryResponse(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    owner: dict[str, Any]
    html_url: str
    description: Optional[str] = None
    fork: bool
    url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    pushed_at: Optional[str] = None


class IssueRequest(BaseModel):
    title: str
    body: Optional[str] = None
    assignees: Optional[List[str]] = None
    labels: Optional[List[str]] = None


class IssueResponse(BaseModel):
    id: int
    number: int
    title: str
    state: str
    user: dict[str, Any]
    body: Optional[str] = None
    pull_request: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PRRequest(BaseModel):
    title: str
    head: str
    base: str
    body: Optional[str] = None


class PRResponse(BaseModel):
    id: int
    number: int
    title: str
    state: str
    body: Optional[str] = None
    user: dict[str, Any]
    head: dict[str, Any]
    base: dict[str, Any]
    html_url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CommitResponse(BaseModel):
    sha: str
    commit: dict[str, Any]
    author: Optional[dict[str, Any]] = None
    html_url: str
    url: Optional[str] = None
