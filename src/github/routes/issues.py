from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies.github import get_github_service, get_optional_github_service
from src.github.service import GitHubService
from src.models.error import AuthError, NotFoundError, RateLimitError, ValidationError
from src.models.github import IssueRequest, IssueResponse

router = APIRouter()


@router.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse)
async def create_issue(
    owner: str,
    repo: str,
    issue: IssueRequest,
    service: GitHubService = Depends(get_github_service),
) -> Any:
    try:
        return await service.create_issue(owner, repo, issue.model_dump())
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail="Authentication failed")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Repository or issue not found")
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


@router.get("/repos/{owner}/{repo}/issues", response_model=List[IssueResponse])
async def list_issues(
    owner: str, repo: str, service: GitHubService = Depends(get_optional_github_service)
) -> Any:
    try:
        return await service.list_issues(owner, repo)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
