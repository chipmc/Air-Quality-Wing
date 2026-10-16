# Contributing

Small, well-explained improvements are welcome. Start with the
[technical reference](docs/HARDWARE_REFERENCE.md),
[challenge](docs/VIBE_CODING_CHALLENGE.md) and
[starter prompts](docs/STARTER_PROMPT.md). Argon is the only supported target.
For substantial firmware or backend work, open an issue to agree the goal first.

## Fork, branch and pull request

Fork `chipmc/Air-Quality-Wing` on GitHub, clone your fork, and branch from `main`:

```sh
git clone https://github.com/YOUR-USERNAME/Air-Quality-Wing.git
cd Air-Quality-Wing
git switch -c challenge/your-improvement
```

Implement a scoped change. Preserve vendored fixes and event compatibility;
document any intentional changes. Run the three host checks in the technical
reference and attempt an Argon/6.4.1 build. Ask a separate LLM session to review
the diff and respond to its findings. Commit and push to your fork:

```sh
git add <files-you-reviewed>
git commit -m "Describe the change"
git push -u origin challenge/your-improvement
```

Open a PR against this repository's `main`. Include:

- Problem, resulting behavior and scope; mention compatibility changes.
- Developer and independent reviewer tools/models, findings and resolutions.
- Exact tested commit, target/version, flags, commands, results and warnings.
  Mark unavailable checks as **not run** and distinguish host/build/hardware tests.
- Owner hardware and end-to-end cloud test plan, known limitations and rollback.

Do not include account tokens, device credentials or unredacted secret-bearing
logs. Webhook credentials belong in cloud secrets. PR CI builds and runs host
checks without credentials and does not flash. Contributors do not flash the
owner's device, change live integrations, or merge on the owner's behalf.

## Owner acceptance

The owner reviews and approves the exact revision, builds or verifies its Argon
binary, flashes it, and records sensor/boot/error/offline/Particle/Ubidots checks
from the technical reference. The owner decides when to merge after acceptance.
If code changes after review/testing, identify the new revision and repeat
relevant checks. Keep a known-good firmware binary for rollback.

## Backend proposals

Use a GitHub issue and the
[backend proposal checklist](docs/VIBE_CODING_CHALLENGE.md#optional-backend-challenge).
Test sample JSON first. The owner can add a webhook after approving the endpoint,
data mapping and handling of nulls, stale values and credentials.

## Reusable backend development process

For UbiFunctions work, follow the [AI development workflow](docs/AI_DEVELOPMENT_WORKFLOW.md)
and [CI/CD guide](docs/CI_CD_PIPELINE.md). Create a [work order](docs/workorders/README.md)
with scope, review findings, revision-specific validation, deployment evidence and
owner acceptance. Apply firmware checks when firmware is affected; backend-only
work uses the relevant backend checks and cloud acceptance instead.
