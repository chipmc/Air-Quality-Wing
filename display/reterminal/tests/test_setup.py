import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

s = module('setup_display', 'setup_reterminal.py')
a = module('awake_display', 'air_quality_display.py')


class SetupTests(unittest.TestCase):
    def test_wifi_preserves_home_and_globals_and_creates_private_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wpa.conf'
            original = 'country=SG\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nnetwork={\nssid="Home"\npsk="HOME_PRIVATE"\n}\n'
            path.write_text(original)
            backup = s.add_wifi(path, 'Office "quoted" network', 'OFFICE_PRIVATE')
            result = path.read_text()
            self.assertTrue(result.startswith(original))
            self.assertNotIn('OFFICE_PRIVATE', result)
            self.assertIn('ssid=' + 'Office "quoted" network'.encode().hex(), result)
            self.assertIn('priority=-10', result)
            self.assertEqual(backup.read_text(), original)
            for p in (path, backup): self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_known_wpa2_key_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wpa.conf'
            path.write_text('country=SG\n')
            s.add_wifi(path, 'IEEE', 'password')
            self.assertIn('psk=f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e', path.read_text())

    def test_duplicate_and_bad_password_do_not_modify_wifi(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wpa.conf'
            path.write_text('country=SG\n')
            for ssid, password in [('', 'password'), ('x' * 33, 'password'), ('office', 'short'), ('office', 'line\nbreak')]:
                with self.assertRaises(s.SetupError): s.add_wifi(path, ssid, password)
                self.assertEqual(path.read_text(), 'country=SG\n')
            s.add_wifi(path, 'office', 'password')
            saved = path.read_text()
            with self.assertRaises(s.SetupError): s.add_wifi(path, 'office', 'different')
            self.assertEqual(path.read_text(), saved)

    def test_startup_is_user_scoped_and_idempotent_and_preserves_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            folder = home / 'app space'
            folder.mkdir()
            app = folder / 'air_quality_display.py'
            app.write_text('# dummy app\n')
            config = home / '.config/air-quality-display/config.json'
            config.parent.mkdir(parents=True)
            config.write_text('{}')
            desktop = s.install_kiosk(home, app)
            self.assertIn('--keep-awake', app.with_name('start-display.sh').read_text())
            self.assertNotIn('DISPLAY=:0', app.with_name('start-display.sh').read_text())
            self.assertIn('Terminal=false', desktop.read_text())
            original = desktop.read_text()
            s.install_kiosk(home, app)
            self.assertEqual(desktop.read_text(), original)
            desktop.write_text('USER CUSTOMIZATION')
            with self.assertRaises(s.SetupError): s.install_kiosk(home, app)
            self.assertEqual(desktop.read_text(), 'USER CUSTOMIZATION')

    def test_no_credentials_or_app_means_no_startup_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with self.assertRaises(s.SetupError): s.install_kiosk(home, home / 'missing.py')
            self.assertFalse((home / '.config/autostart').exists())

    def test_awake_uses_only_unprivileged_xset_and_handles_missing_binary(self):
        with patch.object(a.subprocess, 'run') as run:
            self.assertTrue(a.keep_screen_awake())
            self.assertEqual(run.call_args_list[0].args[0], ['xset', 's', 'off'])
            self.assertEqual(run.call_count, 4)
        with patch.object(a.subprocess, 'run', side_effect=FileNotFoundError):
            self.assertFalse(a.keep_screen_awake())


if __name__ == '__main__': unittest.main()
