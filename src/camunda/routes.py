from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.camunda.client import CamundaClient
from src.dependencies.auth import auth_provider

camunda_router = APIRouter()
logger = structlog.get_logger(__name__)


class ProcessStartRequest(BaseModel):
    owner: str
    repo: str
    pull_number: int


def get_camunda_client() -> CamundaClient:
    return CamundaClient()


@camunda_router.post("/process/start")
async def start_review_process(
    request: ProcessStartRequest,
    current_user: Dict[str, Any] = Depends(auth_provider(required=True)),
    client: CamundaClient = Depends(get_camunda_client),
) -> Dict[str, Any]:
    """Start the BPMN review process for a specific PR."""
    variables = {
        "owner": request.owner,
        "repo": request.repo,
        "pull_number": request.pull_number,
        "reviewer": current_user.get("username"),
    }
    try:
        result = await client.start_process("pr_review_v2", variables)
        return {"status": "started", "camunda_result": result}
    except Exception as e:
        logger.error("start_review_process_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start Camunda process")


@camunda_router.get("/tasks")
async def get_my_tasks(
    current_user: Dict[str, Any] = Depends(auth_provider(required=True)),
    client: CamundaClient = Depends(get_camunda_client),
) -> list[Dict[str, Any]]:
    """Get open tasks assigned to the current user."""
    return await client.get_tasks(assignee=current_user.get("username", ""))


class CompleteTaskRequest(BaseModel):
    decision: str
    comment: str


@camunda_router.post("/tasks/{task_id}/complete")
async def complete_review_task(
    task_id: str,
    request: CompleteTaskRequest,
    current_user: Dict[str, Any] = Depends(auth_provider(required=True)),
    client: CamundaClient = Depends(get_camunda_client),
) -> Dict[str, Any]:
    """Complete a review task with decision variables."""
    variables = {
        "decision": request.decision,
        "comment": request.comment,
    }
    try:
        await client.complete_task(task_id, variables)
        return {"status": "completed"}
    except Exception as e:
        logger.error("complete_review_task_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to complete Camunda task")
