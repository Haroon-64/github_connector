import httpx
import pytest
import time
from unittest.mock import MagicMock
from src.github.retry_policy import GitHubRetryPolicy, RetryType
from src.models.error import RateLimitError

def test_evaluate_exception_timeout():
    policy = GitHubRetryPolicy()
    attempt_counts = {RetryType.TIMEOUT: 0, RetryType.NETWORK: 0}
    exc = httpx.TimeoutException("timeout")
    
    decision = policy.evaluate_exception(exc, attempt_counts)
    assert decision.retry_type == RetryType.TIMEOUT
    assert decision.wait >= 2.0  # At least base wait

def test_evaluate_exception_network():
    policy = GitHubRetryPolicy()
    attempt_counts = {RetryType.TIMEOUT: 0, RetryType.NETWORK: 0}
    exc = httpx.ConnectError("conn error")
    
    decision = policy.evaluate_exception(exc, attempt_counts)
    assert decision.retry_type == RetryType.NETWORK
    assert decision.wait >= 1.0

def test_evaluate_response_server_error():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 502
    attempt_counts = {RetryType.SERVER: 0}
    
    decision = policy.evaluate_response(mock_response, attempt_counts)
    assert decision is not None
    assert decision.retry_type == RetryType.SERVER
    assert decision.wait >= 2.0

def test_evaluate_response_rate_limit_retry_after():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.headers = {"retry-after": "5"}
    attempt_counts = {RetryType.RATE_LIMIT: 0}
    
    decision = policy.evaluate_response(mock_response, attempt_counts)
    assert decision is not None
    assert decision.retry_type == RetryType.RATE_LIMIT
    assert decision.wait == pytest.approx(5.0)

def test_evaluate_response_rate_limit_reset():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    future_time = time.time() + 10
    mock_response.headers = {
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": str(future_time)
    }
    attempt_counts = {RetryType.RATE_LIMIT: 0}
    
    decision = policy.evaluate_response(mock_response, attempt_counts)
    assert decision is not None
    assert decision.retry_type == RetryType.RATE_LIMIT
    assert decision.wait >= 9.0  # ~10 seconds plus jitter

def test_evaluate_response_non_retriable():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    
    decision = policy.evaluate_response(mock_response, {})
    assert decision is None

def test_should_stop_max_time_exceeded():
    policy = GitHubRetryPolicy(max_time=1.0)
    decision = MagicMock()
    decision.retry_type = RetryType.RATE_LIMIT
    attempt_counts = {RetryType.RATE_LIMIT: 1}
    
    start_time = time.time() - 2.0  # 2 seconds ago
    assert policy.should_stop(decision, attempt_counts, start_time) is True

def test_should_stop_max_attempts_exceeded():
    policy = GitHubRetryPolicy(max_rate_limit_retries=3)
    decision = MagicMock()
    decision.retry_type = RetryType.RATE_LIMIT
    attempt_counts = {RetryType.RATE_LIMIT: 4}
    
    start_time = time.time()
    assert policy.should_stop(decision, attempt_counts, start_time) is True

def test_update_rate_limit_state_with_both_headers():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {
        "x-ratelimit-remaining": "4850",
        "x-ratelimit-reset": "1704067200.5"
    }
    
    policy.update_rate_limit_state(mock_response, "token_abc123")
    
    state = policy._rate_limit_state.get("token_abc123")
    assert state is not None
    assert state["remaining"] == 4850
    assert state["reset"] == 1704067200.5

def test_update_rate_limit_state_with_only_remaining():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {"x-ratelimit-remaining": "120"}
    
    policy.update_rate_limit_state(mock_response, "token_xyz789")
    
    state = policy._rate_limit_state.get("token_xyz789")
    assert state is not None
    assert state["remaining"] == 120
    assert "reset" not in state

def test_update_rate_limit_state_with_only_reset():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {"x-ratelimit-reset": "1704068000.0"}
    
    policy.update_rate_limit_state(mock_response, "token_test")
    
    state = policy._rate_limit_state.get("token_test")
    assert state is not None
    assert state["reset"] == 1704068000.0
    assert "remaining" not in state

