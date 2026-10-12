# Validation record — 12 October 2026

Implementation base: `main` at `5b38a52` (the merged Argon documentation PR).
Firmware sources, host tests and vendored drivers are unchanged by this backend.

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Backend behavior tests | Passed | 24 offline tests covering parsing, selection, timestamps, zero/null/error cases, duplicate/revision handling, configured destination, token selection and sanitized failures |
| CLI packaging tests | Passed | Four additional tests using installed ubidots-cli 2.1.2; private binding preservation, schedule/mode selection, rejected placeholder labels and extra upload files |
| Installed CLI command checks | Passed | `functions push`, `functions update` help inspected; current commands differ from older site examples |
| CLI manifest validation | Passed | Generated configuration accepted by installed CLI model; Python 3.11 lite, timeout 30s, HTTP disabled, initial schedule disabled |
| CLI upload archive | Passed | CLI's own packaging code includes only main.py and config.json; private manifest excluded |
| Offline fixture preview | Passed | Invented central value 15; 2026-10-12 16:00 SGT converted to 1791792000000 ms |
| Public NEA API preview | Failed | Unauthenticated read did not return success from this environment; no data written, no production API key used |
| Workflow / source syntax / links | Passed | YAML/JSON/Python parsing, local relative links and whitespace checks |
| Python 3.11 cloud runtime | Not run | Behavior tested locally with Python 3.10 and 3.14; CI includes Python 3.11 and 3.14 |
| Independent LLM review | Not run | Requires a separate reviewer/session; no independent review claim is made |
| Initial GitHub Actions | Partially passed | Behavior tests passed on Python 3.11/3.14 and host checks passed. Packaging exposed CLI 2.1.2 Python 3.12 syntax despite its older-Python metadata. Packaging now selects verified Python 3.14; confirm the latest run on the PR |
| UbiFunction deployment | Not run | Owner CLI login, actual device API label, data.gov.sg key and account-token binding required |
| Live Ubidots writes and scheduled invocation | Not run | Owner must verify the selected account token reaches the scheduler, settings persist across code pushes, and timestamps/context are stored as expected |

Tests were executed with:

```sh
python3 -m unittest discover -s backend/singapore-outdoor-pm25/tests -v
# With the isolated CLI environment active:
python -m unittest discover -s backend/singapore-outdoor-pm25/tests -v
```

The plain Python run passes behavior tests and skips packaging tests if the CLI
is absent. With CLI 2.1.2 installed, all 28 tests pass. Deployment tooling requires Python 3.12+; local verification used 3.14. The source reference checked
for CLI behavior was upstream commit `fe86b72feafe74d1b4c258e2234959a2138c23f3`.

## Remaining owner acceptance

Configure the actual existing device API label separately from
`ARGON_UBIDOTS_KEY` (a credential). Obtain and privately bind the data.gov.sg key.
Select the Ubidots account token using its supported function setting. Deploy
preview mode with the schedule disabled, review a fresh central-region payload,
then deploy live mode and run once. Check that numeric zero is handled correctly,
that the dot carries the source observation time, and that a second unchanged run
skips ingestion. Verify failures leave indoor reporting unaffected and dashboards
identify stale outdoor data. Enable the 15-minute schedule only after those checks.

Read/compare/write deduplication is best-effort; concurrent source corrections
are not an atomic transaction. Socket timeouts are not a strict total deadline.
The cloud timeout and current account permissions/secret-feature availability
must be verified by the operator.
