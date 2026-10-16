# Air Quality Wing: technical reference for AI coding assistants

## Scope and source of truth

Particle **Argon is the only supported target**, with Circuit Dojo Air Quality
Wing v04 (BRD-0010-04), Honeywell HPMA115S0, Si7021 and CCS811. The project selects
Device OS **6.4.1** and platform **argon** (platform ID 12). These are target
settings, not evidence that a particular revision has been built or tested.
Use [VALIDATION.md](VALIDATION.md) for revision-specific evidence.

The owner reports a working Particle `air_quality` → Ubidots integration and now
uses Argon. That does not certify every failure case or future firmware change.
This document describes the checked-in implementation; if source and reference
conflict, report the discrepancy before changing behavior. Update this document
with any intentional contract change. Read `src/Air-Quality-Wing.cpp`,
`src/HoneywellPM.{h,cpp}`, the vendored libraries, `project.properties`, and
`tests/host/` alongside it. Preserve working firmware unless the task requires a
specific change. No sleep, local display, baseline persistence or event queue is
implemented. Backend access credentials are held in the cloud, never firmware.

## Hardware and pin mapping

Primary references:
[Wing v04 schematic](https://github.com/circuitdojo/air-quality-wing-hardware/blob/master/pdf/air-quality-wing-rev4.pdf),
[Argon datasheet](https://docs.particle.io/reference/datasheets/wi-fi/argon-datasheet/),
and [Device OS versions](https://docs.particle.io/reference/device-os/versions/).
Device OS 6.4.1's `hal/src/argon/pinmap_defines.h` defines SDA=D0, SCL=D1,
TX=D9, RX=D10 and WKP=D8. Use the Argon mapping, not assumed numeric UART pins.

| Wing signal | Argon connection and behavior |
| --- | --- |
| Si7021 SDA/SCL, address 0x40 | D0/D1 (`Wire`, 100 kHz) |
| CCS811 SDA/SCL, address 0x5A | D0/D1 |
| CCS811 nRESET and Honeywell power enable | D5 HIGH during operation |
| CCS811 nWAKE | D6 LOW during operation |
| CCS811 nINT | D8/WKP; polling only, no interrupt configured |
| Honeywell RX input | Argon TX/D9 (`Serial1`) |
| Honeywell TX output | Argon RX/D10 (`Serial1`) |
| Honeywell UART | 9600 baud, 8 data bits, no parity, 1 stop bit |

USB 5 V power, no LiPo, is the current setup. GPIO is 3.3 V logic; 5 V power is
not permission to apply 5 V to an Argon GPIO. Attach the required Argon Wi-Fi
antenna. Assemble or change sensor connections with power removed. Validate cold
start, reset and reconnect behavior on Argon; do not infer bench results from
host tests.

D5 HIGH releases CCS811 reset and enables the Honeywell 5 V USB supply path.
D5 LOW disables that supply and asserts CCS811 reset. D5's 4.7 kΩ reset pull-up
outweighs its 100 kΩ pull-down when 3.3 V is established; do not assume power is
off at boot. USB presence disables the battery boost converter. GPIO setup
occurs only after boot; UART pins are not remapped or manipulated as GPIO.

Device OS 6.4.1's `wiring_globals/src/spark_wiring_gpio.cpp` makes
`digitalWrite()` return without writing when the pin is an input or has no mode.
The application now calls `pinMode(OUTPUT)` **before** writing D5 HIGH and D6 LOW.
A brief D5 LOW pulse between mode configuration and the HIGH write is possible;
it may reset CCS811 and interrupt Honeywell power. A 20 ms settling delay follows
both writes (CCS811 power-on <=20 ms, reset recovery <=2 ms, wake <=50 µs).
Honeywell power settling is timed from the actual D5 HIGH write, not setup entry.
The subsequent CCS811 software reset provides a defined sensor initialization
regardless of the pulse width. This does not guarantee a glitch-free electrical
transition; pulse width and rail behavior still need an oscilloscope check.

[CCS811 datasheet v1.06, page 18](https://cdn.sparkfun.com/assets/2/c/c/6/5/CN04-2019_attachment_CCS811_Datasheet_v1-06.pdf)
explicitly specifies that reading register `ERROR_ID` (0xE0) clears `STATUS.ERROR`;
reading STATUS or the error byte inside ALG_RESULT_DATA does not. When STATUS
reports an error, the application reads 0xE0 with transport status checking and
logs its hexadecimal bit mask (or a read failure). The current sample remains
invalid. The next poll checks STATUS again: clearing the flag does not establish
that a heater/sensor fault is resolved. No automatic reset/recovery was added.

## Firmware behavior and event contract

`ENABLE_PUBLISH` defaults to `true` in `src/Air-Quality-Wing.cpp`. Set it to `false`
or pass `EXTRA_CFLAGS=-DENABLE_PUBLISH=false` at compile time to disable events.
Diagnostics-only builds still connect to Wi-Fi/Particle Cloud in AUTOMATIC mode,
but do not call `Particle.publish()`.

At the beginning of `setup()`, `Serial.begin(115200)` initializes USB Serial.
`ENABLE_USB_SERIAL_WAIT` defaults to `true` for development: the application waits
up to 10 seconds for `Serial.isConnected()`, yielding with `delay(1)`, and then
continues even without a monitor. This occurs before application diagnostic
logging and sensor initialization. Device OS 6.4.1 provides both USB Serial APIs;
USB baud is a host setting rather than a physical UART clock.

For production, set `ENABLE_USB_SERIAL_WAIT` to `false` in the source or compile
with `EXTRA_CFLAGS=-DENABLE_USB_SERIAL_WAIT=false`. Serial is still initialized
at 115200. Clean the application cache when changing flags, as described below.
`ENABLE_PUBLISH` remains independently configurable. The optional wait
adds up to 10 seconds before initialization; all existing sensor settling,
conditioning, sample/report intervals and publishing logic remain unchanged.

Initialization follows
Wire → Si7021 → CCS811 → Honeywell UART. D5/D6 are established before CCS811
initialization. Sensors are sampled independently; disconnected sensors do not
stop the main loop or cloud connection. Failed I2C initialization is logged and
requires restarting after correcting hardware; there is no recovery framework.

Environment readings run every five seconds; CCS811 is polled every second.
Honeywell PM readings are requested once per minute and the latest valid sample
remains usable for two minutes, so one failed poll does not lose a report.
The first diagnostic report occurs no earlier than 12 seconds after D5 HIGH,
and, if Honeywell initialization succeeds, no earlier than six seconds after the
start commands actually complete. This is normally slightly later than 12 seconds,
then reports repeat every 15 minutes. A missing Honeywell does not postpone the
first report indefinitely; PM fields are `null`. Honeywell startup waits six
seconds from D5 HIGH for power settling and leaves another six full seconds of
measurement time before reading. Each UART transaction
has a 250 ms total deadline; startup uses at most two transactions. Initialization
failure retries once per minute. D5 remains HIGH after its initial configuration;
there are no runtime power cycles.

CCS811 raw readings appear in diagnostics during its 20-minute conditioning
period, with a validity flag. TVOC/eCO₂ JSON fields remain `null` during that
period. A new sensor can require about 48 hours of initial burn-in; the 20-minute
gate does not establish calibration or accuracy. The later CCS811 datasheet also
specifies 60 minutes before using readings on first power-on; new-sensor readiness
must be checked during diagnostics. See the [CCS811 datasheet](https://cdn.sparkfun.com/assets/2/c/c/6/5/CN04-2019_attachment_CCS811_Datasheet_v1-06.pdf).
eCO₂ is an equivalent estimate,
not a direct CO₂ measurement. No baseline persistence or sensor firmware update
is performed. Valid Si7021 readings provide environmental compensation.

Routine one-second CCS811 STATUS logging is disabled. When STATUS.ERROR is set,
the application logs a warning with the hexadecimal register
and decoded `DATA_READY` (bit 3), `ERROR` (bit 0), `APP_VALID` (bit 4), and
`FW_MODE` (bit 7), for example:
`CCS811 STATUS=0x99 DATA_READY=1 ERROR=1 APP_VALID=1 FW_MODE=1`.
This uses the existing register read and logs before the existing conditional
`ERROR_ID` read, which clears STATUS.ERROR per datasheet page 18. An error logs
`CCS811 ERROR_ID=0xNN` or an explicit read failure; a failed STATUS read retains
the existing communication warning and does not log a fabricated register value.
These diagnostics do not change initialization, conditioning, measurement
cadence, validity checks, or publishing. Null TVOC/eCO₂ in a report about 14 seconds
after boot is expected during conditioning; status logs help distinguish that
gate from sensor errors. Sensor detection and Honeywell initialization messages
remain enabled. Wi-Fi/cloud/publishing status is logged at initialization and
alongside each measurement report, with no per-second application status logs.

Reports use Device OS `JSONBufferWriter` with a fixed 256-byte buffer. Failed,
out-of-range or older-than-10-second samples are `null`; RSSI is `null` when Wi-Fi
is unavailable or its RSSI is zero/positive. Units: `pm25` and `pm10` in µg/m³,
`temperature` in °C, `humidity` in %RH, `tvoc` in ppb, `eco2` in ppm, and `rssi`
in dBm. Example after conditioning:

```json
{"pm25":12,"pm10":21,"temperature":25.40,"humidity":61.20,"tvoc":85,"eco2":620,"rssi":-58}
```

The event name is `air_quality`. Publishing checks cloud connectivity and the
standard `Particle.publish("air_quality", payload)` return status. “Publish
accepted” means API acceptance, not end-to-end delivery confirmation. Offline
reports are logged and dropped; they are not queued as stale measurements.

## Honeywell protocol implementation

`HoneywellPM::start()` sends stop-auto-send (`0x20`) then start-measurements
(`0x01`); `read()` requests a measurement (`0x04`). Commands are
`68 01 <command> <checksum>`, with an 8-bit checksum that makes the sum zero.
ACK is `A5 A5`; NACK is `96 96`. A measurement response is eight bytes beginning
`40 05 04`, followed by big-endian PM2.5 and PM10 and the zero-sum checksum.
An ACK alone does not satisfy a measurement read. The parser drains at most 256
pending bytes, enforces a 250 ms total deadline, resynchronizes after noise,
and consumes overlapping 32-byte auto-send frames (`42 4D`, length 28,
16-bit sum of the first 30 bytes). It returns explicit OK, timeout,
NACK or invalid-frame status without accepting partial readings.

## Vendored dependencies and required fixes

- `particleflux-Si7021` 1.2.1 (MIT).
- `SparkFun_CCS811_Arduino_Library` 2.0.1 (MIT).

Published Particle archives are vendored under `lib/`, with license notices retained.
The following defects were reproduced on the **unchanged** sources using a host
I2C stub before applying any library changes:

1. CCS811 `multiReadRegister()` requested four bytes but received zero. It returned
   `CCS811_Stat_SUCCESS` and left the output buffer unchanged (`12 34 56 78`).
2. Si7021 received a nonzero `endTransmission()` error and a simulated old,
   CRC-valid response. `readTemperature()` returned 24.69 °C and marked it valid.

Required narrow changes: reject short I2C reads in both libraries; propagate
Si7021 command/read failures as `NAN` and clear measurement validity; fail Si7021
initialization if the configuration register cannot be read. Check CCS811 reset
and initialization status transactions so a missing/partial response cannot
start acquisition. Review correction M1 additionally replaces the ESP-only
100 µs APP_START delay with unconditional `delay(1)` immediately after a successful
APP_START transaction, before any measurement-mode access. The CCS811 v1.06
datasheet specifies up to 1 ms before new I²C commands. No algorithms or public
APIs were changed. These fixes prevent invalid/stale data from being
reported as valid; they are not hardware test results.

## Build and host checks

Use Particle Workbench **Compile application (local)** with platform `argon`
and Device OS `6.4.1`, as selected in `.vscode/settings.json`. Keep `lib/` intact:
reinstalling dependencies can overwrite the fixes above. CI uses the same platform
and version and compiles without a Particle access token; it does not flash.

For an installed local Device OS toolchain, from this repository root:

```sh
make -s -C "$DEVICE_OS_DIR/main" all \
  PLATFORM=argon APPDIR="$PWD" TARGET_DIR="$PWD/target/6.4.1/argon" \
  BUILD_PATH_BASE=/tmp/aqw-argon-build \
  GCC_ARM_PATH="$GCC_ARM_DIR/"
```

Set `DEVICE_OS_DIR` to your installed 6.4.1 directory and `GCC_ARM_DIR` to its
ARM compiler's `bin` directory. For the diagnostics-only variant add
`EXTRA_CFLAGS=-DENABLE_PUBLISH=false`; production can use
`EXTRA_CFLAGS=-DENABLE_USB_SERIAL_WAIT=false`. Use a fresh `BUILD_PATH_BASE` or
Workbench's application-clean command when changing flags: a new output directory
alone does not rebuild cached application objects.

The small `tests/host/` stubs exercise actual driver/library source without a
Particle device. They are not part of the firmware build. Run from project root:

```sh
c++ -std=c++14 -Wall -Wextra -Werror -fsanitize=undefined \
  -Itests/host -Isrc tests/host/honeywell_test.cpp src/HoneywellPM.cpp \
  -o /tmp/aqw-honeywell-test
/tmp/aqw-honeywell-test

c++ -std=c++14 -fsanitize=undefined -Itests/host \
  -Ilib/particleflux-Si7021/src -Ilib/SparkFun_CCS811_Arduino_Library/src \
  tests/host/library_regression.cpp \
  lib/particleflux-Si7021/src/Si7021.cpp \
  lib/SparkFun_CCS811_Arduino_Library/src/SparkFunCCS811.cpp \
  -o /tmp/aqw-library-test
/tmp/aqw-library-test
```

Run the focused application checks as well:

```sh
python3 tests/host/application_regression.py
```

Host stubs establish software behavior only. They do not validate GPIO voltage,
electrical timing, sensor accuracy, USB output, Argon Wi-Fi or cloud delivery.

## Owner hardware acceptance checklist

After independent review, the owner approves and flashes the exact reviewed
commit. Participants must not flash the owner's hardware or change integrations.

1. Build an Argon/6.4.1 diagnostics-only variant and record compiler output,
   source commit, flags and binary checksum. Owner flashes it after approval.
2. Monitor USB Serial at 115200. Check Device OS, Si7021/CCS811 detection,
   Honeywell initialization, and Wi-Fi/cloud status. Test boot with everything
   connected, reset and a power cycle without relying on powered insertion.
3. Check first report timing (at least 12 seconds from D5 HIGH and six seconds
   after successful Honeywell start), one-minute PM sampling, then 15-minute
   report cadence. Check PM/environment fields and VOC raw diagnostics; expect
   null VOC fields during 20 minutes.
4. With powered-off connection changes, test missing sensors. Confirm bounded
   failures, null fields and continued reporting; failed I2C initialization needs
   restart after repair. Check stale data, CCS811 errors and Wi-Fi loss.
5. After diagnostics acceptance, owner approves and flashes publishing enabled.
   Confirm JSON in Particle Console and per-variable Ubidots timestamps/values
   and webhook response statuses using [WEBHOOK_INTEGRATION.md](WEBHOOK_INTEGRATION.md).
6. Record pass/fail, remaining limitations and sanitized logs in the PR. Owner
   keeps a known-good firmware binary for rollback and decides when to merge.

## Known limits

The 20-minute gate is a software policy, not proof of sensor calibration or
readiness. New CCS811 sensors need datasheet conditioning/burn-in checks. eCO₂ is
an estimate from VOC response, not directly measured CO₂. There is no automated
I2C reinitialization, persistent delivery queue, baseline storage, or accuracy
certification. D5 pulse/rail timing, power budget, physical sensor failure cases,
and end-to-end delivery need hardware evidence for each changed firmware revision.
