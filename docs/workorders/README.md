# Work orders

Keep one Markdown record per scoped task, including its validation and acceptance.
Copy [TEMPLATE.md](TEMPLATE.md) to `YYYY-MM-DD-short-task.md`; use a suffix if two
tasks share a name/date. Link the issue/PR and update this index. The work order
lives on the same branch as the change so reviewers can assess both together.

Suggested states: proposed → in progress → awaiting review → awaiting live
validation → accepted. Use blocked/cancelled with a reason when appropriate.
Documentation tasks can use local validation rather than cloud deployment, but
must still distinguish pending independent review and owner acceptance.

| Work order | Scope |
| --- | --- |
| [2026-10-15 reusable development documentation](2026-10-15-development-documentation.md) | Environment, AI workflow, CI/CD and work-order conventions |

Record exact commands, results, tested source revisions and CI links. Do not copy
tokens, full incoming arguments, private manifests or secret-bearing logs. State
skips, failures and not-run checks explicitly. Preserve historical results; append
new dated evidence when a result changes. A model should discover this index via
[docs/README.md](../README.md) before starting another task.

- [Singapore secret label fix](2026-10-15-global-property-label.md): lowercase runtime label, compatibility fallback and preview validation.

- [Native reTerminal display](2026-10-15-reterminal-display.md): two-panel trial,
  read-only access, trends and target validation.

- [reTerminal office kiosk](2026-10-15-reterminal-office-kiosk.md): screen-on,
  private additional Wi-Fi profile, and desktop startup.

- [reTerminal OS migration](2026-10-16-reterminal-os-migration.md): private backup,
  64-bit Bookworm flashing prerequisites and restore/acceptance plan.
