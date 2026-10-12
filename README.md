# Air Quality Wing — Particle Argon

An educational air quality monitor using **Particle Argon**, Circuit Dojo Air
Quality Wing v04 and a Honeywell HPMA115S0 particulate sensor. Argon is the only
supported hardware target. The current setup uses USB 5 V power without a LiPo.

**Honeywell + Si7021 + CCS811 → Argon Wi-Fi → Particle Cloud → Ubidots webhook**

The firmware publishes one `air_quality` JSON event every 60 seconds after
startup. It reports PM2.5, PM10, temperature, humidity, TVOC, estimated eCO₂ and
Wi-Fi RSSI. Invalid, stale or conditioning-period readings are `null`.
eCO₂ is a VOC-derived estimate, not a direct CO₂ measurement.

The owner reports all seven variables arriving in Ubidots. This is an existing
cloud integration, not a new live test performed by this documentation update.
[Validation evidence and remaining checks](docs/VALIDATION.md) distinguish host
checks, Argon builds and hardware/cloud results.

## Start here

| Document | Purpose |
| --- | --- |
| [Technical reference](docs/HARDWARE_REFERENCE.md) | Argon pins, power, sensor protocols, timing, validity, library fixes and builds |
| [Webhook integration](docs/WEBHOOK_INTEGRATION.md) | Exact event schema, Ubidots routing, cloud secrets and delivery checks |
| [Vibe Coding Challenge](docs/VIBE_CODING_CHALLENGE.md) | Learning goals, independent AI roles and backend ideas |
| [Starter prompts](docs/STARTER_PROMPT.md) | Copy-and-adapt developer and independent reviewer prompts |
| [Contributing](CONTRIBUTING.md) | Fork, branch, tests, PR and owner hardware approval |

## Build and run checks

Particle Workbench is configured for **Argon / Device OS 6.4.1**. Use **Compile
application (local)**. Keep the vendored libraries and their fixes. The
[technical reference](docs/HARDWARE_REFERENCE.md#build-and-host-checks) contains
local build commands and three host regression checks. CI targets Argon/6.4.1 on
pull requests and pushes to `main`; it builds only. A green host test is not a
hardware test. Contributors submit PRs; the owner approves and flashes hardware.

## Particle → Ubidots

The application already publishes `air_quality`; no Ubidots library or credential
is needed on the device. A Particle webhook POSTs the JSON to Ubidots. Store the
Ubidots credential as a Particle Cloud Secret and reference it from the webhook
header. Never put credentials in firmware, examples, issues, PRs or screenshots.
See the [setup and verification guide](docs/WEBHOOK_INTEGRATION.md), including
how `null` readings and stale dashboard values must be handled.

## Vibe Coding Challenge

Try using an AI coding assistant to improve a real embedded monitor. Choose a
small, testable improvement, or propose alternative firmware with a clear reason
and compatibility plan. Learn to write a precise prompt, inspect generated code,
test failure cases, and explain what remains unverified.

Start with the [technical reference](docs/HARDWARE_REFERENCE.md) and
[starter prompt](docs/STARTER_PROMPT.md). Keep three roles separate:

- **LLM developer:** implements a scoped change and provides evidence.
- **Independent LLM reviewer:** reads the actual diff, hardware reference and tests
  in a separate session, checks assumptions, and reports findings with locations.
- **Human owner:** approves the change, flashes Argon, validates real sensors and
  cloud delivery, and decides when to merge.

Fork → create a branch → implement → run checks → independent review → open a PR
with evidence → owner approval and hardware testing. Compilation is one stage,
not proof that the device works. See [challenge details](docs/VIBE_CODING_CHALLENGE.md)
and [contribution instructions](CONTRIBUTING.md).

## Backend integrations challenge

Prefer dashboards, data storage or visualizations? Build a backend using sample
`air_quality` JSON first. [Open a GitHub issue](https://github.com/chipmc/Air-Quality-Wing/issues/new)
with your proposed backend, HTTPS endpoint, JSON mapping, missing-data behavior,
authentication method, and test plan. The owner can consider adding a Particle
webhook to your backend. Share credentials privately through an agreed secure
channel after acceptance; keep them out of the issue. Firmware changes are
usually unnecessary. See the [backend challenge](docs/VIBE_CODING_CHALLENGE.md#optional-backend-challenge).

## Dependencies

Vendored `particleflux-Si7021` 1.2.1 and
`SparkFun_CCS811_Arduino_Library` 2.0.1 retain their upstream MIT license notices.
Required short-read, initialization and timing fixes are documented in the
[technical reference](docs/HARDWARE_REFERENCE.md#vendored-dependencies-and-required-fixes).

## Indoor + outdoor PM2.5 backend

The [scheduled outdoor PM2.5 UbiFunction](backend/singapore-outdoor-pm25/README.md)
adds NEA's central-region one-hour PM2.5 to the existing Ubidots device every
15 minutes after deployment and schedule activation. It includes source, tests,
credential-free sample data and a pinned CLI workflow for VS Code. Indoor
firmware and its webhook are unchanged. Regional outdoor context and recent
indoor measurements have different measurement periods.

The implementation is prepared for sharing and owner deployment; see its
[validation record](backend/singapore-outdoor-pm25/VALIDATION.md) before assuming
it has been deployed or tested with live credentials.
