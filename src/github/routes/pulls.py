from typing import Any, List

import structlog
from fastapi import APIRouter, Body, Depends

from src.dependencies.github import github_provider
from src.github.service import GitHubService
from src.models.github import (
    CamundaOptionsResponse,
    CommentRequest,
    CommentResponse,
    PRMergeRequest,
    PRMergeResponse,
    PRRequest,
    PRResponse,
    PRReviewRequest,
    PRReviewResponse,
)

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


@router.get("/repos/{owner}/{repo}/pulls", response_model=List[PRResponse])
async def list_pulls(
    owner: str,
    repo: str,
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug("list_pulls_request", owner=owner, repo=repo)
    return await service.get_pulls(owner, repo)


@router.post(
    "/repos/{owner}/{repo}/pulls/{pull_number}/reviews", response_model=PRReviewResponse
)
async def review_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    review: PRReviewRequest = Body(
        ..., description="Review action: APPROVE, REQUEST_CHANGES, or COMMENT"
    ),
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug(
        "review_pull_request",
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        review_event=review.event,
    )
    return await service.create_pull_request_review(
        owner,
        repo,
        pull_number,
        review.model_dump(),
    )


@router.get(
    "/repos/{owner}/{repo}/pulls/camunda-options", response_model=CamundaOptionsResponse
)
async def list_pulls_camunda_options(
    owner: str,
    repo: str,
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug("list_pulls_camunda_options_request", owner=owner, repo=repo)
    pulls = await service.get_pulls(owner, repo)
    options = []
    for p in pulls:
        options.append(
            {
                "label": f"{p['title']} (#{p['number']})",
                "value": p["number"],
            }
        )
    return {"prOptions": options}


@router.put(
    "/repos/{owner}/{repo}/pulls/{pull_number}/merge", response_model=PRMergeResponse
)
async def merge_pull_request_endpoint(
    owner: str,
    repo: str,
    pull_number: int,
    merge_req: PRMergeRequest = Body(...),
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug("merge_pull_request", owner=owner, repo=repo, pull_number=pull_number)
    return await service.merge_pull_request(
        owner,
        repo,
        pull_number,
        merge_req.model_dump(exclude_unset=True),
    )


@router.post(
    "/repos/{owner}/{repo}/pulls/{pull_number}/comments", response_model=CommentResponse
)
async def comment_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    comment: CommentRequest = Body(...),
    service: GitHubService = Depends(github_provider(required=True)),
) -> Any:
    logger.debug(
        "comment_pull_request", owner=owner, repo=repo, pull_number=pull_number
    )
    # PR comments are created via the issues API
    return await service.create_issue_comment(
        owner,
        repo,
        pull_number,
        comment.model_dump(exclude_unset=True),
    )
