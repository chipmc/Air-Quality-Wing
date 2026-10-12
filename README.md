# Air Quality Wing — Photon 2

Minimal diagnostics for Circuit Dojo Air Quality Wing v04 (BRD-0010-04),
Honeywell HPMA115S0, Si7021 and CCS811. Target: Photon 2 (`p2`), Device OS 6.4.1.
USB 5 V power, no LiPo. No sleep, display or Ubidots integration.

## Published libraries and required changes

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

## Hardware

See [Circuit Dojo v04 schematic](https://github.com/circuitdojo/air-quality-wing-hardware/blob/master/pdf/air-quality-wing-rev4.pdf).

| Signal | Photon 2 connection |
| --- | --- |
| Si7021 SDA/SCL, address 0x40 | D0/D1 (`Wire`, 100 kHz) |
| CCS811 SDA/SCL, address 0x5A | D0/D1 |
| CCS811 nRESET and Honeywell power enable | **D5 HIGH during operation** |
| CCS811 nWAKE | **D6 LOW during operation** |
| CCS811 nINT (Wing label D8) | Photon 2 D10/WKP; polling, no interrupt configured |
| Honeywell RX input | Photon 2 TX/D8 (`Serial1`) |
| Honeywell TX output | Photon 2 RX/D9 (`Serial1`) |
| Honeywell UART | 9600 baud, 8 data bits, no parity, 1 stop bit |

D5 HIGH releases CCS811 reset and enables the Honeywell 5 V USB supply path.
D5 LOW disables that supply and asserts CCS811 reset. D5's 4.7 kΩ reset pull-up
outweighs its 100 kΩ pull-down when 3.3 V is established; do not assume power is
off at boot. USB presence disables the battery boost converter. GPIO setup
occurs only after boot; UART pins are not remapped or manipulated as GPIO.

C1: Device OS 6.4.1's `wiring_globals/src/spark_wiring_gpio.cpp` makes
`digitalWrite()` return without writing when the pin is an input or has no mode.
The application now calls `pinMode(OUTPUT)` **before** writing D5 HIGH and D6 LOW.
A brief D5 LOW pulse between mode configuration and the HIGH write is possible;
it may reset CCS811 and interrupt Honeywell power. A 20 ms settling delay follows
both writes (CCS811 power-on <=20 ms, reset recovery <=2 ms, wake <=50 µs).
Honeywell power settling is timed from the actual D5 HIGH write, not setup entry.
The subsequent CCS811 software reset provides a defined sensor initialization
regardless of the pulse width. This does not guarantee a glitch-free electrical
transition; pulse width and rail behavior still need an oscilloscope check.

M2: [CCS811 datasheet v1.06, page 18](https://cdn.sparkfun.com/assets/2/c/c/6/5/CN04-2019_attachment_CCS811_Datasheet_v1-06.pdf)
explicitly specifies that reading register `ERROR_ID` (0xE0) clears `STATUS.ERROR`;
reading STATUS or the error byte inside ALG_RESULT_DATA does not. When STATUS
reports an error, the application reads 0xE0 with transport status checking and
logs its hexadecimal bit mask (or a read failure). The current sample remains
invalid. The next poll checks STATUS again: clearing the flag does not establish
that a heater/sensor fault is resolved. No automatic reset/recovery was added.

## Boot limitation

Photon 2 TX/D8 is boot-sensitive: LOW selects MCU ISP download mode. The attached
Honeywell has experimentally prevented startup; booting without it succeeded.
Connecting it after successful boot has also worked in the user's experiment.
This is a temporary bench workaround, **not a permanent hot-plug procedure**:
powered connector insertion carries electrical risk. A reviewed hardware solution
is still required for reliable cold starts, resets and OTA restarts. Firmware
assumes successful boot and sensor connection before initialization; it cannot
fix the earlier boot conflict. Do not flash or change hardware until review.

## Diagnostics and publishing

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
M3: The first diagnostic report occurs no earlier than 12 seconds after D5 HIGH,
and, if Honeywell initialization succeeds, no earlier than six seconds after the
start commands actually complete. This is normally slightly later than 12 seconds,
then reports repeat every 60 seconds. A missing Honeywell does not postpone the
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

## Build only — do not flash yet

Use Particle Workbench **Compile application (local)** with platform `p2` and
Device OS `6.4.1` (already selected in `.vscode/settings.json`). Preserve the
vendored dependencies: reinstalling them would overwrite the documented fixes.
No cloud build or CI execution has been validated.

The equivalent local build command used on this machine, from the project root:

```sh
make -s -C /Users/chipmc/.particle/toolchains/deviceOS/6.4.1/main all \
  PLATFORM=p2 APPDIR="$PWD" TARGET_DIR="$PWD/target/6.4.1/p2" \
  BUILD_PATH_BASE=/tmp/aqw-build-default \
  GCC_ARM_PATH=/Users/chipmc/.particle/toolchains/gcc-arm/10.2.1/bin/
```

To check the diagnostics-only variant, add `EXTRA_CFLAGS=-DENABLE_PUBLISH=false` and use
`TARGET_DIR="$PWD/target/6.4.1/p2-publish-disabled"`. **Clean the application object
cache before changing flags**: Make does not track `EXTRA_CFLAGS` changes. A new
output directory alone does not force application recompilation. Workbench's
local application-clean command can do this; during validation only the generated
`/tmp/aqw-build-default/user/platform-32-m/Air-Quality-Wing` cache was removed.

Default publishing-enabled and diagnostics-only variants were rebuilt successfully
for Photon 2 / Device OS 6.4.1. The default binary includes `air_quality` and the
publish-result strings; the disabled binary omits them. Two non-fatal warnings remain in unchanged portions of
SparkFun's source: `#elif __AVR__` triggers `-Wundef` because the AVR macro is
undefined on Photon 2 (the expression evaluates to zero), and the unused local
`result` triggers `-Wunused-variable`. Neither is an error or a GPIO warning. Application and Honeywell sources compile without warnings. These
cosmetic library warnings were left alone to keep source changes restricted to
demonstrated functional defects.

## Host regression checks

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

All three checks passed with undefined-behavior instrumentation. Honeywell cases cover
start/stop-auto commands, valid measurements, bad checksums, NACK, partial/missing
responses, ACK-only reads, noise resynchronization, overlapping auto-send frames
and timer rollover. Library cases cover missing/short reads, failed commands,
valid data, CRC failures, initialization failure and the APP_START delay before
any subsequent I²C transaction. Application cases compile the actual helper
functions with focused fakes and cover GPIO ordering/output states/settling,
first-report warmup including delayed command ACKs, missing PM, minute cadence,
timer rollover, checked ERROR_ID reads, error-only STATUS warnings, absence of
routine CCS811 INFO logs and negative/zero/positive/offline RSSI.
Both development/production USB wait settings are tested: 115200 initialization,
immediate/delayed monitor connection, a bounded no-monitor timeout, rollover and
no waiting when disabled. The test also checks that USB initialization is the
first operation in `setup()`.
Stubs establish software
behavior only; they do not validate electrical timing, sensor accuracy, USB
logging, Wi-Fi connectivity or cloud delivery.

## Hardware test procedure — after independent review and approval

1. Review the source and documented library fixes before any flash operation.
2. Resolve/arrange the reviewed temporary boot setup, then flash a publishing-disabled
   diagnostics build using Workbench. No flashing is performed by this work order.
3. Open `particle serial monitor --follow` at 115200. Verify Device OS 6.4.1,
   Si7021/CCS811 detection, Honeywell ACKs, and Wi-Fi/cloud status.
4. Inspect the first JSON diagnostic line after the full Honeywell measurement wait and subsequent lines
   every minute. Confirm temperature/humidity and PM values; check VOC raw values
   during conditioning and populated VOC JSON fields after 20 minutes.
5. Test missing sensors using safely prepared, powered-off connector arrangements
   and the reviewed boot setup. Confirm timeout/failure logs and `null` fields
   while cloud connectivity continues. Do not use powered connector insertion as
   a routine test method. A sensor missing at I2C initialization requires a restart.
6. Only after diagnostics are accepted, rebuild with publishing enabled and,
   following approval, flash that variant. Check one `air_quality` event per
   minute in Particle Console and parse its data as JSON. Disable Wi-Fi to verify
   that publishing is skipped and diagnostics continue.

## Known limitations

No Photon 2 has been flashed or hardware-tested by this implementation work.
Cold-start/reset behavior with Honeywell attached remains a hardware problem.
UART deadlines, corrected CCS811/GPIO startup timing, sensor conditioning and
accuracy, USB power/inrush behavior, disconnected-sensor operation on real
hardware and cloud delivery still need bench validation. The firmware uses
bounded communication and basic validity checks; it deliberately omits advanced
recovery, calibration/baseline storage and persistent event queues. Supported
I2C transactions use Device OS's finite default timeout; UART retries cannot
resolve the pre-application boot conflict.
