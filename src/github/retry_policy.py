import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional, cast

import httpx
import structlog

from src.models.error import (
    NetworkError,
    RateLimitError,
    ServerError,
    TimeoutError,
)

logger = structlog.get_logger(__name__)


class RetryType(Enum):
    RATE_LIMIT = auto()
    SERVER = auto()
    NETWORK = auto()
    TIMEOUT = auto()


@dataclass
class RetryDecision:
    retry_type: RetryType
    wait: float


class GitHubRetryPolicy:
    """Consolidated policy for Retries, Pacing, and Waits."""

    def __init__(
        self,
        max_time: float = 300.0,
        max_rate_limit_retries: int = 6,
        max_error_retries: int = 3,
    ):
        self.max_time = max_time
        self.max_rate_limit_retries = max_rate_limit_retries
        self.max_error_retries = max_error_retries

    def evaluate_response(
        self, response: httpx.Response, attempt_counts: Dict[RetryType, int]
    ) -> Optional[RetryDecision]:
        """Classifies response. Returns a RetryDecision if retriable, else None."""
        status = response.status_code
        if status in (403, 429):
            headers = response.headers
            wait_time = 0.0

            if "retry-after" in headers:
                wait_time = float(cast(Any, headers["retry-after"]))
            elif status == 403 and headers.get("x-ratelimit-remaining") == "0":
                reset = headers.get("x-ratelimit-reset")
                if reset:
                    wait_time = max(0.01, float(reset) - time.time())
                    wait_time += random.uniform(0, 1)
            else:
                attempt = attempt_counts[RetryType.RATE_LIMIT]
                wait_time = min(15.0 * (2**attempt), 60.0)
                wait_time += random.uniform(0, 1)

            if wait_time > 600:  # 10 minutes
                logger.warning("rate_limit_wait_too_long", wait=wait_time)
                raise RateLimitError(
                    detail=f"Rate limit exceeded. Wait {int(wait_time)}s is too long."
                )

            return RetryDecision(RetryType.RATE_LIMIT, min(wait_time, self.max_time))

        if status >= 500:
            attempt = attempt_counts[RetryType.SERVER]
            wait_time = min(max(2.0, 2.0 * (2**attempt)), 60.0)
            wait_time += random.uniform(0, 1)
            return RetryDecision(RetryType.SERVER, wait_time)

        return None

    def evaluate_exception(
        self, e: Exception, attempt_counts: Dict[RetryType, int]
    ) -> RetryDecision:
        """Classifies network exceptions. Returns a RetryDecision."""
        if isinstance(e, httpx.TimeoutException):
            attempt = attempt_counts[RetryType.TIMEOUT]
            wait_time = min(max(2.0, 2.0 * (2**attempt)), 60.0)
            wait_time += random.uniform(0, 1)
            return RetryDecision(RetryType.TIMEOUT, wait_time)

        attempt = attempt_counts[RetryType.NETWORK]
        wait_time = min(max(1.0, 1.0 * (2**attempt)), 60.0)
        wait_time += random.uniform(0, 1)
        return RetryDecision(RetryType.NETWORK, wait_time)

    def check_stop_limits(
        self,
        decision: RetryDecision,
        attempt_counts: Dict[RetryType, int],
        start_time: float,
    ) -> None:
        """Check both absolute max_time and exact attempt counts per type.

        Raises error if stop limit hit.
        """
        elapsed_time = time.time() - start_time
        hit = False
        if elapsed_time > self.max_time:
            logger.error(
                "github_retry_timeout_exceeded",
                max_time=self.max_time,
                retry_type=decision.retry_type.name,
                total_attempts=attempt_counts[decision.retry_type],
                elapsed_time=elapsed_time,
            )
            hit = True

        limit = (
            self.max_rate_limit_retries
            if decision.retry_type == RetryType.RATE_LIMIT
            else self.max_error_retries
        )
        if attempt_counts[decision.retry_type] > limit:
            logger.error(
                "github_retry_amount_exceeded",
                limit=limit,
                retry_type=decision.retry_type.name,
                total_attempts=attempt_counts[decision.retry_type],
                elapsed_time=elapsed_time,
            )
            hit = True

        if hit:
            if decision.retry_type == RetryType.RATE_LIMIT:
                raise RateLimitError()
            if decision.retry_type == RetryType.SERVER:
                raise ServerError()
            if decision.retry_type == RetryType.TIMEOUT:
                raise TimeoutError()
            raise NetworkError()
