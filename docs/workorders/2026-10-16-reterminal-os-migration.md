# Work order: Upgrade original reTerminal from Buster to 64-bit Bookworm

- Date: 16 October 2026; Asia/Singapore
- Status: preparation; awaiting verified backup and physical equipment
- Owner: Chip McClelland; developer: Codex
- Branch: backend/central-outdoor-pm25; candidate additions remain uncommitted
- Independent review: not run

## Goal and scope

Owner authorized proceeding with a supported 64-bit OS replacement after the
successful native display trial. Owner reports pi password already changed.
Use an original reTerminal/CM4-compatible image and restore native display,
private Ubidots configuration, office/home connectivity, startup and screen-on.
No Particle firmware or UbiFunction changes required. Flashing erases the device;
complete and verify a private backup before choosing WRITE in Imager.

## Source and compatibility findings

Seeed's current reTerminal guide provides a 64-bit Bookworm image with drivers:
https://wiki.seeedstudio.com/reTerminal/
Its image-specific warning says not to use Imager advanced initial configuration
with the packaged Bookworm image because of possible display/driver problems.
Follow that warning rather than generic Imager customization instructions.
Official Mac flashing uses raspberrypi/usbboot (rpiboot), libusb/pkg-config,
Raspberry Pi Imager, a data-capable USB-C cable and an internal boot-mode switch.
A screwdriver is needed to open the back and remove the heatsink to access it.
Ethernet and a temporary USB keyboard are useful to regain networking/SSH after
first boot. Do not assume SSH or the old pi password survives reimaging.

## Backup and restore plan

Back up ~/air-quality-display, ~/.config/air-quality-display and the app's user
autostart entry. Back up existing wpa_supplicant configuration separately if
needed, or re-enter home/office network credentials privately. Never put any
credential backup in Git or chat. Verify downloaded archive contents without
printing file bodies. This is an application/configuration backup, not a full
bootable disk image or complete rollback; take an eMMC image before flashing
if full-system recovery is required or other device data matters.

After flash: boot with working display, replace any default password, enable SSH,
apply available security updates from working repositories. Restore app/private
configuration, adapt Wi-Fi for NetworkManager if active, and check X11/Wayland
before reusing xset. The Buster wifi helper deliberately refuses NetworkManager;
never copy the old Wi-Fi file blindly into the new OS. Verify demo, live --check,
GUI, trends/timezone, reboot/autostart, sustained screen-on and office Wi-Fi.

## Validation and acceptance

Planning only. No device backup, downloads, flashing or migration executed yet.
Existing demo/startup/live/screen-on owner evidence remains in earlier work orders.
Owner final migration acceptance, backup integrity, source/image verification,
actual OS/security-update state, target networking and display checks pending.

## Preparation and backup validation — 16 October 2026

Owner transferred the app/settings archive to
~/reterminal-private-backups/reterminal-backup-2026-10-16.tar.gz. Verified locally:
7611 bytes, mode 0600, required app/setup/config/autostart/Wi-Fi paths present,
no absolute or parent-traversal archive paths. Inspected metadata/names only;
no credential contents extracted or printed. This remains an app/config backup,
not a whole-device image. Owner reports pi password was already changed; this
will need reapplying after flashing a factory image.

Mac already has Homebrew, Apple Command Line Tools and Raspberry Pi Imager.
Installed Homebrew dependencies libusb 1.0.30 (upgraded from 1.0.29) and pkgconf
3.0.7. Downloaded official raspberrypi/usbboot source with its rpi-eeprom submodule;
make INSTALL_PREFIX=/usr/local built the local binary and rpiboot -h succeeded.
Compiler emitted a deployment-target warning for libusb (built for macOS 27,
link target 13.3); the binary nevertheless ran on this Mac. No privileged USB
boot operation was run and no system-wide rpiboot installation was performed.
The bundled mass-storage-gadget64 directory must be explicitly supplied with -d;
do not select recovery/EEPROM-flash directories for this OS migration.

Seeed official arm64 Bookworm ZIP download in progress in the chat's
work/reterminal-upgrade directory. Image URL:
https://files.seeedstudio.com/wiki/ReTerminal/RPiOS_Images/2024-03-14-Raspbian-reTerminal/2024-03-14-Raspbian-reTerminal-arm64.zip
Expected download length from HTTPS response: 1737264214 bytes. ZIP validation
and extraction pending. Physical data cable/screwdriver readiness pending owner
reply. No device shutdown, switch movement, flashing, reboot or restore yet.

## Image and tool preparation completed

- Official usbboot source revision: 861a703d8b51f42b76bcdff49da3e0f2766966bf;
  rpiboot -V succeeded. The local mass-storage-gadget64 payload is present.
- Seeed arm64 ZIP completed with expected 1737264214 bytes.
- Full ZIP member extraction completed with CRC verification. Extracted image:
  2024-03-14-Raspbian-reTerminal-arm64.img, 6094323712 bytes.
