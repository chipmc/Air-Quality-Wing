# Work order: Native two-panel reTerminal PM2.5 display

- Date: 15 October 2026; Asia/Singapore
- Status: in progress; awaiting owner device trial and independent review
- Branch/base: backend/central-outdoor-pm25 / f8b5215 (abbreviated)
- Candidate: uncommitted local source and documentation additions
- Owner: Chip McClelland; developer: Codex; independent reviewer: not assigned

## Goal and scope

Owner requested an easier-to-read display after the public Ubidots chart failed
on Chromium 92/Buster. Both indoor and outdoor PM2.5 should be equally large,
colour coded and have one-hour trend arrows. Use Tk already installed (owner
verified 8.6) on the original reTerminal; no OS reflash, firmware changes, cloud
writes or dashboard changes. Source, instructions and tests belong in Git.

## Implementation

Added display/reterminal/air_quality_display.py, README and offline tests. Private
masked configuration stays on the Pi outside Git. GET-only Ubidots access uses
header authentication, bounded responses, timeouts and no redirects. Two panels
show latest values, source timestamps in SGT, ~one-hour comparison and stale/offline
status. Indoor indicative numeric ranges are distinguished from outdoor NEA bands.
Added a separate path-filtered display CI workflow; no deployment in CI.

## Validation

Local validation on the uncommitted candidate:

- `python3 -m unittest discover -s display/reterminal/tests -v`: 13 passed on macOS Python 3.10.
- `backend/.venv/bin/python -m unittest discover -s display/reterminal/tests -q`: 13 passed on Python 3.14.6.
- `ast.parse(..., feature_version=(3,7))`: Python 3.7 grammar passed; not a target runtime test.
- Relative file link check across the six relevant documents: 44 resolved.
- `git diff --check`: passed. Remote CI not run; additions remain local.

The first test run exposed an HTTPError fixture without a body stream on Python
3.10; using a realistic BytesIO response fixed the fixture. No GUI validation was
performed locally. Owner confirmed Python Tk
8.6, SSH user pi, 192.168.1.43, 3.7 GiB RAM. Chromium stays alive but the chart
reports a widget error; the same public dashboard renders in a current browser.
No claim that the native display has rendered on the Pi or read live data yet.

## Acceptance and rollback

Owner should copy the script via SCP, run --demo with DISPLAY=:0, inspect equal
panels/fonts/arrows and exit, then privately configure the Ubidots token. Run
--check and compare with MCP, then run the live GUI. Check 40-minute indoor and
90-minute outdoor staleness, missing history, read failure and SGT timestamps.
No service/autostart configured; Escape stops the app and leaves system unchanged.
Independent review, target Python version/runtime, live access, on-device GUI,
physical readability, owner acceptance, commit/push/CI and merge remain pending.

## Owner device trial

Owner reported the demo display was successful ("This is awesome") and then
reported satisfaction after receiving live setup instructions. Demo rendering
and readability are owner-reported success. Exact live --check output and target
Python version have not been recorded. Subsequent screen-on/office Wi-Fi/startup
work is tracked in the separate office-kiosk work order.
