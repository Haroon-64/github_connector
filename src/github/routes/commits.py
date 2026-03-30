from typing import Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.error import AuthError, NotFoundError, RateLimitError
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
    try:
        return await service.get_commits(owner, repo, sha=sha)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail="Authentication failed")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Repository or commit not found")
    except RateLimitError as e:
        raise HTTPException(
            status_code=403,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(e.retry_after)} if e.retry_after else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
