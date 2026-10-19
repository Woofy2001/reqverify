import os
import pytest

def test_regular_offline_test():
    """Verify regular offline test runs without requiring API credentials."""
    assert 1 + 1 == 2

@pytest.mark.live
def test_live_marker_isolated():
    """Verify live marker test executes only when live testing is enabled."""
    assert os.getenv("ANTHROPIC_API_KEY") is not None
