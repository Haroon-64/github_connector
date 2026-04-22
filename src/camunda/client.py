import json
from typing import Any, Dict

import httpx
import structlog

from src.camunda.auth import get_camunda_token
from src.core.config import settings

logger = structlog.get_logger(__name__)


class CamundaClient:
    def __init__(self):
        if settings.ZEEBE_REST_ADDRESS:
            self.base_url = (
                f"{settings.ZEEBE_REST_ADDRESS}/v2"
                if not settings.ZEEBE_REST_ADDRESS.endswith("/v2")
                else settings.ZEEBE_REST_ADDRESS
            )
        else:
            self.base_url = settings.CAMUNDA_URL
        self.headers = {"Content-Type": "application/json"}

    async def _get_headers(self):
        headers = self.headers.copy()
        token = await get_camunda_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def start_process(
        self, bpmn_process_id: str, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start a Camunda BPMN process instance via Zeebe REST API."""
        url = f"{self.base_url}/process-instances"
        payload = {"processDefinitionId": bpmn_process_id, "variables": variables}

        logger.debug("starting_camunda_process", process_id=bpmn_process_id)
        async with httpx.AsyncClient() as client:
            try:
                headers = await self._get_headers()
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "camunda_process_started",
                    process_instance_key=data.get("processInstanceKey"),
                )
                return data
            except httpx.HTTPStatusError as e:
                logger.error(
                    "camunda_start_process_http_error",
                    status_code=e.response.status_code,
                    detail=e.response.text,
                )
                raise
            except Exception as e:
                logger.error("camunda_start_process_error", error=str(e))
                raise

    async def get_tasks(self, assignee: str) -> list[Dict[str, Any]]:  # noqa: S3776
        """
        Fetch tasks using the modern Camunda 8 Zeebe REST API.
        """
        url = f"{self.base_url}/user-tasks/search"
        payload = {"filter": {"assignee": assignee, "state": "CREATED"}}
        logger.debug("fetching_zeebe_user_tasks", assignee=assignee)

        async with httpx.AsyncClient() as client:
            try:
                headers = await self._get_headers()
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])

                import asyncio

                async def fetch_vars(task):
                    # In V2, the task key is usually "userTaskKey" or "key"
                    task_key = task.get("userTaskKey", task.get("key"))
                    if not task_key:
                        return task

                    var_url = f"{self.base_url}/user-tasks/{task_key}/variables/search"
                    try:
                        v_res = await client.post(var_url, json={}, headers=headers)
                        if v_res.status_code == 200:
                            v_data = v_res.json()

                            parsed_vars = []
                            for v in v_data.get("items", []):
                                val = v.get("value")
                                if isinstance(val, str):
                                    try:
                                        val = json.loads(val)
                                    except json.JSONDecodeError:
                                        logger.debug(
                                            "Failed to parse JSON string", value=val
                                        )
                                parsed_vars.append(
                                    {"name": v.get("name"), "value": val}
                                )

                            task["variables"] = parsed_vars
                    except Exception as ve:
                        logger.warning(
                            "failed_fetching_variables_for_task",
                            task_key=task_key,
                            error=str(ve),
                        )

                    task["id"] = str(task_key)
                    return task

                tasks_with_vars = await asyncio.gather(*(fetch_vars(t) for t in items))
                return list(tasks_with_vars)
            except Exception as e:
                logger.error("zeebe_fetch_user_tasks_error", error=str(e))
                return []

    async def complete_task(self, task_id: str, variables: Dict[str, Any]) -> None:
        """Complete a user task using the Zeebe REST API."""
        url = f"{self.base_url}/user-tasks/{task_id}/completion"
        payload = {"variables": variables, "action": "complete"}

        logger.debug("completing_zeebe_user_task", task_id=task_id)
        async with httpx.AsyncClient() as client:
            try:
                headers = await self._get_headers()
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info("zeebe_user_task_completed", task_id=task_id)
            except Exception as e:
                logger.error("zeebe_complete_user_task_error", error=str(e))
                raise
