# Validation evidence

This documentation/workflow update was checked on **12 October 2026**. Firmware
sources and host tests are unchanged from baseline commit
`b9e32e5072e78058e1bc29717cb102c39a9b8471`; the vendored Si7021 metadata description
was made platform-neutral. These results apply to that source, not future changes.

| Check | Result | Scope |
| --- | --- | --- |
| Honeywell host regression | Passed | Actual driver with host stubs and undefined-behavior instrumentation |
| Vendored library regression | Passed | I2C failures/short reads, CRC and APP_START timing with host stubs |
| Application regression | Passed | GPIO order, warmup/cadence/rollover, error handling, RSSI and both USB-wait settings |
| Argon / Device OS 6.4.1 local build, default flags | Passed | Publishing enabled, USB wait enabled; binary header platform ID 12 |
| Argon publishing-disabled local build | Passed | Clean application cache; platform ID 12; publisher string absent |
| GitHub Actions execution | Not run | Updated workflow configuration; no remote PR was created |
| Documentation/configuration checks | Passed | Relative links, Workbench JSON, workflow YAML, obsolete target scan and whitespace checks |
| New Argon hardware flash/test | Not run | Owner acceptance required |
| New live Particle/Ubidots/null-path test | Not run | Owner reports existing numeric delivery; live settings were not accessed |

## Local build environment and command

GNU Arm Embedded Toolchain 10.2.1 (10-2020-q4-major), Particle Device OS 6.4.1.
From the repository root, default build:

```sh
make -s -C /Users/chipmc/.particle/toolchains/deviceOS/6.4.1/main all \
  PLATFORM=argon APPDIR="$PWD" TARGET_DIR="$PWD/target/6.4.1/argon" \
  BUILD_PATH_BASE=/tmp/aqw-argon-challenge-default \
  GCC_ARM_PATH=/Users/chipmc/.particle/toolchains/gcc-arm/10.2.1/bin/
```

The publishing-disabled check uses a separate clean cache at
`/tmp/aqw-argon-challenge-diagnostics`, output
`target/6.4.1/argon-diagnostics`, and `EXTRA_CFLAGS=-DENABLE_PUBLISH=false`.
For portable commands and host test commands, see the
[technical reference](HARDWARE_REFERENCE.md#build-and-host-checks).

The default binary is 22,562 bytes with SHA-256:

```text
4f0bc2e14b6e50271eff7d1df20eb5e2433bfe5c3324ee7477aaf0090cfd47e3
```

The publishing-disabled binary is 20,674 bytes with SHA-256:

```text
6a13fb081a649ef2ea1409b81950510a1118a0984441bf34e774ca1e1210b9e4
```

Both initial compilations emitted two existing CCS811 warnings:
`__AVR__` undefined in `#elif` (`-Wundef`) and unused local `result`
(`-Wunused-variable`). No firmware changes were made to suppress them.
Firmware build success does not establish electrical timing, sensor accuracy,
cold-start/reset behavior, or end-to-end delivery.

## Remote access limit

The connected GitHub account can read the repository, but creating the requested
branch returned HTTP 403, `Resource not accessible by integration`. The local
GitHub CLI authentication was also invalid. A local branch and a patch/archive
are prepared instead; the remote default branch and live integrations are
unchanged. A maintainer with write access can apply the patch on a new branch and
open a PR. The GitHub workflow remains unverified until it runs there.
