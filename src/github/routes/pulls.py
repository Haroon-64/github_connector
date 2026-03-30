from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies.github import get_github_service
from src.github.service import GitHubService
from src.models.error import AuthError, NotFoundError, RateLimitError, ValidationError
from src.models.github import PullRequestRequest, PullRequestResponse

router = APIRouter()


@router.post("/repos/{owner}/{repo}/pulls", response_model=PullRequestResponse)
async def create_pull(
    owner: str,
    repo: str,
    pull: PullRequestRequest,
    service: GitHubService = Depends(get_github_service),
) -> Any:
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
