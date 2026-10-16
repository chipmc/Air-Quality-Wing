#include "Particle.h"
#include "Si7021.h"
#include "SparkFunCCS811.h"
#include "HoneywellPM.h"
#include <cmath>

#ifndef ENABLE_PUBLISH
#define ENABLE_PUBLISH true
#endif
constexpr bool publishEnabled = ENABLE_PUBLISH;

#ifndef ENABLE_USB_SERIAL_WAIT
#define ENABLE_USB_SERIAL_WAIT true
#endif
constexpr bool usbSerialWaitEnabled = ENABLE_USB_SERIAL_WAIT;

SYSTEM_MODE(AUTOMATIC);
// Device OS 6.4.1 enables the system thread by default.
SerialLogHandler logHandler(115200, LOG_LEVEL_INFO);

namespace {
constexpr uint32_t reportInterval = 15L*60000L;
constexpr uint32_t conditioningTime = 20 * 60 * 1000;
constexpr uint32_t freshnessTime = 10000;
constexpr uint32_t pmSampleInterval = 60000;
constexpr uint32_t pmFreshnessTime = 2 * pmSampleInterval;
constexpr uint32_t pmRetryInterval = 60000;
Si7021 si7021;
CCS811 ccs811(0x5A);
HoneywellPM honeywell(Serial1);
bool siReady = false, ccsReady = false, pmStarted = false;
bool environmentValid = false, vocValid = false, pmValid = false;
bool vocErrorLogged = false, ccsConditioned = false;
float temperature = 0, humidity = 0;
uint16_t tvoc = 0, eco2 = 0, pm25 = 0, pm10 = 0;
uint32_t environmentTime = 0, vocTime = 0, pmTime = 0;
uint32_t pmPowerTime = 0, ccsStartTime = 0, pmStartTime = 0;
uint32_t lastEnvironment = 0, lastVoc = 0, lastPmAttempt = 0, lastPmRead = 0, lastReport = 0;
bool firstReport = true;

bool elapsed(uint32_t now, uint32_t since, uint32_t interval) {
    return static_cast<uint32_t>(now - since) >= interval;
}

void initializeUsbSerial() {
    Serial.begin(115200);
    if (usbSerialWaitEnabled) {
        const uint32_t started = millis();
        while (!elapsed(millis(), started, 10000) && !Serial.isConnected()) {
            delay(1);
        }
    }
}

void initializeControlPins() {
    // Device OS 6.4.1 ignores digitalWrite() while a pin is still an input.
    // D5 can briefly be LOW between OUTPUT configuration and the HIGH write:
    // account for a CCS811 reset / Honeywell power interruption below.
    pinMode(D5, OUTPUT);
    digitalWrite(D5, HIGH);
    pmPowerTime = millis();
    pinMode(D6, OUTPUT);
    digitalWrite(D6, LOW);
    delay(20); // CCS811 power-on <=20 ms, reset <=2 ms, nWAKE <=50 us.
}

bool reportDue(uint32_t now) {
    if (!firstReport) return elapsed(now, lastReport, reportInterval);
    // Successful start commands may complete after the nominal six-second
    // startup point. Wait six full seconds from their actual completion.
    return elapsed(now, pmPowerTime, 12000) &&
        (!pmStarted || elapsed(now, pmStartTime, 6000));
}

void logCcsError() {
    uint8_t errorId = 0;
    if (ccs811.readRegister(CSS811_ERROR_ID, &errorId) == CCS811Core::CCS811_Stat_SUCCESS)
        Log.warn("CCS811 ERROR_ID=0x%02x", errorId);
    else Log.warn("CCS811 ERROR_ID read failed");
    // Datasheet v1.06 p18: reading ERROR_ID clears STATUS.ERROR. This does
    // not prove a physical fault is resolved; leave this sample invalid.
}

void logCcsStatus(uint8_t status) {
    // Log the poll's existing STATUS read before ERROR_ID can clear ERROR.
    Log.warn("CCS811 STATUS=0x%02x DATA_READY=%d ERROR=%d APP_VALID=%d FW_MODE=%d",
        status, !!(status & 0x08), !!(status & 0x01),
        !!(status & 0x10), !!(status & 0x80));
}

void readEnvironment() {
    environmentValid = false;
    if (!siReady) return;
    humidity = si7021.readHumidity();
    const bool rhValid = si7021.wasLastMeasurementValid;
    temperature = si7021.readTemperature();
    environmentValid = rhValid && si7021.wasLastMeasurementValid &&
        std::isfinite(temperature) && std::isfinite(humidity) &&
        temperature >= -40 && temperature <= 125 && humidity >= 0 && humidity <= 100;
    if (!environmentValid) {
        Log.warn("Si7021 measurement failed");
        return;
    }
    environmentTime = millis();
    if (ccsReady && ccs811.setEnvironmentalData(humidity, temperature) != CCS811Core::CCS811_Stat_SUCCESS)
        Log.warn("CCS811 compensation write failed");
}

void readVoc() {
    if (!ccsReady) return;
    uint8_t status = 0;
    if (ccs811.readRegister(CSS811_STATUS, &status) != CCS811Core::CCS811_Stat_SUCCESS) {
        vocValid = false;
        if (!vocErrorLogged) Log.warn("CCS811 status/communication error");
        vocErrorLogged = true;
        return;
    }
    if (status & 0x01) {
        vocValid = false;
        logCcsStatus(status);
        logCcsError();
        return;
    }
    if (!(status & 0x80)) {
        vocValid = false;
        if (!vocErrorLogged) Log.warn("CCS811 not in application mode");
        vocErrorLogged = true;
        return;
    }
    if (!(status & 0x08)) return; // No new data; timestamp still expires.
    if (ccs811.readAlgorithmResults() != CCS811Core::CCS811_Stat_SUCCESS) {
        vocValid = false;
        if (!vocErrorLogged) Log.warn("CCS811 measurement failed");
        vocErrorLogged = true;
        return;
    }
    eco2 = ccs811.getCO2();
    tvoc = ccs811.getTVOC();
    vocValid = eco2 >= 400 && eco2 <= 29206 && tvoc <= 32768;
    if (vocValid) {
        vocTime = millis();
        vocErrorLogged = false;
    } else {
        if (!vocErrorLogged) Log.warn("CCS811 invalid measurement range");
        vocErrorLogged = true;
    }
}

void readPm() {
    uint16_t nextPm25 = 0, nextPm10 = 0;
    const auto result = honeywell.read(nextPm25, nextPm10);
    if (result != HoneywellPM::Result::OK) {
        Log.warn("Honeywell read: %s", HoneywellPM::status(result));
        return;
    }
    if (nextPm25 > 1000 || nextPm10 > 1000) {
        Log.warn("Honeywell invalid measurement range");
        return;
    }
    pm25 = nextPm25;
    pm10 = nextPm10;
    pmValid = true;
    pmTime = millis();
}

void report() {
    const uint32_t now = millis();
    const bool env = environmentValid && !elapsed(now, environmentTime, freshnessTime);
    const bool voc = vocValid && !elapsed(now, vocTime, freshnessTime) &&
        ccsConditioned;
    const bool pm = pmValid && !elapsed(now, pmTime, pmFreshnessTime);
    char payload[256];
    JSONBufferWriter json(payload, sizeof(payload) - 1);
    json.beginObject();
    json.name("pm25"); if (pm) json.value(pm25); else json.nullValue();
    json.name("pm10"); if (pm) json.value(pm10); else json.nullValue();
    json.name("temperature"); if (env) json.value(temperature, 2); else json.nullValue();
    json.name("humidity"); if (env) json.value(humidity, 2); else json.nullValue();
    json.name("tvoc"); if (voc) json.value(tvoc); else json.nullValue();
    json.name("eco2"); if (voc) json.value(eco2); else json.nullValue();
    const int32_t rssi = WiFi.ready() ? WiFi.RSSI() : 0;
    json.name("rssi"); if (rssi < 0) json.value(rssi); else json.nullValue();
    json.endObject();
    if (json.dataSize() >= sizeof(payload)) {
        Log.error("JSON buffer overflow; report skipped");
        return;
    }
    payload[json.dataSize()] = '\0';
    Log.info("Readings: %s", payload);
    Log.info("Wi-Fi=%s Cloud=%s Publish=%s", WiFi.ready() ? "ready" : "offline",
        Particle.connected() ? "connected" : "offline", publishEnabled ? "enabled" : "disabled");
    if (ccsReady && !ccsConditioned)
        Log.info("CCS811 conditioning; raw TVOC=%u eCO2=%u valid=%d", tvoc, eco2, vocValid);

    if (publishEnabled) {
        if (!Particle.connected()) Log.warn("Publish skipped: cloud offline");
        else if (Particle.publish("air_quality", payload)) Log.info("Publish accepted");
        else Log.warn("Publish failed");
    }
}
} // namespace

