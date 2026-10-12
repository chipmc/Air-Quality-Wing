"""Packaging checks require the pinned CLI; behavior tests need no packages."""
import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_pm25", ROOT / "tools/prepare_deployment.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
try:
    from cli.functions.helpers import compress_project_to_zip, read_manifest_project_file
    from cli.functions.pipelines import CompressProjectStep
    import yaml
    CLI_AVAILABLE = True
except ImportError:
    CLI_AVAILABLE = False


@unittest.skipUnless(CLI_AVAILABLE, "Install requirements-dev.txt for CLI packaging checks")
class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        shutil.copytree(ROOT / "function", self.root / "function", ignore=shutil.ignore_patterns("__pycache__"))
        self.patch = patch.object(p, "ROOT", self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.directory.cleanup()

    def test_manifest_and_uploaded_files_are_credential_free(self):
        target = p.prepare("existing-monitor")
        manifest = read_manifest_project_file(target)
        self.assertFalse(manifest.function.triggers.schedulerEnabled)
        self.assertFalse(manifest.function.triggers.httpEnabled)
        self.assertEqual(manifest.function.serverless.authToken, "")
        data = compress_project_to_zip(target, CompressProjectStep().exclude_files)
        with zipfile.ZipFile(data) as z:
            self.assertEqual(set(z.namelist()), {"main.py", "config.json"})
            self.assertEqual(json.loads(z.read("config.json"))["mode"], "preview")

    def test_reprepare_preserves_binding_and_changes_mode_explicitly(self):
        target = p.prepare("existing-monitor")
        f = target / ".manifest.yaml"
        manifest = yaml.safe_load(f.read_text())
        manifest["function"]["id"] = "existing-remote-id"
        manifest["function"]["serverless"]["authToken"] = "fake-private-binding"
        f.write_text(yaml.safe_dump(manifest))
        p.prepare("existing-monitor", live=True, schedule=True)
        updated = read_manifest_project_file(target)
        self.assertEqual(updated.function.id, "existing-remote-id")
        self.assertEqual(updated.function.serverless.authToken, "fake-private-binding")
        self.assertTrue(updated.function.triggers.schedulerEnabled)
        self.assertEqual(updated.function.triggers.schedulerCron, "*/15 * * * *")
        self.assertEqual(json.loads((target / "config.json").read_text())["mode"], "live")

    def test_extra_private_files_block_preparation(self):
        target = p.prepare("existing-monitor")
        (target / ".env").write_text("FAKE_SECRET=not-a-real-credential")
        with self.assertRaisesRegex(ValueError, "extra files"):
            p.prepare("existing-monitor")

    def test_templates_and_credentials_are_not_device_labels(self):
        for bad in ["{{ARGON_UBIDOTS_KEY}}", "configure-device-label", "BBFF-fake-token", "a/b"]:
            with self.assertRaises(ValueError): p.prepare(bad)


if __name__ == "__main__": unittest.main()