- Measured image SHA256:
  97e32d5360fb19f92e93240e4d740dba32e4322558480d428a2906d975aa95b0.
  This is a locally measured integrity identifier, not a vendor-signed checksum.
- Preparation folder:
  /Users/chipmc/Documents/Codex/2026-10-12/referenced-chatgpt-conversation-this-is-an/work/reterminal-upgrade
- Private backup remains outside the Git repository and was not extracted.

Next: owner confirms cable/screwdriver, powers down and disconnects the device,
opens the case and identifies the boot switch using Seeed's diagram/photo.
Flashing and restore remain pending. Keep the OS image customization warning in
scope and verify the target storage identity before any erase/write action.

## Storage identification and Imager preparation

Owner moved boot switch and ran rpiboot; reported second-stage boot completed.
Read-only diskutil verification found /dev/disk6, USB external mmcblk0 Media,
31268536320 bytes (31.3 GB decimal; Imager shows 29.1 GB), with old boot/Linux
partitions. Raspberry Pi Imager v2.0.7 prepared for Pi 4/CM4 family, custom
2024-03-14-Raspbian-reTerminal-arm64.img, storage mmcblk0 Media. Customization
was skipped automatically for this custom image. Stopped at the Write summary;
no erase/write started by agent. Owner must review and click Write/confirm erase
and enter any local Mac authorization themselves. Backup already verified.

## Owner flashing success and SSH preparation

Owner reported Imager success. Imager had ejected storage; owner repeated
rpiboot in flashing mode. Verified disk6 still mmcblk0 Media / 31268536320 bytes,
with new bootfs 536.9 MB and Linux root 5.6 GB (remaining free space awaits
first-boot expansion). Mounted verified disk6s1 at /Volumes/bootfs, confirmed
config.txt and cmdline.txt, added ssh boot-enable flag, synced and safely ejected
disk6. No credentials, network settings, boot drivers or customisation changed.
Owner must unplug USB, restore normal boot switch, refit heatsink/thermal pad and
case, connect Ethernet if available and apply normal power. First boot, user
credentials, SSH login and actual aarch64/Bookworm checks remain unverified.
Old pi password is not restored by imaging; reset any factory credential at login.


## Completed migration and recovery — owner validation, 16 October 2026

This section supersedes the earlier pending status entries above.

- Owner confirmed Debian 12 Bookworm, 64-bit userspace, pi UID 1000 and
  /home/pi. Initial setup lacked a usable login despite the SSH flag; because
  the device has no usable keyboard, login should have been provisioned before
  first boot. Re-entered USB storage mode and used the documented userconf.txt
  method with a privately entered, SHA-512 hashed password; no password/hash
  was printed or added to this repository. SSH login then succeeded.
- Restored app and private configuration from the existing private backup.
  Fixed the image's root-owned /home/pi/.config directory with a targeted
  ownership change. Live indoor/outdoor reads succeeded. Did not copy the old
  wpa_supplicant configuration over NetworkManager.
- Saved Home and Work NetworkManager profiles via nmtui. Corrected Home SSID
  to its exact 2.4 GHz broadcast name. Home Wi-Fi and SSH at 192.168.1.43 were
  verified. Work remains saved but untested until the office visit.
- Selected X11 and desktop auto-login using raspi-config and installed the
  display's user autostart launcher. DSI-1 requires xrandr rotation right;
  added that command before the app exec in the device's local launcher.
  Re-running the current kiosk setup helper can overwrite this local rotation
  customization; preserve it until the helper gains explicit rotation support.
- Package upgrade initially failed because bundled Seeed DKMS sources were
  incompatible with Linux 6.12.109. Reviewed and pinned Seeed source revision
  d8370e5919f809e0f91afa2a2349535714676385. Backed up the three old source
  directories on the Pi under /root/reterminal-driver-sources-before-repair.tar.gz.
  Replaced sources for mipi_dsi, lis3lv02d, and bq24179_charger and successfully
  built/installed them for both 6.12.109+rpt-rpi-v8 and rpi-2712; retained the
  installed 6.6.20 modules. dpkg configuration and dependency checks succeeded.
- First new-kernel boot had a black screen: the old overlay declared
  i2c_dsi,ili9881d, while the new driver matches i2c_dsi,ili9881x. Built the
  matching reTerminal overlay from the same pinned source, backed up the boot
  config and old overlay, installed it, and disabled the duplicate legacy
  vc4-kms-v3d-pi4 entry while retaining vc4-kms-v3d and tp_rotate=0.
- Owner subsequently confirmed the live air-quality app visible and upright,
  touch aligned, uname -r = 6.12.109+rpt-rpi-v8, and sudo dpkg --audit produced
  no output. These are owner-reported hardware results, not agent-run checks.

Remaining: test Work Wi-Fi at the office; confirm deployment/readability of the
larger-font app change documented separately. A clean dpkg audit confirms package
configuration consistency, not that no further upgrades are available. Future
kernel upgrades must check Seeed driver AND overlay compatibility before reboot.
No new full image backup or post-upgrade private settings backup was recorded.
