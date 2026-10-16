# AI development workflow

Use this process for each UbiFunction change. The human owner remains responsible
for acceptance, deployment authorization, and merge decisions. Firmware changes
also require owner-controlled hardware flashing.

## 1. Capture the task before implementation

Create `docs/workorders/YYYY-MM-DD-short-task.md` from the
[template](workorders/TEMPLATE.md), link the issue/PR, and record the branch and
base commit. Define the behavior, affected function, compatibility requirements,
non-goals, acceptance criteria, test plan, and rollback before editing code.
Use a fork and descriptive branch for external contributions; owner work can use
a branch in the main repository. Never record credentials.

For this project, indoor Particle webhook ingestion remains separate from the
scheduled outdoor function. Leave firmware timing changes to the owner unless
explicitly included in a task.

## 2. Assign developer, independent reviewer, and owner

| Role | Responsibility | Evidence |
| --- | --- | --- |
| Developer assistant | Implement scoped behavior; add meaningful tests; update references/work order | Changed files, exact checks and results, known limits |
| Independent reviewer assistant | In a separate session, read requirements, source, actual diff, tests, and CI | Reviewed revision, findings with file locations, severity, and disposition |
| Human owner | Resolve scope/tradeoffs, approve live actions, inspect acceptance, decide merge | Approved revision, deployment/acceptance and merge decision |

Example: Codex develops; Claude reviews; Copilot helps with small edits. Rotate
these roles as needed. The developer's self-review is useful but does not count
as independent review. Do not assume another agent has reviewed a change or send
it work without the user's authorization to use that session/agent.

## 3. Implement and document together

Read this guide, the environment guide, CI/CD guide, affected function README,
source, and existing tests. For a new Python function use **UbiFunctions: Create
new function**. The scaffold is inert until its behavior is implemented.

Preserve the input/output contract and working firmware unless the task requires
a change. Test normal, missing/null, zero, malformed, stale/future data, upstream
failure, and write/duplicate behavior where relevant. Test outcomes and failure
handling rather than mirroring the implementation. Use synthetic fixtures.

Update public configuration, explicit upload allowlists, and function instructions
as behavior changes. Avoid logging `args` or unredacted remote manifests; injected
credentials can be present. Keep schedules and HTTP endpoints off for initial
previews. Record limitations, not just successes.

## 4. Validate, then request independent review

Run the relevant checks in [CI/CD](CI_CD_PIPELINE.md), inspect the diff, and update
the work order with commands, environment, outcomes and skipped checks. Push the
branch and open/update a PR against `main` so the change is reviewable and CI runs.
Review and CI can iterate before owner acceptance.

Give the reviewer a concrete handoff such as:

> Review work order docs/workorders/<task>.md and the diff from <base SHA> to
> <candidate SHA>. Read the affected function reference and CI/CD guide. Check
> correctness, timestamps, failure behavior, credentials, packaging, test gaps,
> and documentation claims. Report actionable findings with locations and evidence.
> Do not modify or deploy code. State checks you ran and what remains unverified.

Record the reviewer's identity/session/tool and exact reviewed revision. Resolve
each finding or document why the owner accepts it. Changes after review require
review of the affected diff and relevant checks on the new revision.

## 5. Owner-approved preview and live release

Prepare the concrete source, tests, documentation, and preview plan before asking
for any missing approval. Existing explicit authorization can cover subsequent
steps within its scope; do not repeatedly ask for the same approval.

Use the correct private CLI profile and destination API label. Deploy preview
with schedule off, bind runtime credentials privately, run it, and inspect
sanitized output/logs. An invocation returning HTTP 200 can still contain an error
result; inspect application status.

After preview acceptance, deploy live with schedule off and invoke once. Verify
the destination variable, source timestamps, context, duplicate handling, and
unaffected indoor data through MCP or the Ubidots UI. Enable the schedule only
after the live checks pass and the owner authorizes activation. Recheck secret
bindings and live settings after pushes. Profiles separate deployment bindings,
but two profiles can still write to the same device; avoid competing schedules.

## 6. Close with evidence and a reusable handoff

Update the work order with deployed source SHA, profile name, remote label,
mode/schedule, reviewer findings, CI links, acceptance results and rollback.
Record owner acceptance and merge separately; neither is implied by passing CI.
Keep an unfinished task in an honest state such as awaiting review or awaiting
live validation. Mark not-run checks explicitly. Link any reusable lesson back
into the guides or function reference; leave historical evidence dated.
