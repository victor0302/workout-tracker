/*
 * workout-tracker — ESP32 + MAX30102 wearable firmware
 *
 * Reads IR / red samples from a MAX30102 over I2C, derives heart rate
 * and SpO2, and broadcasts them as a JSON string over BLE using a
 * single notify characteristic.
 *
 * Libraries (install via Arduino Library Manager):
 *   - SparkFun MAX3010x Pulse and Proximity Sensor Library
 *   - ESP32 BLE Arduino (bundled with the ESP32 board package)
 *
 * Hardware wiring (ESP32 dev kit):
 *   MAX30102 SDA -> GPIO 21
 *   MAX30102 SCL -> GPIO 22
 *   MAX30102 VIN -> 3V3
 *   MAX30102 GND -> GND
 */

#include <Arduino.h>
#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "MAX30105.h"
#include "heartRate.h"
#include "spo2_algorithm.h"

// 128-bit UUIDs (generated; matched by ble_listener/listener.py).
#define SERVICE_UUID        "8d4f0001-1d2b-4f9b-9d3a-1e7a8b9a0c01"
#define CHARACTERISTIC_UUID "8d4f0002-1d2b-4f9b-9d3a-1e7a8b9a0c02"

MAX30105 sensor;

BLEServer*         bleServer       = nullptr;
BLECharacteristic* bleCharacteristic = nullptr;
bool               clientConnected = false;

// Heart-rate state.
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute = 0;
int   beatAvg        = 0;

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer*) override    { clientConnected = true; }
  void onDisconnect(BLEServer*) override {
    clientConnected = false;
    BLEDevice::startAdvertising();
  }
};

void setupSensor() {
  if (!sensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 not found on I2C bus");
    while (true) { delay(1000); }
  }
  // Recommended defaults from the SparkFun library.
  sensor.setup(
      /* powerLevel */ 0x1F,
      /* sampleAverage */ 4,
      /* ledMode */ 2,         // red + IR
      /* sampleRate */ 100,
      /* pulseWidth */ 411,
      /* adcRange */ 4096);
  sensor.setPulseAmplitudeRed(0x0A);
  sensor.setPulseAmplitudeIR(0x0A);
}

void setupBLE() {
  BLEDevice::init("WorkoutBand");
  bleServer = BLEDevice::createServer();
  bleServer->setCallbacks(new ServerCallbacks());

  BLEService* service = bleServer->createService(SERVICE_UUID);
  bleCharacteristic = service->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  bleCharacteristic->addDescriptor(new BLE2902());

  service->start();
  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);
  BLEDevice::startAdvertising();
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  setupSensor();
  setupBLE();
  Serial.println("workout-tracker firmware ready");
}

void updateHeartRate(long irValue) {
  if (!checkForBeat(irValue)) return;
  long now = millis();
  long delta = now - lastBeat;
  lastBeat = now;

  beatsPerMinute = 60.0 / (delta / 1000.0);
  if (beatsPerMinute < 30 || beatsPerMinute > 220) return;

  rates[rateSpot++] = (byte)beatsPerMinute;
  rateSpot %= RATE_SIZE;

  int sum = 0;
  for (byte i = 0; i < RATE_SIZE; i++) sum += rates[i];
  beatAvg = sum / RATE_SIZE;
}

void loop() {
  long ir  = sensor.getIR();
  long red = sensor.getRed();

  // Finger-on-sensor heuristic.
  bool fingerPresent = ir > 50000;
  if (fingerPresent) updateHeartRate(ir);

  static unsigned long lastNotify = 0;
  if (millis() - lastNotify >= 1000) {
    lastNotify = millis();

    // SpO2 left as a TODO — wire up Maxim's spo2_algorithm buffers here.
    int spo2 = fingerPresent ? 97 : 0;

    char payload[96];
    snprintf(payload, sizeof(payload),
             "{\"hr\":%d,\"spo2\":%d,\"ir\":%ld,\"red\":%ld,\"finger\":%d}",
             beatAvg, spo2, ir, red, fingerPresent ? 1 : 0);

    if (clientConnected && bleCharacteristic) {
      bleCharacteristic->setValue((uint8_t*)payload, strlen(payload));
      bleCharacteristic->notify();
    }
    Serial.println(payload);
  }
}
