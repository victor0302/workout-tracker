# workout-tracker

A fitness tracking system that combines computer-vision rep counting with
biometric data from a wearable, surfaced through a shared dashboard.

## Components

### 1. `vision/` — Vision-based workout tracker (Python)
Uses MediaPipe Pose for body keypoint estimation and OpenCV for video capture.
Counts reps from joint-angle trajectories and classifies the current exercise
(squat / curl / deadlift).

### 2. `firmware/` — ESP32 + MAX30102 wearable
Arduino C++ sketch that reads heart-rate and SpO2 samples from a MAX30102
sensor over I2C and broadcasts them over Bluetooth Low Energy.

### 3. `ble_listener/` — Python BLE listener
Subscribes to the ESP32's BLE characteristic, decodes incoming samples and
forwards them to the dashboard.

### 4. `dashboard/` — FastAPI server
Accepts ingest from both the vision tracker and the BLE listener, holds
recent state in memory, and exposes a `/metrics` endpoint.

## Folder layout

```
workout-tracker/
├── vision/                  # MediaPipe pose + rep counter + classifier
├── firmware/esp32_max30102/ # Arduino sketch for the wearable
├── ble_listener/            # Python BLE client
└── dashboard/               # FastAPI ingest + /metrics
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

Each component runs independently. Start the dashboard first so the other
two have somewhere to post to.

### Dashboard
```bash
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```
Then `GET http://localhost:8000/metrics`.

### Vision tracker
```bash
python -m vision.main --source 0           # webcam
python -m vision.main --source path/to.mp4 # video file
```

### BLE listener
```bash
python -m ble_listener.listener --device-name WorkoutBand
```

### Firmware
Open `firmware/esp32_max30102/esp32_max30102.ino` in the Arduino IDE,
install the **Adafruit MAX30105** and **ESP32 BLE Arduino** libraries,
select your ESP32 board and flash.

## Status

This is a scaffold — pose detection, BLE I/O and the ingest endpoints are
wired together, but the rep counter and exercise classifier are intentionally
left as stubs to be filled in.
