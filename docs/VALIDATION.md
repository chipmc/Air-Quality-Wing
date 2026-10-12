# Validation evidence

This documentation/workflow update was freshly checked on **12 October 2026**
after applying the prepared patch in the owner's checkout. The results below
were rerun for this execution, not copied from patch preparation. Firmware
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
| GitHub Actions execution | Not run locally | Remote run status must be checked on the PR; local results do not certify CI |
| Documentation/configuration checks | Passed | 26 relative links/anchors, nine public links (HTTP 200), Workbench JSON, workflow YAML/target/triggers, obsolete target scan and whitespace checks |
| Independent LLM diff review | Completed | Firmware/library/test sources unchanged; Argon pins and workflow inputs checked; webhook scope and Cloud Secrets link findings corrected |
| New Argon hardware flash/test | Not run | Owner acceptance required |
| New live Particle/Ubidots/null-path test | Not run | Owner reports existing numeric delivery; live settings were not accessed |

## Local build environment and command

GNU Arm Embedded Toolchain 10.2.1 (10-2020-q4-major), Particle Device OS 6.4.1.
From the repository root, default build:

```sh
make -s -C /Users/chipmc/.particle/toolchains/deviceOS/6.4.1/main all \
  PLATFORM=argon APPDIR="$PWD" TARGET_DIR="$PWD/target/6.4.1/argon" \
  BUILD_PATH_BASE=/tmp/aqw-dispatch-argon-enabled \
  GCC_ARM_PATH=/Users/chipmc/.particle/toolchains/gcc-arm/10.2.1/bin/
```

The publishing-disabled check uses a separate clean cache at
`/tmp/aqw-dispatch-argon-disabled`, output
`target/6.4.1/argon-diagnostics`, and `EXTRA_CFLAGS=-DENABLE_PUBLISH=false`.
For portable commands and host test commands, see the
[technical reference](HARDWARE_REFERENCE.md#build-and-host-checks).

The default binary is 22,562 bytes with SHA-256:

```text
bac85ee0094cfeb7f0b5ca711a3a0c79a1fd290700f6d2823beae66cd8f63edd
```

The publishing-disabled binary is 20,674 bytes with SHA-256:

```text
93ce8d63fa252f2780dba41757422c8ea37d636b82cf15588f9aa85ccba03923
```

The initial `make -j4` attempts failed because the Device OS make rules linked
before `libhal-dynalib.a` existed in the fresh caches. Both were rerun without
parallel make, after removing their separate generated application caches, and
completed with exit code 0. No firmware correction was required. Each successful
compilation emitted two existing CCS811 warnings:
`__AVR__` undefined in `#elif` (`-Wundef`) and unused local `result`
(`-Wunused-variable`). No firmware changes were made to suppress them.
Firmware build success does not establish electrical timing, sensor accuracy,
cold-start/reset behavior, or end-to-end delivery.

## Repository and access checks

The active checkout was clean and `git fetch origin` succeeded. Remote `main`
still matched the patch baseline. The prepared changes were not already present;
the patch passed `git apply --check` and was applied with `git am` on
`docs/argon-vibe-coding-challenge`. GitHub CLI reported an invalid login, while
the connected GitHub app reported repository push permission; actual push/PR
results are reported with the task deliverable rather than inferred from these
checks. No credentials were printed or committed. The owner approves and flashes
hardware, validates cloud delivery and decides when to merge. No live integration
was changed.
