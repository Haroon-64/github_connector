from typing import Any

import structlog
from fastapi import APIRouter, Body, Depends

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.github import PRRequest, PRResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/repos/{owner}/{repo}/pulls", response_model=PRResponse)
async def create_pull(
    owner: str,
    repo: str,
    pull: PRRequest = Body(..., description="The pull request information to create"),
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug("create_pull_request", owner=owner, repo=repo)
    return await service.create_pull_request(owner, repo, pull.model_dump())
