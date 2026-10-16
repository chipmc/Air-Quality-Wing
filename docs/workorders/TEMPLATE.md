# Work order: <short task title>

- ID / date: <YYYY-MM-DD-short-task; timezone if needed>
- Status: proposed
- Owner: <human owner>
- Issue / PR: <links or not created>
- Branch / base commit: <branch; full SHA>
- Candidate source revision: <SHA; note uncommitted changes if present>
- Developer: <tool/model/session>
- Independent reviewer: <tool/model/session or not assigned>

## Goal and acceptance criteria

Describe the trigger, expected result, inputs/outputs, and observable acceptance
criteria. Link the authoritative function/hardware references.

## Scope and exclusions

List affected components, compatibility promises and explicit non-goals.
Identify any live writes, schedule activation, webhook changes or hardware work.

## Plan and validation strategy

Describe implementation, meaningful normal/failure checks, review handoff,
documentation updates, deployment gates, and rollback. Record existing owner
authorization and any missing decision without copying credentials.

## Implementation and documentation

Summarize the final change, decisions and affected files. Update this section when
scope changes; do not leave the record describing an abandoned implementation.

## Validation evidence

| Date / environment / source revision | Command or observation | Result | Evidence / limits |
| --- | --- | --- | --- |
| <date; interpreter/OS; SHA> | <exact command> | Not run | <output summary, CI link, skip/failure reason> |

Separate local tests, CI, cloud runtime, real data and hardware. A passing build
or HTTP status is not proof of end-to-end behavior. Record warnings and skipped
checks. After edits, identify the new revision and repeat affected checks.

## Independent review

- Reviewed revision and diff base: <SHAs>
- Reviewer identity/session: <identifier or not run>
- Findings with file locations and resolution: <list; or none with evidence>
- Follow-up review after changes: <result or pending>

## Deployment and rollback

- Source SHA / private profile name / remote label: <identifiers only>
- Mode / HTTP / schedule before and after: <values>
- Owner release authorization: <scope/date or pending>
- Runtime token and secret bindings: <verified/pending; never values>
- Preview, live single run, duplicate and scheduled-run results: <evidence>
- Rollback revision and procedure / data correction limits: <details>
- For documentation-only work: mark deployment not applicable.

## Owner acceptance and handoff

- Acceptance and merge decisions: <separate dates/revisions or pending>
- Remaining work / limitations: <specific actions>
- Reusable lessons and updated reference links: <links>
