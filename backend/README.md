# UbiFunctions development in VS Code

This repository is the source of truth for function source, public settings,
tests and deployment tooling. The first example is Singapore outdoor PM2.5 for
the existing Argon air quality monitor. Additional functions use the same layout,
toolchain and GitHub review process. No reTerminal is needed.

```text
VS Code → local tests → Git branch/PR → review → explicit Ubidots CLI deployment
                                              → run/logs → owner acceptance
```

## Open and set up

Open **UbiFunctions.code-workspace** from this folder in VS Code. This is a
separate workspace from Particle firmware development, with its own Python
environment and tasks. Accept the Python extension recommendation if needed.

Select **Terminal → Run Task → UbiFunctions: Setup Python tooling**. The task
creates ignored `backend/.venv` and installs `requirements-dev.txt`, pinned to
Ubidots CLI **2.1.2**. It selects Python 3.12 if installed, then 3.13/3.14 as a
fallback. Python 3.12 is recommended for portable installations. CLI 2.1.2 uses
Python 3.12 syntax despite its older-Python metadata; on some Linux systems,
Python 3.14 also needs development headers for its older dependencies. The
function itself runs on **Python 3.11** in Ubidots. Docker is optional.

Next run **UbiFunctions: Check tooling**, **Test function** and
**PM2.5 fixture preview (offline)**. The fixture contains invented data, so those
checks require no account or credentials and do not write to Ubidots. Use **Run
and Debug → Debug PM2.5 fixture preview (offline)** for breakpoints.

## Connect a private account profile

Run **UbiFunctions: Configure account privately** and use profile `aqw-dev`.
Enter the token in the CLI's private prompt, never in a VS Code input box, source,
chat, screenshot, GitHub Actions secret for tests, or committed configuration.
CLI profiles live outside Git under `~/.ubidots_cli`. The browser-login task is
an alternative if your Ubidots installation supports the CLI OAuth application;
it may require a client ID provided by Ubidots. Token-based interactive
configuration is the straightforward fallback.

Run **UbiFunctions: List remote functions** to confirm access. This requests only
IDs/labels/names, not the runtime environment or credentials. The CLI login is a
deployment credential. The function's selected account token is a separate runtime
binding that Ubidots supplies as `args['_auth_token']`.

## First project: indoor + outdoor PM2.5

Indoor measurements continue through the existing Particle → Ubidots webhook.
The owner will change indoor reporting to 15 minutes separately; this PR does
not change firmware or flash a device. The outdoor function runs independently
every 15 minutes after schedule activation and writes only `outdoor_pm25_1h`.
NEA's observation time and one-hour averaging period remain attached to that
reading; matching upload frequency does not make the measurement periods equal.

For the outdoor example:

1. Supply the actual existing device **API label**, separate from its display name
   and `ARGON_UBIDOTS_KEY`. That last name refers to a credential, not a device label.
2. In Ubidots Global Properties, create a text **Secret** labelled
   `DATAGOVSG_API_KEY`. Enter the Singapore API key privately, with Functions scope.
   Bind it in the new function's environment after the first preview deployment.
   Both Functions and Global Properties are available in the owner's account.
3. Run **Prepare PM2.5 preview (local only)** with profile `aqw-dev`. The remote
   label will be `singapore-outdoor-pm25-aqw-dev`; preparation makes no API calls.
4. Run **Deploy PM2.5 preview**. This reruns tests, rebuilds the upload from source,
   and invokes the CLI. Confirm the intended account/function at its prompt.
   The initial deployment has HTTP and scheduling disabled and uses preview mode.
5. In the function's Ubidots settings, select the account token and bind the
   `DATAGOVSG_API_KEY` secret. Do not copy either credential into code or a manifest.
6. Run **Run selected remote function** and inspect the preview result/logs.
   Confirm central-region data and source timestamps. Error dictionaries must be
   treated as failures even if the invocation itself returns HTTP 200.
7. After review, choose **Deploy PM2.5 live, schedule OFF**. Run it once, inspect
   the new dot on the correct existing device, verify an unchanged second run is
   skipped and confirm indoor measurements still arrive.