void setup() {
    initializeUsbSerial(); // Development wait precedes application logging/sensors.
    Log.info("Device OS %s; publishing %s", System.version().c_str(), publishEnabled ? "enabled" : "disabled");
    Wire.setSpeed(CLOCK_SPEED_100KHZ);
    Wire.begin();
    siReady = si7021.begin();
    Log.info("Si7021 0x40: %s", siReady ? "detected" : "initialization failed");

    // v04 D5 is BOTH Honeywell power enable and CCS811 active-low reset.
    // Never cycle D5 to recover either sensor after this initial configuration.
    initializeControlPins();
    auto status = ccs811.beginWithStatus(); // Uses I2C software reset.
    ccsReady = status == CCS811Core::CCS811_Stat_SUCCESS;
    if (ccsReady) {
        // beginWithStatus() now waits after APP_START and selects 1-second mode.
        ccsStartTime = millis();
    }
    if (status == CCS811Core::CCS811_Stat_INTERNAL_ERROR) {
        uint8_t deviceStatus = 0;
        if (ccs811.readRegister(CSS811_STATUS, &deviceStatus) == CCS811Core::CCS811_Stat_SUCCESS) {
            logCcsStatus(deviceStatus);
            if (deviceStatus & 0x01) logCcsError();
        }
    }
    Log.info("CCS811 0x5A: %s (%s)", ccsReady ? "detected" : "initialization failed", ccs811.statusString(status));
    Serial1.begin(9600); // Default SERIAL_8N1; standard TX/RX pins.
    Log.info("Honeywell UART started; initialization scheduled after power settling");
    Log.info("Wi-Fi=%s Cloud=%s", WiFi.ready() ? "ready" : "offline", Particle.connected() ? "connected" : "offline");
}

