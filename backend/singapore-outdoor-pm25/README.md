# Central Singapore outdoor PM2.5

A scheduled UbiFunction that adds NEA's one-hour regional outdoor PM2.5 to the
existing indoor air quality device in Ubidots. CapitaSpring in the CBD uses
**central** as the configured region. This is regional background context, not
a sensor immediately outside the tower or an instantaneous indoor/outdoor ratio.

```text
Argon → Particle → existing webhook → Ubidots indoor variables
NEA PM2.5 API → scheduled UbiFunction → same device, outdoor_pm25_1h
```

Firmware and the existing indoor webhook require no changes. This backend is an
educational reference implementation, ready for local review/testing. It has not
been deployed or tested against the owner's Ubidots account. The device API label
and secure API credentials must be configured before deployment; credentials are
never included in the shared repository.

## Behavior and data contract

The function runs every 15 minutes after its schedule is enabled. It reads
`data.items[].readings.pm25_one_hourly.central` from
`https://api-open.data.gov.sg/v2/real-time/api/pm25`. It selects the newest
observation by timestamp, then the newest revision, rather than assuming array
order. All timestamps must carry a timezone. Missing values, null, booleans,
strings, negative/nonfinite numbers, source errors and observations over three
hours old are rejected. Numeric zero is valid. A five-minute future-clock
allowance accommodates minor skew; the update timestamp must not precede the
observation. Failed reads never become a zero reading or a refreshed old reading.

Only `outdoor_pm25_1h` is written. Its dot uses NEA's observation timestamp in Unix
milliseconds, not the function execution time. Context includes region, one-hour
averaging period, unit, dataset ID and NEA observation/update timestamps.
`tests/fixtures/pm25.json` contains invented test readings, not recorded NEA data.

Before writing, the function verifies the existing device label. It reads the
latest outdoor dot and skips an unchanged observation, an older observation, or
an older source revision. A corrected reading is written at its original source
timestamp. Ubidots permits one dot per timestamp per variable, so resubmitting
that timestamp replaces the same dot. This read/compare/write sequence is not an
atomic transaction: overlapping invocations may still submit the same dot, and
a simultaneous newer revision is not protected by a compare-and-swap lock.

Requests have four-second socket timeouts, bounded response sizes, no redirects,
and no internal retries. A later scheduled run retries current data. Set the
function timeout to 30 seconds. Socket timeouts do not guarantee a strict total
wall-clock deadline for DNS or trickling responses; the cloud runtime timeout
is the outer limit. HTTP success alone is insufficient: the returned outdoor
variable's status must also indicate successful ingestion.

## Local tests and preview

From the repository root, with Python 3.11+ recommended:

```sh
python3 -m unittest discover -s backend/singapore-outdoor-pm25/tests -v
python3 backend/singapore-outdoor-pm25/tools/preview.py \
  --fixture backend/singapore-outdoor-pm25/tests/fixtures/pm25.json \
  --at 2026-10-12T16:20:00+08:00
```

These commands do not contact Ubidots. To preview the latest public NEA data:

```sh
python3 backend/singapore-outdoor-pm25/tools/preview.py
```

The preview tool never writes to Ubidots. An API key is optional for this testing
path, but the deployed function requires a configured `DATAGOVSG_API_KEY` for
production. Supply it through a private environment; never put a key on a command
line, in a public file or in a test fixture. Public requests may be rate-limited.

## Reusable VS Code workflow

For the shared workspace, account profiles, tests and new-function starter, use
[backend/README.md](../README.md). Its profile-suffixed remote function names
isolate development/production copies. The manual commands below remain supported
for an unsuffixed deployment; choose one path consistently for a given function.

## VS Code → UbiFunctions deployment

Use an isolated tooling environment. This implementation pins **ubidots-cli
2.1.2**, whose command/manifest structure differs from older website examples:

```sh
python3.12 -m venv backend/singapore-outdoor-pm25/.venv
source backend/singapore-outdoor-pm25/.venv/bin/activate
python -m pip install -r backend/singapore-outdoor-pm25/requirements-dev.txt
ubidots login
```

`ubidots config` is the interactive alternative for an account token. The local
CLI login/profile is a deployment credential, separate from the function's
runtime account-token binding. Keep profiles outside Git. Use **Python 3.12 for the CLI** (3.14 passed locally on macOS, but its older
CLI dependencies require system development headers on a clean Linux runner); the cloud code targets
`python3.11:lite`. CLI 2.1.2 declares support for older Python versions but its
OAuth module uses Python 3.12 syntax, as confirmed by the first packaging CI run. Docker is optional for
this workflow: unit tests run directly and cloud deployment uses the CLI. Its
optional Docker commands are `ubidots functions dev ...`, rather than the older
`functions new/start` commands.

Prepare a private deployment directory using the **actual existing device API
label** (shown below the device icon in Ubidots), not its display name or a token:

