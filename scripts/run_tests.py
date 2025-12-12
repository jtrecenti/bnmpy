"""Run test suite with different options."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Run tests based on command line arguments."""
    args = sys.argv[1:]

    if "--integration" in args:
        # Run only integration tests
        pytest.main(["-m", "integration", "-v"])
    elif "--browser" in args:
        # Run browser tests
        pytest.main(["-m", "browser", "-v", "-s"])
    elif "--all" in args:
        # Run all tests including integration
        pytest.main(["-v", "-s"])
    else:
        # Run unit tests only (default)
        pytest.main(["-v", "-m", "not integration and not browser"])


if __name__ == "__main__":
    main()

