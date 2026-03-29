import httpx
import pytest
import time
from unittest.mock import MagicMock
from src.github.retry_policy import GitHubRetryPolicy, RetryType

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