def test_update_rate_limit_state_with_no_headers():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {}
    
    policy.update_rate_limit_state(mock_response, "token_empty")
    
    state = policy._rate_limit_state.get("token_empty")
    assert state is None

def test_update_rate_limit_state_with_none_token():
    policy = GitHubRetryPolicy()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {
        "x-ratelimit-remaining": "45",
        "x-ratelimit-reset": "1704068000.0"
    }
    
    policy.update_rate_limit_state(mock_response, None)
    
    state = policy._rate_limit_state.get(None)
    assert state is not None
    assert state["remaining"] == 45
    assert state["reset"] == 1704068000.0

def test_update_rate_limit_state_updates_existing():
    policy = GitHubRetryPolicy()
    
    # First update
    mock_response1 = MagicMock(spec=httpx.Response)
    mock_response1.headers = {
        "x-ratelimit-remaining": "5000",
        "x-ratelimit-reset": "1704067200.0"
    }
    policy.update_rate_limit_state(mock_response1, "token_update")
    
    # Second update with new values
    mock_response2 = MagicMock(spec=httpx.Response)
    mock_response2.headers = {
        "x-ratelimit-remaining": "4999",
        "x-ratelimit-reset": "1704067200.0"
    }
    policy.update_rate_limit_state(mock_response2, "token_update")
    
    state = policy._rate_limit_state.get("token_update")
    assert state is not None
    assert state["remaining"] == 4999
    assert state["reset"] == 1704067200.0


def test_check_pacing_no_state():
    """Test check_pacing returns 0 when no rate limit state exists."""
    policy = GitHubRetryPolicy()
    
    wait_time = policy.check_pacing("token_no_state")
    
    assert wait_time == 0.0

def test_check_pacing_missing_remaining():
    """Test check_pacing returns 0 when remaining is missing from state."""
    policy = GitHubRetryPolicy()
    policy._rate_limit_state["token_test"] = {"reset": 1704067200.0}
    
    wait_time = policy.check_pacing("token_test")
    
    assert wait_time == 0.0

def test_check_pacing_missing_reset():
    """Test check_pacing returns 0 when reset is missing from state."""
    policy = GitHubRetryPolicy()
    policy._rate_limit_state["token_test"] = {"remaining": 100}
    
    wait_time = policy.check_pacing("token_test")
    
    assert wait_time == 0.0

def test_check_pacing_remaining_above_100():
    """Test check_pacing returns 0 when remaining > 100."""
    policy = GitHubRetryPolicy()
    future_time = time.time() + 3600
    policy._rate_limit_state["token_test"] = {
        "remaining": 150,
        "reset": future_time
    }
    
    wait_time = policy.check_pacing("token_test")
    
    assert wait_time == 0.0

def test_check_pacing_remaining_exactly_100():
    """Test check_pacing calculates proportional wait when remaining = 100."""
    policy = GitHubRetryPolicy()
    future_time = time.time() + 1000  # 1000 seconds until reset
    policy._rate_limit_state["token_test"] = {
        "remaining": 100,
        "reset": future_time
    }
    
    wait_time = policy.check_pacing("token_test")
    
    # Should be approximately 1000 / 100 = 10 seconds
    assert wait_time > 0
    assert wait_time < 15  # Allow some margin for timing

def test_check_pacing_remaining_low():
    """Test check_pacing calculates proportional wait when 0 < remaining <= 100."""
    policy = GitHubRetryPolicy()
    future_time = time.time() + 500  # 500 seconds until reset
    policy._rate_limit_state["token_test"] = {
        "remaining": 50,
        "reset": future_time
    }
    
    wait_time = policy.check_pacing("token_test")
    
    # Should be approximately 500 / 50 = 10 seconds
    assert wait_time > 0
    assert wait_time < 15  # Allow some margin for timing

def test_check_pacing_remaining_zero():
    """Test check_pacing calculates wait with jitter when remaining = 0."""
    policy = GitHubRetryPolicy()
    future_time = time.time() + 100  # 100 seconds until reset
    policy._rate_limit_state["token_test"] = {
        "remaining": 0,
        "reset": future_time
    }
    
    wait_time = policy.check_pacing("token_test")
    
    # Should be approximately 100 seconds + jitter (0-1)
    assert wait_time >= 100
    assert wait_time <= 102  # 100 + max jitter