8. Choose **Deploy PM2.5 live, schedule ON** only after those checks. Inspect the
   live settings after pushes to confirm the account-token and secret bindings
   remain present. A 15-minute cron is configured, not an every-minute template.

Use the same chosen profile consistently. A different profile deliberately
produces a distinct remote label and private deployment binding. For a production
copy use a separately configured profile such as `aqw-prod`; repeating preparation
for `aqw-dev` never reads or replaces the `aqw-prod` binding. Existing unsuffixed
manual deployments are not silently adopted by this workflow. Profiles isolate
CLI credentials and remote function bindings; they do not isolate device data.
Choose a separate test device label for live tests that must not affect the main
monitor. Disable a development function's schedule before activating its
production replacement, so both copies do not keep writing to the same variable.

See [the PM2.5 reference](singapore-outdoor-pm25/README.md) for timestamps,
validity checks, duplicate handling, limitations and rollback details.

## What goes into Git

| Commit and review | Keep private / ignored |
| --- | --- |
| function/main.py, public config.json, project.json | Account tokens and Singapore API key |
| Tests and synthetic fixtures | CLI profiles and .env files |
| Shared VS Code workspace, tools and pinned requirements | .venv/, .deploy/, generated .manifest.yaml |
| Deployment/acceptance notes without credentials | Downloaded remote manifests containing token bindings |

`project.json` lists the upload files explicitly. The shared preparation tool
rejects hidden/key files, files outside `function/`, and unexpected files in a
staging folder. Git ignore rules alone do not control what the Ubidots CLI zips.
Each push rebuilds staging from source after tests, preserving private remote
identity and account-token bindings. Do not put secret values in public config.

GitHub Actions runs offline tests and CLI packaging checks without an Ubidots
login. Pushing a Git commit or merging a PR does **not** deploy a function.
Deployment is an explicit VS Code/CLI step following review. Record the Git commit,
profile, remote function label, mode, schedule and acceptance results for each
release, without credentials. Restore the prior reviewed Git revision and deploy
it explicitly for rollback; disable the schedule first if appropriate.

## Create the next function

Run **UbiFunctions: Create new function**, supplying a lowercase name such as
`my-next-function`. This creates only local source, public configuration, tests
and project metadata; it does not create a remote function or install a service.
The starter is intentionally inert and does not echo incoming credentials.

Edit `function/main.py` and add meaningful behavior/failure tests in `tests/`.
`project.json` controls the cloud runtime, upload allowlist, HTTP availability
and cron. Initially HTTP/scheduling are off. Use the selected-function test,
preview preparation, deployment, run and log tasks with the new project name.
For advanced settings, activate `backend/.venv` and use:

```sh
python tools/workflow.py test --project my-next-function
python tools/workflow.py prepare --project my-next-function --profile aqw-dev
python tools/workflow.py push --project my-next-function --profile aqw-dev
python tools/workflow.py run --project my-next-function --profile aqw-dev
python tools/workflow.py logs --project my-next-function --profile aqw-dev
```

This starter targets Python UbiFunctions. Follow the supported CLI runtime/model
when adding Node.js or other project types; do not assume the Python template can
run them unchanged.

Use a descriptive Git branch and PR for each change. Ask a separate reviewer
session to check the actual source/diff and evidence before owner acceptance.
See [CONTRIBUTING.md](../CONTRIBUTING.md). Independent review and live deployment
must be recorded honestly rather than inferred from a passing test run.

## Validation status

See [VALIDATION.md](VALIDATION.md) and the latest PR checks for evidence. Local
setup, 36 tests, scaffold execution and command parsing have been checked. No
Ubidots account has been configured in this workspace and no live function has
been deployed by this update.

## References

- [Ubidots CLI source and authentication/development workflow](https://github.com/ubidots/ubidots-cli)
- [CLI UbiFunctions guide](https://dev.ubidots.com/sdks/cli/ubifunctions)
- [Account token](https://dev.ubidots.com/ubifunctions/advanced/account-token)
- [Secret Global Properties](https://help.ubidots.com/en/articles/9265555-ubifunctions-using-global-properties)
