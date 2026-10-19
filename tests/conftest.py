import os
import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: mark test as requiring active ANTHROPIC_API_KEY and network access"
    )

@pytest.fixture(autouse=True)
def skip_live_if_no_key(request):
    """Automatically skip tests marked @pytest.mark.live if ANTHROPIC_API_KEY is not set."""
    if request.node.get_closest_marker("live"):
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("Skipping live test: ANTHROPIC_API_KEY environment variable is not set")
