import pytest
from fastapi import HTTPException
from app.security import SlidingWindowRateLimiter


def test_rate_limiter_blocks_after_limit():
    limiter = SlidingWindowRateLimiter()
    limiter.check("workspace:client", limit=2)
    limiter.check("workspace:client", limit=2)
    with pytest.raises(HTTPException) as error:
        limiter.check("workspace:client", limit=2)
    assert error.value.status_code == 429
    assert "Retry-After" in error.value.headers