void loop() {
    uint32_t now = millis();
    // Latch conditioning completion so millis() rollover cannot restart it.
    if (ccsReady && !ccsConditioned && elapsed(now, ccsStartTime, conditioningTime))
        ccsConditioned = true;
    if (elapsed(now, lastEnvironment, 5000)) {
        lastEnvironment = now;
        readEnvironment();
    }
    if (elapsed(now, lastVoc, 1000)) {
        lastVoc = now;
        readVoc();
    }
    // Initialization failures get a simple, bounded retry every 60 seconds.
    if (!pmStarted && elapsed(now, pmPowerTime, 6000) &&
        (lastPmAttempt == 0 || elapsed(now, lastPmAttempt, pmRetryInterval))) {
        lastPmAttempt = now;
        const auto result = honeywell.start();
        pmStarted = result == HoneywellPM::Result::OK;
        pmStartTime = millis();
        Log.info("Honeywell initialization: %s", HoneywellPM::status(result));
    }
    now = millis();
    if (pmStarted && elapsed(now, pmStartTime, 6000) &&
        (lastPmRead == 0 || elapsed(now, lastPmRead, pmSampleInterval))) {
        lastPmRead = now;
        readPm();
    }
    now = millis();
    if (reportDue(now)) {
        lastReport = now;
        firstReport = false;
        report();
    }
}
