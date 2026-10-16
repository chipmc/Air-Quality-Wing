#!/usr/bin/env python3
"""Explicit setup for the original reTerminal's Buster/X11 desktop and WPA2 Wi-Fi."""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

WIFI_PATH = Path('/etc/wpa_supplicant/wpa_supplicant.conf')
MARKER = '# Air-Quality-Wing managed launcher'


class SetupError(Exception):
    pass


def private_write(path, text, mode=0o600):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.aqw-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def install_kiosk(home, app):
    if not app.is_file():
        raise SetupError('Copy air_quality_display.py alongside this setup script first')
    if not (home / '.config/air-quality-display/config.json').is_file():
        raise SetupError('Configure and check live API access before installing startup')
    autostart = home / '.config/autostart'
    state = home / '.local/state/air-quality-display'
    autostart.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    launcher = app.with_name('start-display.sh')
    desktop = autostart / 'air-quality-display.desktop'
    # Refuse to replace unrelated local customizations under these filenames.
    for path in (launcher, desktop):
        if path.exists() and MARKER not in path.read_text():
            raise SetupError('Existing launcher is not managed by this setup; preserve it first')
    shell = '#!/bin/sh\n' + MARKER + '\numask 077\nexec /usr/bin/python3 ' + shlex.quote(str(app))
    shell += ' --keep-awake >> ' + shlex.quote(str(state / 'app.log')) + ' 2>&1\n'
    private_write(launcher, shell, 0o700)
    # Desktop Exec has its own quoting rules (not shell quoting).
    escaped = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    entry = '[Desktop Entry]\n' + MARKER + '\nType=Application\nName=Air Quality Display\n'
    entry += 'Exec="' + escaped + '"\nTerminal=false\nX-GNOME-Autostart-enabled=true\n'
    private_write(desktop, entry)
    return desktop


def add_wifi(path, ssid, password):
    ssid_bytes = ssid.encode('utf-8')
    if not 1 <= len(ssid_bytes) <= 32 or any(c in ssid for c in '\x00\n\r'):
        raise SetupError('SSID must contain 1–32 UTF-8 bytes without line breaks')
    if not 8 <= len(password) <= 63 or any(ord(c) < 32 or ord(c) > 126 for c in password):
        raise SetupError('Use an 8–63 character ASCII WPA2 passphrase')
    if not path.is_file() or path.is_symlink():
        raise SetupError('Expected a regular existing Buster wpa_supplicant configuration; no file changed')
    original = path.read_text()
    identity = 'aqw-office-' + hashlib.sha256(ssid_bytes).hexdigest()[:16]
    if identity in original or ('ssid="' + ssid + '"') in original or ('ssid=' + ssid_bytes.hex()) in original:
        raise SetupError('A matching network already exists; no file changed')
    # wpa_supplicant accepts an unquoted hex SSID and a PBKDF2-derived 256-bit PSK.
    # Neither the password nor its derived PSK is passed in a command or printed.
    psk = hashlib.pbkdf2_hmac('sha1', password.encode('ascii'), ssid_bytes, 4096, 32).hex()
    block = '\n# Office network added by Air-Quality-Wing\nnetwork={\n'
    block += '    ssid=' + ssid_bytes.hex() + '\n    psk=' + psk + '\n'
    block += '    key_mgmt=WPA-PSK\n    scan_ssid=1\n    priority=-10\n'
    block += '    id_str="' + identity + '"\n}\n'
    # Backup contains credentials too: create it privately before replacing anything.
    fd, backup = tempfile.mkstemp(dir=str(path.parent), prefix='.aqw-wifi-backup-')
    with os.fdopen(fd, 'w') as stream:
        stream.write(original)
    private_write(path, original.rstrip() + '\n' + block)
    return Path(backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['kiosk', 'wifi'])
    args = parser.parse_args()
    try:
        if args.action == 'kiosk':
            if os.geteuid() == 0:
                raise SetupError('Run kiosk as pi, without sudo')
            if not shutil.which('xset'):
                raise SetupError('xset is not installed; no launcher installed')
            desktop = install_kiosk(Path.home(), Path(__file__).resolve().with_name('air_quality_display.py'))
            print('Desktop startup installed for this user. No reboot or autologin change made.')
            print('Next: enable desktop auto-login, then reboot when ready.')
        else:
            if os.geteuid() != 0:
                raise SetupError('Run Wi-Fi setup using sudo')
            # This helper deliberately supports the observed Buster networking stack only.
            if subprocess.run(['systemctl', 'is-active', '--quiet', 'NetworkManager'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                raise SetupError('NetworkManager is active; use its network setup instead')
            ssid = input('Office SSID (exact name): ')
            password = getpass.getpass('Office Wi-Fi password (hidden): ')
            confirm = getpass.getpass('Confirm Wi-Fi password (hidden): ')
            if password != confirm:
                raise SetupError('Passwords differ; no configuration changed')
            backup = add_wifi(WIFI_PATH, ssid, password)
            print('Office network saved alongside existing networks. Private backup: ' + str(backup))
            print('No reconnect requested. It will be available after the next reboot.')
        return 0
    except (SetupError, OSError, UnicodeError):
        # Do not echo paths or arbitrary exceptions from credential-bearing file operations.
        # Our fixed SetupError messages never contain supplied secrets.
        import sys
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, SetupError) else 'Setup failed; inspect file permissions and prerequisites')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
