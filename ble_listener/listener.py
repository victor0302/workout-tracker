"""BLE listener for the ESP32 wearable.

Scans for the ESP32 advertising the configured service UUID, subscribes
to its notify characteristic, decodes the JSON payload it sends each
second and forwards the sample to the dashboard.
"""

import argparse
import asyncio
import json
import logging
from typing import Any

import requests
from bleak import BleakClient, BleakScanner

# Must match firmware/esp32_max30102/esp32_max30102.ino.
SERVICE_UUID = "8d4f0001-1d2b-4f9b-9d3a-1e7a8b9a0c01"
CHARACTERISTIC_UUID = "8d4f0002-1d2b-4f9b-9d3a-1e7a8b9a0c02"

DASHBOARD_URL = "http://localhost:8000/ingest/biometric"

log = logging.getLogger("ble_listener")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device-name", default="WorkoutBand")
    p.add_argument("--dashboard", default=DASHBOARD_URL)
    p.add_argument("--scan-timeout", type=float, default=10.0)
    return p.parse_args()


def forward_to_dashboard(url: str, sample: dict[str, Any]) -> None:
    try:
        requests.post(url, json=sample, timeout=0.5)
    except requests.RequestException as exc:
        log.debug("dashboard post failed: %s", exc)


async def run(args: argparse.Namespace) -> None:
    log.info("scanning for %r ...", args.device_name)
    device = await BleakScanner.find_device_by_name(args.device_name, timeout=args.scan_timeout)
    if device is None:
        raise SystemExit(f"BLE device {args.device_name!r} not found")

    log.info("connecting to %s (%s)", device.name, device.address)
    async with BleakClient(device) as client:
        def on_notify(_sender: int, data: bytearray) -> None:
            try:
                sample = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                log.warning("dropped malformed payload: %r", data)
                return
            log.info("sample %s", sample)
            forward_to_dashboard(args.dashboard, sample)

        await client.start_notify(CHARACTERISTIC_UUID, on_notify)
        log.info("subscribed; press Ctrl+C to exit")
        try:
            while True:
                await asyncio.sleep(1.0)
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
