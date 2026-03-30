import structlog
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.error import (
    AuthError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
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
    try:
        return await service.get_repositories(username=username, org=org)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail="Authentication failed")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    except RateLimitError as e:
        raise HTTPException(
            status_code=403,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(e.retry_after)} if e.retry_after else None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=e.status, detail=str(e.details))
    except Exception as e:
        logger.error("list_repos_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/repos/{owner}/{repo}", response_model=RepositoryResponse)
async def get_repo(
    owner: str,
    repo: str,
    service: GitHubService = Depends(github_provider(required=False)),
) -> Any:
    logger.debug("get_repo_request", owner=owner, repo=repo)
    try:
        return await service.get_repository(owner, repo)
    except Exception as e:
        logger.error("get_repo_failed", owner=owner, repo=repo, error=str(e))
        if hasattr(e, "status"):
            raise
        raise HTTPException(status_code=500, detail=str(e))