def test_check_pacing_reset_in_past():
    """Test check_pacing handles reset time in the past gracefully."""
    policy = GitHubRetryPolicy()
    past_time = time.time() - 100  # 100 seconds ago
    policy._rate_limit_state["token_test"] = {
        "remaining": 50,
        "reset": past_time
    }
    
    wait_time = policy.check_pacing("token_test")
    
    # Should be 0 since time_until_reset is clamped to 0
    assert wait_time == 0.0

def test_check_pacing_raises_error_when_wait_exceeds_600():
    """Test check_pacing raises RateLimitError when wait time > 600 seconds."""
    policy = GitHubRetryPolicy()
    future_time = time.time() + 700  # 700 seconds until reset
    policy._rate_limit_state["token_test"] = {
        "remaining": 0,
        "reset": future_time
    }
    
    with pytest.raises(RateLimitError):
        policy.check_pacing("token_test")

def test_check_pacing_with_none_token():
    """Test check_pacing works with None token (unauthenticated requests)."""
    policy = GitHubRetryPolicy()
    future_time = time.time() + 200
    policy._rate_limit_state[None] = {
        "remaining": 10,
        "reset": future_time
    }
    
    wait_time = policy.check_pacing(None)
    
    # Should be approximately 200 / 10 = 20 seconds
    assert wait_time > 0
    assert wait_time < 25  # Allow some margin

def test_check_pacing_proportional_calculation():
    """Test check_pacing proportional calculation with specific values."""
    policy = GitHubRetryPolicy()
    future_time = time.time() + 300  # 300 seconds until reset
    policy._rate_limit_state["token_test"] = {
        "remaining": 30,
        "reset": future_time
    }
    
    wait_time = policy.check_pacing("token_test")
    
    # Should be approximately 300 / 30 = 10 seconds
    assert 9 <= wait_time <= 11  # Allow small margin for timing


@pytest.mark.anyio
async def test_execute_with_retries_success_on_first_attempt():
    """Test execute_with_retries returns response on first successful attempt."""
    policy = GitHubRetryPolicy()
    
    # Create a mock response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {}
    
    # Create a callback that returns the mock response
    async def callback():
        return mock_response
    
    result = await policy.execute_with_retries(callback, "token_test")
    
    assert result == mock_response

@pytest.mark.anyio
async def test_execute_with_retries_retries_on_server_error():
    """Test execute_with_retries retries on server error and eventually succeeds."""
    policy = GitHubRetryPolicy(max_error_retries=2)
    
    # Create mock responses
    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 502
    error_response.headers = {}
    
    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.headers = {}
    
    # Track call count
    call_count = 0
    
    async def callback():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return error_response
        return success_response
    
    result = await policy.execute_with_retries(callback, "token_test")
    
    assert result == success_response
    assert call_count == 2

@pytest.mark.anyio
async def test_execute_with_retries_raises_on_max_retries():
    """Test execute_with_retries raises exception when max retries exceeded."""
    policy = GitHubRetryPolicy(max_error_retries=1)
    
    # Create mock response that always fails
    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 502
    error_response.headers = {}
    
    async def callback():
        return error_response
    
    from src.models.error import ServerError
    with pytest.raises(ServerError):
        await policy.execute_with_retries(callback, "token_test")

@pytest.mark.anyio
async def test_execute_with_retries_handles_network_exception():
    """Test execute_with_retries handles network exceptions and retries."""
    policy = GitHubRetryPolicy(max_error_retries=2)
    
    # Create success response
    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.headers = {}
    
    # Track call count
    call_count = 0
    
    async def callback():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("Connection failed")
        return success_response
    
    result = await policy.execute_with_retries(callback, "token_test")
    
    assert result == success_response
    assert call_count == 2

