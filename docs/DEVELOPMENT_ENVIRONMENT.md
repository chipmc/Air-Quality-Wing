# UbiFunctions development environment

## Tools and responsibilities

| Tool | Role | Boundary |
| --- | --- | --- |
| VSCode | Edit, run tasks, debug fixture data, inspect Git changes | Does not itself host the cloud function |
| Python and isolated `.venv` | Run local checks and pinned deployment tooling | Deployment interpreter differs from cloud runtime |
| Codex | Example primary developer; implementation, tests, documentation | Must report evidence and unresolved work |
| Claude | Example independent reviewer in a separate session | Inspect the actual revision and requirements |
| GitHub Copilot | Optional completion, explanation, or a designated review role | Suggestions still require inspection and tests |
| Git / GitHub | Source history, branches, PR review, CI results | A push or merge does not deploy |
| Ubidots CLI | Explicit function upload, invocation, and logs | Requires its own private account profile |
| Ubidots MCP | Inspect devices, variables, and live time-series data | Documented tools do not manage UbiFunctions or Global Properties |
| UbiFunctions | Execute deployed code in Ubidots | Runtime secrets and schedule must be verified separately |
| Particle Workbench | Argon firmware development | Only needed for firmware changes; owner flashes hardware |

The tools can exchange roles. Independence comes from a separate review session,
requirements, and inspection of the actual diff, not simply using several brands.

## Repository and workspace

Clone `https://github.com/chipmc/Air-Quality-Wing.git`, or use your fork for
contributions. Keep one working clone at your chosen permanent location. The
owner's current clone is `~/Documents/Maker/Ubidots/Air-Quality-Wing`.
It already has Git history and `origin`; do not initialize another repository
inside `backend/`.

Open `backend/UbiFunctions.code-workspace` using VSCode's **File → Open Workspace
from File**. The workspace intentionally displays `backend/`, while Git uses the
parent repository. Firmware lives elsewhere in the same repository.

Install Python 3.12 for the deployment tools and the VSCode Python/debugpy
extensions. Install/sign in to whichever AI extensions you use. The installed
Codex extension exposes **Open Codex Sidebar** through the command palette.
The desktop chat and an IDE session can have different conversation context;
give a new session the work-order path and relevant documents.

## Offline setup and first checks

Use **Terminal → Run Task** in the dedicated workspace:

1. **UbiFunctions: Setup Python tooling** creates ignored `backend/.venv` and
   installs `backend/requirements-dev.txt` (Ubidots CLI 2.1.2).
2. **UbiFunctions: Check tooling** confirms local Python/CLI versions. It does not
   authenticate or prove cloud access.
3. **UbiFunctions: Test function** checks the chosen function.
4. **UbiFunctions: PM2.5 fixture preview (offline)** uses invented data without
   network access or writes. The matching debug configuration supports breakpoints.

The shared setup prefers Python 3.12, then 3.13/3.14. CLI 2.1.2 requires Python
3.12+ in practice; some Python 3.14 Linux installs need dependency build headers.
The PM2.5 cloud runtime is independently set to `python3.11:lite` in
`backend/singapore-outdoor-pm25/project.json`. Run both shared workflow and
function tests before release; see [CI/CD](CI_CD_PIPELINE.md).

Virtual environments contain absolute paths. After relocating a clone, recreate
`.venv` through setup, or repair and verify its local entry points. Relative
workspace paths are portable; a moved environment is not automatically portable.

## Separate credential uses

| Credential | Configure privately | Used for |
| --- | --- | --- |
| Ubidots MCP token | Client authentication environment/settings | Inspecting account data through MCP |
| Ubidots CLI token | **Configure account privately**, profile `aqw-dev`; local `~/.ubidots_cli` | Deploying and operating functions |
| Function account token | Select in Ubidots function settings; injected as `args['_auth_token']` | Runtime Ubidots API access |
| Singapore API key | Secret Global Property `datagovsg_api_key`, with Functions scope, bound to the function environment | Runtime data.gov.sg retrieval |

MCP connectivity does not authenticate the CLI. A device API label is a public
routing identifier, not any of these credentials. `ARGON_UBIDOTS_KEY` refers to a
credential, not a device label. Keep all credential values out of Git, work orders,
chat, screenshots, fixtures, task inputs, and logs. Ignore rules do not replace
upload allowlists or credential review.

For CLI setup, run **Configure account privately** and enter `aqw-dev` when the
CLI asks for the profile; its token prompt is masked. Then use **List remote
functions**. Browser login is an alternative only where the account supports it.

## Optional MCP connection

Use Streamable HTTP URL `https://mcp.ubidots.com/mcp/readonly` and bearer-token
environment-variable name `UBIDOTS_MCP_TOKEN`. The field takes the variable name,
not its value; leave extra authorization headers empty when using this option.
The client must inherit the variable when it starts. macOS desktop apps may not
inherit terminal shell exports; after privately setting their login environment,
fully quit and reopen the desktop app and VSCode. Login-session environment values
may need re-entry after logout/restart. This is not an encrypted secret vault.

Test with a device lookup and latest readings. This project verified a read-only
connection on 15 October 2026; that does not imply another clone/client is connected.
Use MCP for observation and explicit CLI tasks for deployment. Never assume an MCP
connection grants function-management tools; inspect available tools first.

See the [backend guide](../backend/README.md) for deployment steps and
[AI workflow](AI_DEVELOPMENT_WORKFLOW.md) for review and acceptance.

The Singapore secret is read by its actual Global Property label,
`datagovsg_api_key`, not the uppercase display name. Uppercase
`DATAGOVSG_API_KEY` remains supported as a local/legacy environment fallback.
