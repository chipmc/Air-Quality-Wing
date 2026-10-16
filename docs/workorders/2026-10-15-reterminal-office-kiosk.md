# Work order: Screen-on, office Wi-Fi and startup for the reTerminal

- Date: 15 October 2026; Asia/Singapore
- Status: awaiting owner installation/device validation and independent review
- Branch/base: backend/central-outdoor-pm25 / f8b5215 (abbreviated)
- Candidate: uncommitted additions on existing branch; developer Codex
- Reviewer: not assigned; no independent review performed

## Goal, scope and authorization

Owner asked to keep the display on, preload office Wi-Fi, and launch the native
app on boot. Owner confirmed a shared Wi-Fi password; no password requested in
chat. Existing Buster/X11 and wpa_supplicant setup are the supported target.
No OS replacement, cloud writes, firmware changes or API credential changes.

## Implementation and safeguards

Added opt-in --keep-awake using unprivileged xset. Added setup_reterminal.py with
separate wifi (sudo) and kiosk (unprivileged) actions. Wi-Fi prompts privately,
validates input, derives the WPA2 PSK, creates a private backup and atomically
appends the new network without restarting the active connection. SSID hex
encoding avoids configuration syntax injection. Existing networks/country remain.
Refuses duplicates or NetworkManager-managed systems. A derived PSK is still a
credential; both configuration and backup remain mode 0600.

Kiosk setup creates only a managed current-user XDG desktop entry and launcher;
unrelated custom files are preserved. It requires the app and private runtime
config to exist and xset to be present. The separate raspi-config B4 command
explicitly enables graphical auto-login. The app launches fullscreen with screen
blanking suppressed and uses private error logs. Reboot is a separate owner step.
Desktop startup is not a service and does not restart a crashed app.

## Validation evidence

- 19 offline display/setup tests passed on local Python 3.10, including known WPA2
  PSK derivation, existing-network preservation, private backup modes, invalid
  input, duplicate refusal, idempotent user startup and unrelated-file protection.
- Both scripts parse as Python 3.7 grammar. Actual Pi runtime/setup not yet run.
- git diff --check passed. CI update is local; remote checks not run.
- Target screen-on duration, reboot/autologin, office association, live data,
  independent review and owner final acceptance remain pending.

## Owner acceptance and rollback

Copy scripts from the Mac, add office network privately over existing SSH, check
live access, install kiosk launcher, enable desktop auto-login, then reboot at
home. Verify app launches without SSH and screen remains on for 15 minutes.
Verify office connection/data after moving; new IP is expected. If unavailable,
keep home network intact and use it for recovery. Remove the managed desktop
entry for startup rollback; B3 restores desktop password login. Restore session
screen saver/DPMS after exiting the app as documented. Remove only the office
network block, preserving later edits; old backups must not overwrite new work.
No device action has been executed by the agent; commands are for owner execution.

## Owner validation — 15 October 2026, Singapore time

Owner reported the display started on reboot, initially showed OFFLINE, and
subsequently retrieved readings. A manual read-only --check returned indoor
90 ug/m3 at 22:46 SGT (rising +9 over approximately one hour) and outdoor
207 ug/m3 at 22:00 SGT (falling -10). Owner then confirmed the screen was working
and later confirmed "Display stays on". Startup, authenticated live retrieval,
recovery after the initial offline state, and screen-on behavior are therefore
owner-verified. Exact unattended duration was not supplied. Office Wi-Fi
association and data retrieval after moving remain pending; independent review,
remote CI, commit/push and merge have not been performed for these additions.