@pytest.mark.anyio
async def test_execute_with_retries_updates_rate_limit_state():
    """Test execute_with_retries updates rate limit state from response headers."""
    policy = GitHubRetryPolicy()
    
    # Create mock response with rate limit headers
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {
        "x-ratelimit-remaining": "4850",
        "x-ratelimit-reset": "1704067200.0"
    }
    
    async def callback():
        return mock_response
    
    await policy.execute_with_retries(callback, "token_test")
    
    # Verify rate limit state was updated
    state = policy._rate_limit_state.get("token_test")
    assert state is not None
    assert state["remaining"] == 4850
    assert state["reset"] == pytest.approx(1704067200.0)



from hypothesis import given, settings as h_settings
import hypothesis.strategies as st


@given(
    remaining=st.integers(min_value=0, max_value=10000),
    reset=st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
    token=st.one_of(st.none(), st.text(min_size=1, max_size=64)),
)
@h_settings(max_examples=20)
def test_rate_limit_state_updates_are_idempotent(remaining, reset, token):
    """
    **Validates: Requirements 1.2, 6.1, 6.2**

    Property 1: Rate limit state updates are idempotent.
    Calling update_rate_limit_state multiple times with the same headers
    produces the same result as calling it once.
    """
    policy = GitHubRetryPolicy()

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {
        "x-ratelimit-remaining": str(remaining),
        "x-ratelimit-reset": str(reset),
    }

    policy.update_rate_limit_state(mock_response, token)
    state_after_first = dict(policy._rate_limit_state.get(token, {}))

    policy.update_rate_limit_state(mock_response, token)
    state_after_second = dict(policy._rate_limit_state.get(token, {}))

    policy.update_rate_limit_state(mock_response, token)
    state_after_third = dict(policy._rate_limit_state.get(token, {}))

    assert state_after_first == state_after_second == state_after_third
    assert state_after_first["remaining"] == remaining
    assert state_after_first["reset"] == reset


@given(
    remaining=st.integers(min_value=0, max_value=10000),
    reset_offset=st.floats(min_value=-1000.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    token=st.one_of(st.none(), st.text(min_size=1, max_size=64)),
)
@h_settings(max_examples=20)
def test_pacing_wait_time_is_non_negative(remaining, reset_offset, token):
    """
    **Validates: Requirements 2.1, 2.2, 2.3**

    Property 2: Pacing wait time is non-negative.
    For any valid rate limit state (remaining, reset), check_pacing
    either returns a wait time >= 0 or raises RateLimitError (wait > 600).
    """
    policy = GitHubRetryPolicy()
    reset = time.time() + reset_offset
    policy._rate_limit_state[token] = {
        "remaining": remaining,
        "reset": reset,
    }

    try:
        wait_time = policy.check_pacing(token)
        assert wait_time >= 0, f"Expected non-negative wait time, got {wait_time}"
    except RateLimitError:
        # Wait time exceeded 600 seconds — this is valid behavior per Requirement 2.4
        pass


@given(
    max_error_retries=st.integers(min_value=0, max_value=5),
)
@h_settings(max_examples=20, deadline=None)
def test_retry_attempts_never_exceed_configured_limits(max_error_retries):
    """
    **Validates: Requirements 3.2, 5.1, 5.2, 5.3, 5.4**

    Property 3: Retry attempts never exceed configured limits.
    For any retry configuration, the total number of callback invocations
    never exceeds max_error_retries + 1 (initial attempt + retries).
    """
    import asyncio
    from unittest.mock import patch, AsyncMock

    call_count = 0

    async def run():
        nonlocal call_count
        call_count = 0

        policy = GitHubRetryPolicy(max_error_retries=max_error_retries)

        error_response = MagicMock(spec=httpx.Response)
        error_response.status_code = 502
        error_response.headers = {}

        async def always_fail():
            nonlocal call_count
            call_count += 1
            return error_response

        from src.models.error import ServerError
        with patch("asyncio.sleep", new_callable=AsyncMock):
            try:
                await policy.execute_with_retries(always_fail, "token_test")
            except ServerError:
                pass

    asyncio.run(run())

    # Total invocations = 1 initial + up to max_error_retries retries
    assert call_count <= max_error_retries + 1, (
        f"Expected at most {max_error_retries + 1} calls, got {call_count}"
    )


# --- Task 5.4: Unit tests for retry orchestration ---

@pytest.mark.anyio
async def test_execute_with_retries_retries_on_rate_limit_429():
    """Test retry on 429 rate limit error, eventually succeeds. Requirements: 3.1, 5.1"""
    from unittest.mock import patch, AsyncMock

    policy = GitHubRetryPolicy(max_rate_limit_retries=3)

    rate_limit_response = MagicMock(spec=httpx.Response)
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"retry-after": "0.01"}

    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.headers = {}

    call_count = 0

    async def callback():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return rate_limit_response
        return success_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await policy.execute_with_retries(callback, "token_test")

    assert result == success_response
    assert call_count == 2


