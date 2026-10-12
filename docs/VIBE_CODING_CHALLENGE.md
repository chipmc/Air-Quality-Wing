# Vibe Coding Challenge

Use an AI assistant to improve a real Argon air quality monitor and learn how to
check its work. You can participate without owning hardware: test locally, submit
a PR, and let the owner approve and flash the device.

## Choose a focused experiment

Read the [technical reference](HARDWARE_REFERENCE.md) and
[event/webhook contract](WEBHOOK_INTEGRATION.md). Choose one measurable goal:
clearer diagnostics, better failure recovery that respects shared D5 control,
more useful tests, or a documented backend visualization. Alternative firmware
is welcome when its goal justifies replacement and its compatibility is reviewed.
A wholesale rewrite is not required to participate.

Define success before coding. For example: “A sensor communication failure
produces null values, never stale numeric values, while reporting continues.”
Explain the tradeoff and which host or hardware observations would establish it.
Use the [starter prompts](STARTER_PROMPT.md) with an explicit scope.

## Separate duties to improve quality

| Role | Responsibilities | Evidence |
| --- | --- | --- |
| LLM developer | Inspect sources, implement the agreed scope, run checks, explain changes and uncertainties | Diff, test/build output and hardware checklist |
| Independent LLM reviewer | In a separate session, inspect the actual diff against the technical reference, schematic, library fixes and tests; challenge assumptions | Findings with file/line, impact, reproduction and unresolved questions |
| Human owner | Resolve requirements, approve hardware actions, flash the exact reviewed revision, test physical sensors and cloud path, decide when to merge | Hardware log and acceptance decision |

Prefer a different model/tool for review when available, but independence depends
on the reviewer's separate context and evidence, not its brand. Start it with the
reference, code and diff, rather than the developer's assurance that everything
works. The developer responds to findings; the reviewer rechecks corrections.
Disagreement is resolved with source, datasheets or a concrete test, not by
counting model votes. AI review cannot establish electrical behavior or sensor
accuracy. Identify both tools/models and their roles in your PR.

## Suggested workflow

1. Open an issue for a large change; for a small improvement, state the objective
   in your PR. Fork the repository and create a descriptive branch.
2. Give the developer assistant the technical reference and a scoped prompt.
   Preserve the Argon/6.4.1 target, event schema and vendored library fixes unless
   an explicitly proposed contract change requires otherwise.
3. Review its diff yourself. Run all three host checks and attempt an Argon build.
   Record the exact commit, tool versions, flags, results and warnings. If you
   cannot build, say so; do not turn host success into a firmware-build claim.
4. Ask the independent reviewer to inspect the code and evidence. Fix findings
   and have that reviewer recheck the final revision.
5. Open a PR using [CONTRIBUTING.md](../CONTRIBUTING.md), with remaining unknowns
   and an owner hardware test plan. PR checks build/test; they do not flash.
6. The owner approves and flashes the reviewed revision, tests on Argon and
   verifies Ubidots, records results, and decides whether to merge. Keep the
   known-good binary available for rollback. New changes need renewed review
   of the changed revision before hardware acceptance.

## Optional backend challenge

Build a dashboard, time-series store, stale-data view, or another integration
using the same `air_quality` event. Work with numeric and mixed-null sample JSON
first; show units, explain eCO₂, and visibly distinguish old data from fresh data.
Keep service credentials on the server, never in browser code or public artifacts.

[Open a GitHub issue](https://github.com/chipmc/Air-Quality-Wing/issues/new) containing:

- Purpose, backend/service, and a screenshot or demo using sample data.
- HTTPS ingestion endpoint and expected body (raw JSON or a proposed mapping).
- Authentication mechanism and secret name only, never a credential value.
- Null/stale handling, numeric zero behavior, timestamps, retries/duplicate policy,
  expected cadence, retention and any costs/quotas.
- A reproducible test plan and requested webhook setup.

The owner can review the proposal and add a webhook to your chosen backend.
Agree a secure private channel for credentials after the proposal is accepted.
Only the owner changes the live integration. Start from the existing event
contract; most backend projects need no firmware change. A proposed endpoint or
a sample-data demo is not evidence of a live sensor integration.
