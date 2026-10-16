# Work order: Accept the actual Singapore secret property label

- Date: 2026-10-15; Asia/Singapore
- Status: awaiting live validation and independent review
- Branch: backend/central-outdoor-pm25
- Candidate: local changes on base f8b5215; not yet committed
- Developer: Codex; independent review not run

## Scope and evidence

Owner reported two preview invocations returning configure_datagovsg_api_key.
Screenshot confirms display name DATAGOVSG_API_KEY and actual property label
`datagovsg_api_key`. Existing code read only the uppercase environment variable.
Accept the lowercase label first and retain the uppercase fallback. Correct setup
guidance and test label selection, precedence, fallback, and missing values.
No secrets, firmware, live configuration or schedules changed by this fix.

## Validation

Local checks passed on the uncommitted candidate using backend/.venv/bin/python:

- `-m unittest discover -s backend/singapore-outdoor-pm25/tests -q`: 29 passed.
- `-m unittest discover -s backend/tests -q`: 8 passed, including scaffold contract subprocess.
- `git diff --check`: passed.

Live preview rerun and remote CI for this candidate: not run.
Successful deployment reported by owner before the fix did not prove API access.

## Deployment and acceptance

Owner should push preview with schedule off, verify the lowercase property remains
selected in the function settings, and rerun preview. Do not enable live writes.
CLI pushes must preserve existing secret and account-token bindings; check them
after pushing. Owner acceptance and merge remain pending. Rollback is restoring
the prior source and redeploying preview; no data correction is needed for this
configuration failure because it occurs before API access or writes.

## Follow-up: source HTTP diagnostic

Owner reran the updated preview and received `source_http_error` (1051 ms).
This establishes that the configured key passed local validation; it does not
establish the API accepted it. Add a numeric `http_status` to the sanitized error
response, retaining the existing reason. No response body, credentials or request
headers are exposed. Test 401/403/429/503 propagation and rejection of invalid
status metadata. Remote preview remains pending; no live writes are authorized.

Follow-up local validation: 30 function tests and 8 workflow tests passed with
backend/.venv/bin/python; git diff --check passed. These results cover the
uncommitted diagnostic changes, not a remote deployment.

## Follow-up: Python client identification

Owner screenshot confirms an active Development key expiring 14 October 2028.
Key-bearing local Python request also returned 403. A controlled local probe of
the same public endpoint without credentials returned: default Python User-Agent
403; Air-Quality-Wing/1.0 200; curl/8.7.1 200. This reproduces a client-dependent
access difference without involving the owner's key; it does not establish the
server's filtering policy or validate the key itself.

Add an explicit truthful User-Agent Air-Quality-Wing/1.0 to the source request,
retaining the configured API key and existing error handling. Add a regression
check for the client identifier and retained key header. Owner must redeploy
preview and rerun to validate the authenticated cloud request. No automatic
fallback to unauthenticated production ingestion and no live writes.

## Owner preview success and live ingestion — 15 October 2026

Owner reported successful authenticated preview: central PM2.5 205 ug/m3,
observation 17:00 SGT, updated 17:15:33 SGT. Subsequent live invocation CLI
returned ReadTimeout at 09:29:43 UTC; completion was initially unknown.
Read-only MCP verification then found outdoor_pm25_1h = 205 on device
`e00fce6889936b9d0ffd8930`, timestamp 1792054800000, created_at 1792056585322,
with source/region/1h averaging/source-update context preserved. Seven indoor
variables were also present, last updated around the live ingestion time.
Thus live data delivery is verified despite the CLI timeout. The exact deployed
source SHA remains unrecorded because source changes are uncommitted.

Latest local source checks: 31 function tests and 8 workflow tests passed;
whitespace checks passed after the User-Agent change. Independent review,
activation-log inspection, unchanged-run deduplication, scheduled execution,
owner final acceptance and merge remain pending. Keep schedule disabled until
remaining live acceptance checks are complete. Next operation: read logs, not an
unexamined repeat write. CLI timeout does not establish failed execution.
