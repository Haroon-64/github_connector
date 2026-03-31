import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Awaitable, Callable, Dict, Optional, cast

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
        self._rate_limit_state: Dict[Optional[str], Dict[str, Any]] = {}

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
                raise RateLimitError()

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

    def should_stop(
        self,
        decision: RetryDecision,
        attempt_counts: Dict[RetryType, int],
        start_time: float,
    ) -> bool:
        """Check both absolute max_time and exact attempt counts per type.

        Returns True if stop limit hit.
        """
        elapsed_time = time.time() - start_time
        if elapsed_time > self.max_time:
            logger.error(
                "github_retry_timeout_exceeded",
                max_time=self.max_time,
                retry_type=decision.retry_type.name,
                total_attempts=attempt_counts[decision.retry_type],
                elapsed_time=elapsed_time,
            )
            return True

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
            return True

        return False

    def update_rate_limit_state(
        self,
        response: httpx.Response,
        access_token: Optional[str],
    ) -> None:
        """Update stored rate limit state from response headers.

        Args:
            response: HTTP response with rate limit headers
            access_token: Token to update state for
        """
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")

        if remaining is not None or reset is not None:
            state = self._rate_limit_state.get(access_token, {})
            if remaining is not None:
                state["remaining"] = int(remaining)
            if reset is not None:
                state["reset"] = float(reset)
            self._rate_limit_state[access_token] = state

    def check_pacing(self, access_token: Optional[str]) -> float:
        """Proactively calculate wait time based on rate limit state.

        Args:
            access_token: Token to check rate limit state for

        Returns:
            Wait time in seconds (0 if no wait needed)

        Raises:
            RateLimitError: When wait time exceeds 600 seconds
        """
        state = self._rate_limit_state.get(access_token)

        if not state:
            return 0.0

        remaining = state.get("remaining")
        reset = state.get("reset")

        if remaining is None or reset is None:
            return 0.0

        if remaining > 100:
            return 0.0

        now = time.time()
        time_until_reset = max(0.0, reset - now)

        wait_time: float
        if remaining == 0:
            wait_time = time_until_reset + random.uniform(0, 1)
        else:
            # Low quota (0 < remaining <= 100)
            wait_time = time_until_reset / remaining

        if wait_time > 600:
            logger.warning("rate_limit_pacing_wait_too_long", wait=wait_time)
            raise RateLimitError()

        if wait_time > 0:
            logger.debug("rate_limit_pacing_delay", wait=wait_time, remaining=remaining)

        return wait_time

    def _handle_retry_failure(self, decision: RetryDecision) -> None:
        """Raises the appropriate exception when retry limits are hit."""
        if decision.retry_type == RetryType.RATE_LIMIT:
            raise RateLimitError()
        if decision.retry_type == RetryType.SERVER:
            raise ServerError()
        if decision.retry_type == RetryType.TIMEOUT:
            raise TimeoutError()
        raise NetworkError()

    async def execute_with_retries(
        self,
        request_callback: Callable[[], Awaitable[httpx.Response]],
        access_token: Optional[str] = None,
    ) -> httpx.Response:
        """Orchestrate retries for a request callback.

        Args:
            request_callback: Async function that performs the HTTP request
            access_token: Token for rate limit state tracking

        Returns:
            The successful response

        Raises:
            RateLimitError: When rate limits are exceeded
            ServerError: When server errors exceed retry limit
            NetworkError: When network errors exceed retry limit
            TimeoutError: When timeout errors exceed retry limit
        """
        start_time = time.time()
        attempt_counts = {
            RetryType.RATE_LIMIT: 0,
            RetryType.SERVER: 0,
            RetryType.NETWORK: 0,
            RetryType.TIMEOUT: 0,
        }

        while True:
            wait_time = self.check_pacing(access_token)
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            try:
                response = await request_callback()
                self.update_rate_limit_state(response, access_token)
                decision = self.evaluate_response(response, attempt_counts)

            except (httpx.TimeoutException, httpx.RequestError) as e:
                decision = self.evaluate_exception(e, attempt_counts)

            if decision is None:
                return response

            attempt_counts[decision.retry_type] += 1

            if self.should_stop(decision, attempt_counts, start_time):
                self._handle_retry_failure(decision)

            logger.warning(
                "github_request_retry",
                wait=decision.wait,
                retry_type=decision.retry_type.name,
                attempt=attempt_counts[decision.retry_type],
            )

            await asyncio.sleep(decision.wait)
