# Work order: Reusable UbiFunctions development documentation

- ID / date: 2026-10-15-development-documentation; Asia/Singapore
- Status: awaiting review
- Owner: Chip McClelland
- Issue / PR: existing backend [PR #2](https://github.com/chipmc/Air-Quality-Wing/pull/2); these documentation additions are local until pushed
- Branch / base commit: `backend/central-outdoor-pm25`; `f8b5215` (abbreviated base)
- Candidate source revision: uncommitted documentation additions on the base above
- Developer: Codex desktop session
- Independent reviewer: not assigned; no independent review performed

## Goal and acceptance criteria

Make the VSCode/GitHub/UbiFunctions approach discoverable and reusable. Provide an
environment guide, AI development workflow, actual CI/CD guide, work-order folder,
template and validation record. Link these from the repository entry points.
Describe current tooling accurately and distinguish automatic checks from explicit
deployment. Keep secrets out of all records.

## Scope and exclusions

Documentation and navigation only. Do not change firmware, backend behavior,
GitHub workflows, credentials, live cloud configuration or schedules. The owner
continues to handle indoor reporting cadence. No hardware flashing.

## Implementation and documentation

Added a documentation index and three reusable guides, plus a work-order index,
template and this task record. Linked them from the root README, backend guide,
and contribution instructions. The pipeline guide names the actual triggers,
Python matrix, packaging checks, Argon build and manual delivery gates, including
path-filter and future-function test-discovery limitations.

## Validation evidence

| Date / environment / source revision | Command or observation | Result | Evidence / limits |
| --- | --- | --- | --- |
| 2026-10-15; local clone; base f8b5215 plus documentation edits | Read `.github/workflows/backend.yaml`, `main.yaml`, workspace, shared tools and backend guides | Passed | Guides derived from checked-in implementation; no live behavior inferred |
| 2026-10-15; same candidate | Relative Markdown link scan across changed files | Passed | 57 relative file links resolve across 10 documents; remote URLs and heading anchors not checked |
| 2026-10-15; same candidate | `git diff --check` | Passed | No whitespace errors in tracked documentation edits |
| 2026-10-15; same candidate | Firmware/backend execution tests | Not run | Documentation-only change; executable files unchanged |
| 2026-10-15; same candidate | GitHub Actions for these additions | Not run | Additions not pushed; prior PR runs do not validate this candidate |
| 2026-10-15; same candidate | Cloud deployment / hardware | Not applicable | No function deployment, live writes or flashing in scope |

## Independent review

Not run. Owner may assign Claude or another separate reviewer session to inspect
the docs against the actual tools and workflow YAML. Developer inspection is not
independent review.

## Deployment and rollback

Deployment is not applicable. Revert only these documentation/navigation changes
if needed; do not reset unrelated branch work. No cloud or data rollback required.

## Owner acceptance and handoff

Owner review and merge decision remain pending. Future tasks should copy the
template and append their own revision-specific validation. Existing historical
backend validation files remain dated evidence and are not rewritten as new tests.
