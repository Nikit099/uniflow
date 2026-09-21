from app.core.rate_limit import SlidingWindowLimiter


def test_sliding_window_limiter_blocks_after_limit() -> None:
    limiter = SlidingWindowLimiter()
    assert limiter.allow("actor", 2)
    assert limiter.allow("actor", 2)
    assert not limiter.allow("actor", 2)
    assert limiter.allow("other", 2)
