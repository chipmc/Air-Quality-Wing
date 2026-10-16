# CI/CD pipeline

## Current model

This repository automates integration checks and packaging validation. Deployment
is an explicit, owner-approved VSCode/CLI operation. There is no automatic cloud
deployment on merge, and GitHub Actions does not flash hardware.

```text
Work order → branch + local checks → PR + GitHub Actions
           → independent review + resolved findings → owner release approval
           → CLI preview → live run with schedule off → verify → activate schedule
           → record acceptance and owner merge decision
```

The owner can merge an approved candidate before deployment where appropriate;
record the exact source revision deployed in either order. A successful workflow
run proves only its listed checks, not cloud credentials, sensor correctness,
cloud-runtime behavior or successful ingestion.

## Actual GitHub workflows

| Workflow | Trigger | Jobs and scope |
| --- | --- | --- |
| [Outdoor PM2.5 backend](../.github/workflows/backend.yaml) | PRs to `main` and pushes to `main` affecting `backend/**` or that workflow; manual dispatch | Python 3.11/3.14 offline shared/function tests and synthetic fixture preview; Python 3.12 installs pinned CLI and reruns tests including packaging checks |
| [Particle Compile](../.github/workflows/main.yaml) | All PRs to `main`, pushes to `main`, manual dispatch | Three host regression checks; Argon / Device OS 6.4.1 compile; firmware artifact upload |

Backend CI uses no login, live API calls or deployment secrets. CLI-dependent
checks can skip when the CLI is absent in the offline jobs; the packaging job
installs it to exercise those checks. Workflow permissions are `contents: read`.
Firmware compilation uses the vendored libraries and requires no Particle token.

Documentation-only PRs do not trigger backend CI under the current path filters.
The Particle workflow still runs. Documentation links and whitespace are checked
locally; there is currently no automated Markdown-link job. Branch protection and
required status checks are account settings, not guaranteed by these YAML files.
Check actual PR results before reporting any remote check as passed.

## Local release checks

From the repository root, after setting up the backend environment:

```sh
backend/.venv/bin/python -m unittest discover -s backend/tests -v
backend/.venv/bin/python -m unittest discover -s backend/singapore-outdoor-pm25/tests -v
backend/.venv/bin/python backend/singapore-outdoor-pm25/tools/preview.py --fixture backend/singapore-outdoor-pm25/tests/fixtures/pm25.json --at 2026-10-12T16:20:00+08:00
git diff --check
```

On Windows use `.venv/Scripts/python.exe`. The fixture is invented data and its
explicit timestamp prevents normal freshness checks treating it as current data.
For another function, run its own tests too. The current CI explicitly names the
PM2.5 tests: adding a new scaffold does not automatically add its suite to CI.
Update the workflow's test commands and, if needed, filters in that task.
For firmware changes use the commands in the [hardware reference](HARDWARE_REFERENCE.md).

## Manual delivery gates

1. **Reviewable source:** scoped work order, public files only, relevant local
   checks, passing applicable PR checks, and independent review findings resolved.
2. **Preview:** choose private profile and intended remote label; preview mode,
   HTTP off and schedule off initially. The push task reruns selected-function
   tests and rebuilds staging, but does not replace shared tests or independent review.
3. **Runtime configuration:** privately select the function account token and bind
   required secret Global Properties. Inspect bindings after every deployment.
4. **Live smoke test:** schedule remains off; run once and check output/logs plus
   the actual Ubidots dot. Verify source timestamp and a repeated unchanged read.
5. **Activation:** enable the 15-minute schedule for the PM2.5 example only after
   owner acceptance of live checks. Observe scheduled runs and source freshness.
6. **Release record:** capture source SHA, profile, label, mode/schedule, sanitized
   evidence and acceptance in the work order. Approval, deployment, and merge are
   separate events; record each honestly.

The upload allowlist is defined by `project.json`; `.deploy`, `.manifest.yaml`,
`.venv`, private profiles and `.env` files are not release source. Keep credentials
out of source and Actions. The CLI's overwrite prompt is an additional destination
check, not a substitute for owner approval or a release record.

## Rollback and failed releases

Disable the affected schedule first when continuing writes could be wrong. Keep
indoor ingestion working. Restore the previous reviewed source in a rollback
branch/commit or separate checkout, use the same intended profile/remote binding,
and deploy it explicitly. Recheck token/secret bindings, mode and schedule before
reactivation. Record the prior and rollback revisions and verify the result.
Code rollback does not remove or repair already stored bad data; plan any data
correction separately with the owner.

Unverified account access, key bindings, live output, or scheduling keeps a task
awaiting validation. Never infer deployment from a green PR or a merge.

## Optional native display CI

[Native PM2.5 display](../.github/workflows/display.yaml) triggers for PRs/pushes
to main affecting display/** or its workflow, plus manual dispatch. It runs
offline display tests on Python 3.11/3.14 and checks the app parses as Python 3.7.
It does not run a Tk GUI, test an actual Python 3.7 runtime, configure credentials
or deploy to a reTerminal. On-device acceptance remains a separate owner step.
