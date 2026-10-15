# Shared workflow validation — 15 October 2026

The reusable VS Code workflow extends the existing outdoor PM2.5 backend on draft
PR #2. Firmware, sensor drivers, host firmware tests and the existing indoor
Particle webhook are unchanged. The owner will change indoor reporting cadence
separately.

Verified locally:

- The setup task created ignored `backend/.venv`, installed Ubidots CLI 2.1.2,
  and passed the tooling diagnostic on Python 3.14.6/macOS.
- All **28 PM2.5 behavior/packaging tests** passed with the installed CLI.
- All **8 shared workflow tests** passed, including remote-command parsing against
  the real CLI without logging in, profile binding isolation, refreshed source on
  push, private-file/symlink rejection, and a new function's offline contract.
- The scaffold's two generated contract tests passed in a separate process.
- Shared behavior tests passed on Python 3.11; CLI-dependent tests are skipped on
  that interpreter because CLI 2.1.2 uses Python 3.12 syntax.
- All **16 VS Code tasks** reference existing scripts, the workspace parses as
  JSON, YAML/JSON configuration parses, relative documentation links resolve,
  and diff whitespace checks pass. Python/debugpy extensions are already present.
- A private `aqw-dev` preview project was generated with an invented device label,
  remote label `singapore-outdoor-pm25-aqw-dev`, HTTP disabled and schedule off.
  No function or data was created remotely.

The CLI's README example `functions run --logs` is not supported by the installed
2.1.2 command parser. This workflow calls `functions run` and then `functions logs`
separately. Its interactive `config` command also asks for the profile itself;
passing `--profile` does not prefill that prompt in interactive mode. The task
prints the intended profile name before opening the CLI's masked token prompt.

Not yet verified:

- A logged-in Ubidots profile and account permission to create/update functions.
- Secure Global Property and selected account-token binding on a live function.
- Source-key authenticated NEA retrieval, live Ubidots writes, remote run/logs,
  schedule behavior and preservation of bindings across code updates.
- A separate independent LLM review session and owner live acceptance.

The owner has confirmed that Functions and Global Properties are available.
Secrets should be entered privately using those platform facilities. Local
GitHub CI is credential-free and does not deploy; the latest PR checks are the
source for remote test/build status.
