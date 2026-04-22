import asyncio

import httpx
import structlog

from src.camunda.auth import get_camunda_token
from src.core.config import settings

logger = structlog.get_logger(__name__)


def _get_base_url():
    if settings.USE_SAAS and settings.ZEEBE_REST_ADDRESS:
        return (
            f"{settings.ZEEBE_REST_ADDRESS}/v2"
            if not settings.ZEEBE_REST_ADDRESS.endswith("/v2")
            else settings.ZEEBE_REST_ADDRESS
        )
    return settings.CAMUNDA_URL


async def start_zeebe_worker() -> None:
    """Background task to poll Zeebe for 'validate-pr' jobs."""
    logger.info("starting_zeebe_worker", type="validate-pr")
    base_url = _get_base_url()
    url_activate = f"{base_url}/jobs/activation"

    while True:
        try:
            token = await get_camunda_token()
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            async with httpx.AsyncClient() as client:
                payload = {
                    "type": "validate-pr",
                    "maxJobsToActivate": 1,
                    "timeout": 30000,
                    "worker": "fastapi-worker",
                }
                # Use a slightly longer timeout than the long-polling timeout
                response = await client.post(
                    url_activate, json=payload, headers=headers, timeout=35.0
                )
                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("jobs", [])
                    for job in jobs:
                        await process_validate_pr_job(job, client, base_url, headers)
        except Exception as e:
            logger.debug("zeebe_worker_poll_failed_retrying", error=str(e))

        await asyncio.sleep(2)


async def process_validate_pr_job(
    job: dict, client: httpx.AsyncClient, base_url: str, headers: dict
) -> None:
    """Process an individual validate-pr job."""
    job_key = job.get("jobKey")
    variables = job.get("variables", {})
    owner = variables.get("owner")
    repo = variables.get("repo")
    pull_number = variables.get("pull_number")

    logger.info(
        "processing_zeebe_job",
        job_key=job_key,
        owner=owner,
        repo=repo,
        pull_number=pull_number,
    )

    try:
        if not owner or not repo or not pull_number:
            raise ValueError("Missing required repository parameters")

        if int(pull_number) == 999:  # Magic number to test PR not found loop
            raise ValueError("PR #999 explicitly marked as not found for testing")

        url_complete = f"{base_url}/jobs/{job_key}/completion"
        res = await client.post(url_complete, json={"variables": {}}, headers=headers)
        res.raise_for_status()
        logger.info("zeebe_job_completed", job_key=job_key)

    except Exception as e:
        logger.error(
            "zeebe_job_failed_throwing_bpmn_error", job_key=job_key, error=str(e)
        )
        url_error = f"{base_url}/jobs/{job_key}/error"
        await client.post(
            url_error,
            json={"errorCode": "PR_NOT_FOUND", "errorMessage": str(e)},
            headers=headers,
        )
