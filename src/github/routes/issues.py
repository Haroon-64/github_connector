from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies.github import get_github_client
from src.github.client import GitHubClient
from src.models.error import AuthError, NotFoundError, RateLimitError, ValidationError
from src.models.github import IssueRequest, IssueResponse

router = APIRouter()


@router.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse)
async def create_issue(
    owner: str,
    repo: str,
    issue: IssueRequest,
    client: GitHubClient = Depends(get_github_client),
) -> Any:
    try:
        return await client.create_issue(owner, repo, issue.model_dump())
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
    owner: str, repo: str, client: GitHubClient = Depends(get_github_client)
) -> Any:
    try:
        return await client.list_issues(owner, repo)
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
