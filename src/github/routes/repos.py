from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.dependencies.github import get_github_client
from src.github.client import GitHubClient
from src.models.error import (
    AuthError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from src.models.github import RepositoryResponse

router = APIRouter()


@router.get("/repos", response_model=List[RepositoryResponse])
async def list_repos(
    username: Optional[str] = Query(None),
    org: Optional[str] = Query(None),
    client: GitHubClient = Depends(get_github_client),
) -> Any:
    try:
        return await client.get_repositories(username=username, org=org)
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos/{owner}", response_model=List[RepositoryResponse])
async def list_user_repos(
    owner: str,
    client: GitHubClient = Depends(get_github_client),
) -> Any:
    try:
        return await client.get_repositories(username=owner)
    except Exception as e:
        if hasattr(e, "status"):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos/{owner}/{repo}", response_model=RepositoryResponse)
async def get_repo(
    owner: str,
    repo: str,
    client: GitHubClient = Depends(get_github_client),
) -> Any:
    try:
        return await client.get_repository(owner, repo)
    except Exception as e:
        if hasattr(e, "status"):
            raise
        raise HTTPException(status_code=500, detail=str(e))
