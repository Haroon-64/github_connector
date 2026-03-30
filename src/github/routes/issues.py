from typing import Any, List

import structlog
from fastapi import APIRouter, Depends, HTTPException

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.github import IssueRequest, IssueResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse)
async def create_issue(
    owner: str,
    repo: str,
    issue: IssueRequest,
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug("create_issue_request", owner=owner, repo=repo)
    return await service.create_issue(owner, repo, issue.model_dump())


@router.get("/repos/{owner}/{repo}/issues", response_model=List[IssueResponse])
async def list_issues(
    owner: str,
    repo: str,
    service: GitHubService = Depends(github_provider(required=False)),
) -> Any:
    logger.debug("list_issues_request", owner=owner, repo=repo)
    return await service.list_issues(owner, repo)
