from typing import Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, Query

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.github import CommitResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/repos/{owner}/{repo}/commits", response_model=List[CommitResponse])
async def list_commits(
    owner: str,
    repo: str,
    sha: Optional[str] = Query(None),
    service: GitHubService = Depends(github_provider(required=False)),
) -> Any:
    logger.debug("list_commits_request", owner=owner, repo=repo, sha=sha)
    return await service.get_commits(owner, repo, sha=sha)
