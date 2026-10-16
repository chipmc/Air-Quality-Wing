# Native reTerminal PM2.5 display

Trial display for the original reTerminal: two equally sized panels for `pm25`
(indoor latest sensor reading) and `outdoor_pm25_1h` (NEA Central one-hour average).
It uses Python 3.7+ and Tk 8.6 with no pip packages or browser. No firmware,
UbiFunction, dashboard settings, timezone, or stored data are changed. The old
Buster system remains old; this trial is not an OS maintenance solution.

## Design and interpretation

Large numbers and arrows appear on a dark fullscreen display. Both observation
times and the clock are explicitly Singapore time (UTC+8), independent of account
and OS timezone. Escape exits; F11 toggles fullscreen. The layout targets the
original reTerminal's landscape 1280×720 display. Physical readability and GUI
operation on the target are still awaiting owner validation.

Outdoor categories use [NEA's one-hour bands](https://www.haze.gov.sg/): Normal
0–55, Elevated >55–150, High >150–250, Very high >250 µg/m³. The chosen green,
blue, amber and red palette is a display choice. Indoor colours use the same
numeric ranges as an **indicative scale only**, labelled as ranges, not official
NEA categories, an indoor health assessment, PSI, or AQI. Indoor spot readings
and outdoor one-hour averages are different measurement periods.

Arrows compare the current observation with the latest point at/before one hour
before it, allowing up to 15 minutes of additional history gap. A change of at
most 2 µg/m³ shows steady. Rising/falling means concentration, not a health claim.
Missing history shows no arrow. This is a comparison with ~one hour ago, not a
regression or forecast. Source revisions keep their source observation timestamp.

Indoor values become stale after 40 minutes (planned 15-minute indoor reports);
outdoor after 90 minutes. Stale data and read failures show grey numbers and no
trend, never a green zero. Read failures keep the prior value labelled OFFLINE.
The display refreshes its age each second and polls every five minutes. Each
successful poll retrieves at most four dots (latest and hour-prior baseline for
each variable) using only authenticated GET requests. No data is published.
Baseline lookup failures show the current value with trend unavailable.

## Trial installation

Run these in a **new Mac terminal**, not inside an existing Pi SSH session:

```sh
cd /Users/chipmc/Documents/Maker/Ubidots/Air-Quality-Wing
ssh pi@192.168.1.43 'mkdir -p ~/air-quality-display'
scp display/reterminal/air_quality_display.py pi@192.168.1.43:air-quality-display/
ssh pi@192.168.1.43
```

Then run these **on the Pi via SSH**:

```sh
cd ~/air-quality-display
DISPLAY=:0 python3 air_quality_display.py --demo
```

Demo uses clearly labelled invented values, with no network or credentials. Check
both panels, arrows, fonts, fullscreen sizing and Escape before configuring live
access. Use Ctrl+C in SSH if needed to stop the foreground process.

For live access:

```sh
python3 air_quality_display.py --configure
python3 air_quality_display.py --check
DISPLAY=:0 python3 air_quality_display.py
```

At configuration, accept the existing monitor's default API label or enter your
own. Enter an Ubidots API token in the masked prompt, preferably scoped read-only
to this device. This is not the Singapore API key. It is saved only to
`~/.config/air-quality-display/config.json`, mode 0600, outside the project. It is
a private plaintext file, not an encrypted vault. Never copy it into Git, logs,
screenshots, work orders or chat. SSH encrypts transfer; no token in a command or
URL. The display does not automatically reuse Mac MCP/CLI credentials.

`--check` performs the same read-only API calls and prints observations/statuses
without opening Tk or disclosing the token. It can exit successfully with stale
or absent data: inspect the text, not just the process exit code. On a network
error the check prints only a fixed/sanitized error. No auto-start service is
installed by these trial steps; leave SSH open during the trial. See the optional
startup setup below for unattended operation. Stop Chromium from its close button to avoid
leaving its failed dashboard behind the native window.

## Verification and rollback

From the repository root:

```sh
python3 -m unittest discover -s display/reterminal/tests -v
```

Tests cover missing/invalid/zero values, timestamps, trends, stale/offline state,
private configuration, header authentication and rejection of redirects. Tests do
not authenticate a real account, render Tk, or prove readability on the device.
GitHub runs the display tests in its own credential-free workflow. Historical
validation and remaining owner checks are in the [work order](../../docs/workorders/2026-10-15-reterminal-display.md).

To stop the trial, press Escape. The trial changes no services or system packages. Optional setup below changes
user startup settings and adds a saved Wi-Fi network only when invoked.
Delete the private configuration separately if you no longer need the credential
stored on the Pi. Deployment remains local until you explicitly copy a newer
reviewed script; Git pushes alone do not update the device.

Reference: [Ubidots variable-data API](https://docs.ubidots.com/v1.6/reference/get-variable-data).

## Optional office Wi-Fi and startup on boot (Buster/X11)

These are explicit opt-in changes for the observed Buster/wpa_supplicant setup.
The Wi-Fi helper supports WPA2-Personal (or a compatible shared-password mixed
network), not WPA3-only, enterprise credentials, certificates or captive portals.
It preserves existing networks and country settings, privately backs up the
existing configuration, and adds an office network with lower priority than the
usual default home network. Hidden SSIDs are supported. The key is stored as its
derived PSK (also sensitive), never echoed or passed in command arguments.
The helper deliberately does not reconnect or restart networking; it is read at
next boot. Do not expose either the configuration or its private backup.

Copy both scripts from a **Mac terminal** (not inside the Pi SSH session):

```sh
scp /Users/chipmc/Documents/Maker/Ubidots/Air-Quality-Wing/display/reterminal/*.py pi@192.168.1.43:air-quality-display/
```

Then run these on the **Pi over SSH**, one at a time:

```sh
cd ~/air-quality-display
sudo python3 setup_reterminal.py wifi
```

Enter the exact office SSID, then the shared password twice at the masked prompts.
No active connection changes at this point. Do not enter sudo's own password in
the office-Wi-Fi password fields; its prompt, if any, comes before the script.

Ensure `python3 air_quality_display.py --check` already works with private live
credentials. Then install the current user's desktop launcher (without sudo):

```sh
python3 setup_reterminal.py kiosk
sudo raspi-config nonint do_boot_behaviour B4
```

The last command enables automatic login to the graphical desktop. The launcher
starts this app with `--keep-awake` when that user logs into the desktop; it is
independent of the SSH session. A user desktop entry is installed in
`~/.config/autostart/air-quality-display.desktop`, referencing
`~/air-quality-display/start-display.sh`. The app applies `xset s off`, `s noblank`,
`-dpms`, and screen-saver reset every minute for the X11 session. These options
prevent idle screen blanking; they do not change brightness or hardware power.
The launcher uses the desktop's display environment rather than hardcoding it.
Errors go to `~/.local/state/air-quality-display/app.log`, created privately.

Reboot when ready (the SSH connection will close):

```sh
sudo reboot
```

Confirm the live app appears without logging in, data returns, and the screen
stays on for at least 15 minutes without touch. Repeat at the office; its IP
address will normally change. Try `ssh pi@raspberrypi.local` or find the new IP in
the office router. If initially offline, the app remains visible and retries at
its next five-minute poll. This is desktop autostart, not a crash-restarting
service. Do not start a second manual copy on top of the autostarted instance.

Rollback: remove only `~/.config/autostart/air-quality-display.desktop` to stop
future automatic app launches; choose desktop login without autologin (`B3`) in
raspi-config if desired. To restore idle display power management for the current
X session after stopping the app, use `DISPLAY=:0 xset s default` and
`DISPLAY=:0 xset +dpms`. Remove the office network's managed `network={...}` block
with a root-owned editor if no longer needed. A backup path is printed during
Wi-Fi setup; restoring an old backup wholesale also discards any later network
changes, so preserve those first. Do not change networking over SSH without
planning how to reconnect.

References: [desktop autostart specification](https://specifications.freedesktop.org/autostart/latest/),
[Raspberry Pi boot/login settings](https://www.raspberrypi.com/documentation/computers/configuration.html).