@pytest.mark.anyio
async def test_execute_with_retries_retries_on_rate_limit_403():
    """Test retry on 403 rate limit error, eventually succeeds. Requirements: 3.1, 5.1"""
    from unittest.mock import patch, AsyncMock

    policy = GitHubRetryPolicy(max_rate_limit_retries=3)

    rate_limit_response = MagicMock(spec=httpx.Response)
    rate_limit_response.status_code = 403
    rate_limit_response.headers = {"retry-after": "0.01"}

    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.headers = {}

    call_count = 0

    async def callback():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return rate_limit_response
        return success_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await policy.execute_with_retries(callback, "token_test")

    assert result == success_response
    assert call_count == 2


@pytest.mark.anyio
async def test_execute_with_retries_raises_rate_limit_error_after_max_retries():
    """Test RateLimitError raised when rate limit retries exhausted. Requirements: 3.7, 5.1"""
    from unittest.mock import patch, AsyncMock
    from src.models.error import RateLimitError

    policy = GitHubRetryPolicy(max_rate_limit_retries=2)

    rate_limit_response = MagicMock(spec=httpx.Response)
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"retry-after": "0.01"}

    async def callback():
        return rate_limit_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RateLimitError):
            await policy.execute_with_retries(callback, "token_test")


@pytest.mark.anyio
async def test_execute_with_retries_retries_on_timeout_error():
    """Test retry on timeout exception, eventually succeeds. Requirements: 3.1, 5.4"""
    from unittest.mock import patch, AsyncMock

    policy = GitHubRetryPolicy(max_error_retries=3)

    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.headers = {}

    call_count = 0

    async def callback():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("timed out")
        return success_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await policy.execute_with_retries(callback, "token_test")

    assert result == success_response
    assert call_count == 2


@pytest.mark.anyio
async def test_execute_with_retries_raises_timeout_error_after_max_retries():
    """Test TimeoutError raised when timeout retries exhausted. Requirements: 3.7, 5.4"""
    from unittest.mock import patch, AsyncMock
    from src.models.error import TimeoutError

    policy = GitHubRetryPolicy(max_error_retries=1)

    async def callback():
        raise httpx.TimeoutException("timed out")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(TimeoutError):
            await policy.execute_with_retries(callback, "token_test")


@pytest.mark.anyio
async def test_execute_with_retries_enforces_max_time():
    """Test that max_time stops retries when elapsed time exceeds limit. Requirements: 3.3, 5.5"""
    from unittest.mock import patch, AsyncMock
    from src.models.error import ServerError

    policy = GitHubRetryPolicy(max_time=0.0, max_error_retries=10)

    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 503
    error_response.headers = {}

    async def callback():
        return error_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ServerError):
            await policy.execute_with_retries(callback, "token_test")


@pytest.mark.anyio
async def test_execute_with_retries_enforces_attempt_count_limit():
    """Test that attempt count limit stops retries. Requirements: 3.2, 5.2"""
    from unittest.mock import patch, AsyncMock
    from src.models.error import ServerError

    max_retries = 2
    policy = GitHubRetryPolicy(max_error_retries=max_retries)

    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 500
    error_response.headers = {}

    call_count = 0

    async def callback():
        nonlocal call_count
        call_count += 1
        return error_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ServerError):
            await policy.execute_with_retries(callback, "token_test")

    # 1 initial attempt + max_retries retries
    assert call_count == max_retries + 1
