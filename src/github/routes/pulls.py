from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.error import AuthError, NotFoundError, RateLimitError, ValidationError
from src.models.github import PRRequest, PRResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/repos/{owner}/{repo}/pulls", response_model=PRResponse)
async def create_pull(
    owner: str,
    repo: str,
    pull: PRRequest,
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug("create_pull_request", owner=owner, repo=repo)
    try:
        return await service.create_pull_request(owner, repo, pull.model_dump())
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail="Authentication failed")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Repository not found")
    except RateLimitError as e:
        raise HTTPException(
            status_code=403,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(e.retry_after)} if e.retry_after else None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=e.status, detail=str(e.details))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
