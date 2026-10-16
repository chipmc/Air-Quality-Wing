# Documentation index

Start here when reusing this repository's UbiFunctions development approach.
Paths in these guides are relative to the repository, so clones can live anywhere.

| Guide | Purpose |
| --- | --- |
| [Development environment](DEVELOPMENT_ENVIRONMENT.md) | Tools, local setup, credentials, MCP, and a first offline check |
| [AI development workflow](AI_DEVELOPMENT_WORKFLOW.md) | Task definition, independent review, testing, documentation, and owner deployment |
| [CI/CD pipeline](CI_CD_PIPELINE.md) | Actual GitHub checks, their limits, manual release gates, and rollback |
| [Work orders](workorders/README.md) | Task index, reusable template, validation evidence, and acceptance |
| [Backend task reference](../backend/README.md) | Exact VSCode tasks and CLI workflow |
| [PM2.5 function reference](../backend/singapore-outdoor-pm25/README.md) | Data contract, timestamps, errors, and live acceptance |
| [Hardware reference](HARDWARE_REFERENCE.md) | Authoritative Argon technical details |
| [Webhook integration](WEBHOOK_INTEGRATION.md) | Existing Particle event delivery and secrets |
| [Vibe Coding Challenge](VIBE_CODING_CHALLENGE.md) | Educational challenge and contributor roles |
| [Starter prompts](STARTER_PROMPT.md) | Firmware/challenge prompting examples |

For a new backend task, read the first three guides, create a work order from the
template, then read the affected function's reference. Existing validation records
are dated evidence; check the latest work order and PR for current status.

- [Native reTerminal display](../display/reterminal/README.md): optional read-only
  two-panel display, installation and acceptance.