```sh
python backend/singapore-outdoor-pm25/tools/prepare_deployment.py \
  --device-label YOUR_ACTUAL_DEVICE_API_LABEL
cd backend/singapore-outdoor-pm25/.deploy/singapore-outdoor-pm25
ubidots functions push
```

This uploads the prepared function in **preview mode**, with HTTP invocation and
the schedule disabled. The CLI prompts to create it or overwrite an existing
binding. Inspect the destination before confirming. `.deploy/` and local
`.manifest.yaml` are ignored by Git. The preparation script preserves remote
identity on subsequent runs and refuses unexpected extra files. The CLI upload
was checked to contain only `main.py` and `config.json`; do not add secret files
to this directory. Git ignore rules alone do not control the CLI upload archive.

Configure the function in Ubidots before enabling it:

1. Select the account token in the function's **Token** setting. Ubidots supplies
   it to `main(args)` as `_auth_token`. The code does not consume a caller's ordinary
   `token`, `device`, `region` or mode arguments. An optional `UBIDOTS_TOKEN` private
   environment fallback exists for local/custom-runtime use.
2. Create a text-format Secret Global Property labelled `DATAGOVSG_API_KEY`, enter
   your key privately, and bind it to the function's environment. The label and
   raw environment value must match exactly; do not enter JSON into a text secret.
   Global Properties currently require the account feature described in Ubidots'
   guide. Confirm availability before deployment; do not substitute a committed
   credential if that feature is unavailable.
3. The device label is public configuration. `UBIDOTS_DEVICE_LABEL` can override
   the generated config if desired. **ARGON_UBIDOTS_KEY is a credential, not the
   device label**; keep the two separate. Literal `{{...}}` templates are rejected.
4. Keep HTTP invocation disabled, use non-raw mode and a 30-second timeout. Run a
   preview from the owner's authenticated console and verify central-region data.
   Confirm that the selected account token is available on scheduled invocations
   before considering live operation validated.

After review and successful preview, return to the repository root and prepare
live mode (still without a schedule):

```sh
python backend/singapore-outdoor-pm25/tools/prepare_deployment.py \
  --device-label YOUR_ACTUAL_DEVICE_API_LABEL --live
cd backend/singapore-outdoor-pm25/.deploy/singapore-outdoor-pm25
ubidots functions push
```

Run once from the owner console. Verify the correct existing device, outdoor dot,
original timestamp and context; verify a second run skips unchanged data. Set the
new variable unit to `µg/m³`. Confirm indoor updates continue independently.

Finally prepare/push with `--live --enable-schedule` to enable
`*/15 * * * *`. Confirm the secret and selected account token bindings survive
redeployment. The CLI preserves remote environment references during code pushes,
but check the live settings rather than assume account-specific behavior.
Do not use a default every-minute schedule from an old template.

## Dashboard, rollback and contributions

Label the outdoor widget **Outdoor PM2.5 — Central Singapore (1-hour average)**.
Show its observation timestamp and flag it stale after the configured three-hour
limit. A failed refresh leaves the prior dot in Ubidots; that dot does not mean
fresh data. The indoor firmware's minute cadence is not a minute-average metric.
Do not call the ratio an infiltration efficiency without a defined, matched
averaging/measurement method.

For rollback, disable only this function's schedule in Ubidots. Indoor ingestion
continues. Keep the previous reviewed commit and private function binding, then
prepare and push the previous code if required. Never restore secrets from Git.

Fork the repository, branch from `main`, modify `backend/`, run tests and submit
a PR. A separate reviewer should check timestamps, region selection, credentials,
missing/zero data, idempotency and failure handling. Owner review and live
acceptance follow before publishing a validated deployment claim. See
[CONTRIBUTING.md](../../CONTRIBUTING.md) and [VALIDATION.md](VALIDATION.md).

## Primary references

- [NEA PM2.5 dataset](https://data.gov.sg/datasets/d_e1058d6974c877257e32048ab128ad83/view)
- [data.gov.sg PM2.5 API](https://guide.data.gov.sg/developer-guide/real-time-apis)
- [Ubidots CLI source and current workflow](https://github.com/ubidots/ubidots-cli)
- [UbiFunctions CLI guide](https://dev.ubidots.com/sdks/cli/ubifunctions)
- [Account token](https://dev.ubidots.com/ubifunctions/advanced/account-token)
- [Configured token example using _auth_token](https://help.ubidots.com/en/articles/9377159-connect-teltonika-trb140-modbus-iot-gateway-to-ubidots-using-mqtt)
- [Secret Global Properties](https://help.ubidots.com/en/articles/9265555-ubifunctions-using-global-properties)
- [Send timestamped dots](https://docs.ubidots.com/v1.6/reference/send-data-to-a-device)
- [Retrieve existing dots](https://docs.ubidots.com/v1.6/reference/live-test-get-variable-data)
