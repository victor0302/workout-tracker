"""Phase 0 (5/5): BLE listener exits cleanly when no device is found.

We're not testing the wearable itself (that's Phase 2). We only verify
that the listener's failure mode when no ESP32 is in range is a clean
SystemExit with an informative message — not a traceback or hang.
"""

import argparse
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ble_listener.listener import run


def _args(scan_timeout: float = 0.1) -> argparse.Namespace:
    return argparse.Namespace(
        device_name="WorkoutBand",
        dashboard="http://localhost:8000/ingest/biometric",
        scan_timeout=scan_timeout,
    )


def test_exits_cleanly_when_no_device_found():
    with patch(
        "ble_listener.listener.BleakScanner.find_device_by_name",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(SystemExit) as exc:
            asyncio.run(run(_args()))
        assert "WorkoutBand" in str(exc.value)


def test_exit_message_includes_configured_device_name():
    args = argparse.Namespace(
        device_name="CustomBand",
        dashboard="http://localhost:8000/ingest/biometric",
        scan_timeout=0.1,
    )
    with patch(
        "ble_listener.listener.BleakScanner.find_device_by_name",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(SystemExit) as exc:
            asyncio.run(run(args))
        assert "CustomBand" in str(exc.value)
