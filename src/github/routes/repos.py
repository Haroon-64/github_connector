from typing import Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, Query

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.github import RepositoryResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get(
    "/repos",
    response_model=List[RepositoryResponse],
    description="List repos by user or org, return current users' if none provided",
)
async def list_repos(
    username: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    service: GitHubService = Depends(github_provider(required=False)),
) -> Any:
    logger.debug("list_repos_request", username=username, org=org)
    return await service.get_repositories(username=username, org=org)


@router.get("/repos/{owner}/{repo}", response_model=RepositoryResponse)
async def get_repo(
    owner: str,
    repo: str,
    service: GitHubService = Depends(github_provider(required=False)),
) -> Any:
    logger.debug("get_repo_request", owner=owner, repo=repo)
    return await service.get_repository(owner, repo)
