"""Shared test fixtures."""

import pytest

from dashboard.app import state


@pytest.fixture(autouse=True)
def reset_dashboard_state():
    """Reset in-memory dashboard state between tests so order doesn't matter."""
    state.vision_latest = None
    state.biometric_latest = None
    state.vision_history.clear()
    state.biometric_history.clear()
    yield
