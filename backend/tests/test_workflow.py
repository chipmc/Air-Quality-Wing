import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import workflow
from ubifunction_project import read_project, prepare

try:
    import yaml
    from cli.functions.helpers import read_manifest_project_file, compress_project_to_zip
    from cli.functions.pipelines import CompressProjectStep
    CLI = sys.version_info >= (3, 12)
except ImportError:
    CLI = False


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.replace = patch.object(workflow, "BACKEND", self.root)
        self.replace.start()

    def tearDown(self):
        self.replace.stop()
        self.tmp.cleanup()

    def test_scaffold_is_local_inert_and_does_not_overwrite(self):
        root = workflow.scaffold("next-function")
        metadata = read_project(root)
        self.assertEqual(metadata["label"], "next-function")
        self.assertFalse(metadata["http_enabled"])
        self.assertEqual(metadata["cron"], "")
        with patch.object(workflow, "invoke") as invoke:
            workflow.main(["new", "--project", "another-function"])
            invoke.assert_not_called()
        with self.assertRaises(ValueError): workflow.scaffold("next-function")
        for bad in ["../escape", "/absolute", "Bad_Name", "x;touch"]:
            with self.assertRaises(ValueError): workflow.scaffold(bad)

    def test_upload_allowlist_rejects_hidden_and_external_files(self):
        root = workflow.scaffold("next-function")
        f = root / "project.json"
        for bad in ["../secret", ".env", "id.pem", "/tmp/secret"]:
            metadata = json.loads(f.read_text())
            metadata["files"] = ["main.py", "config.json", bad]
            f.write_text(json.dumps(metadata))
            with self.assertRaises(ValueError): read_project(root)

    def test_scaffold_contract_runs_without_platform_or_secrets(self):
        root = workflow.scaffold("next-function")
        workflow.main(["test", "--project", "next-function"])

    def test_remote_actions_are_explicit_and_profile_scoped(self):
        workflow.scaffold("next-function")
        with patch.object(workflow, "cli_path", return_value="/tools/ubidots"), patch.object(workflow, "invoke") as invoke:
            workflow.main(["run", "--project", "next-function", "--profile", "aqw-dev"])
            command = invoke.call_args_list[0].args[0]
            self.assertIn("next-function-aqw-dev", command)
            self.assertEqual(command[-2:], ["--payload", "{}"])
            self.assertEqual(invoke.call_args_list[1].args[0][1:3], ["functions", "logs"])
            self.assertIn("aqw-dev", command)

    @unittest.skipUnless(CLI, "Requires pinned CLI tooling on Python 3.12+")
    def test_remote_commands_parse_in_actual_cli_without_login(self):
        import subprocess
        workflow.scaffold("next-function")
        commands = []
        with patch.object(workflow, "invoke", side_effect=lambda command, **kw: commands.append(command)):
            for action in ["list", "run", "logs", "config", "login"]:
                workflow.main([action, "--project", "next-function"])
        for command in commands:
            result = subprocess.run(command + ["--help"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(CLI, "Requires pinned CLI tooling on Python 3.12+")
    def test_profiles_keep_remote_bindings_and_modes_separate(self):
        root = workflow.scaffold("next-function")
        dev = prepare(root, profile="dev")
        prod = prepare(root, profile="prod")
        self.assertNotEqual(dev, prod)
        first = yaml.safe_load((dev / ".manifest.yaml").read_text())
        first["function"]["id"] = "dev-only-id"
        first["function"]["serverless"]["authToken"] = "fake-private-binding"
        (dev / ".manifest.yaml").write_text(yaml.safe_dump(first))
        prepare(root, live=True, profile="dev")
        self.assertEqual(read_manifest_project_file(dev).function.id, "dev-only-id")
        self.assertEqual(read_manifest_project_file(prod).function.id, "")
        self.assertEqual(read_manifest_project_file(dev).function.serverless.authToken, "fake-private-binding")
        self.assertFalse(read_manifest_project_file(dev).function.triggers.schedulerEnabled)
        (dev / ".env").write_text("FAKE_SECRET=test-only")
        with self.assertRaisesRegex(ValueError,"extra files"): prepare(root, profile="dev")

    @unittest.skipUnless(CLI, "Requires pinned CLI tooling on Python 3.12+")
    def test_staging_symlink_cannot_redirect_upload(self):
        root = workflow.scaffold("next-function")
        outside = self.root / "private"
        outside.mkdir()
        (root / ".deploy").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            prepare(root, profile="dev")
        self.assertFalse(list(outside.iterdir()))

    @unittest.skipUnless(CLI, "Requires pinned CLI tooling on Python 3.12+")
    def test_push_tests_and_prepares_before_upload(self):
        root = workflow.scaffold("next-function")
        # A source edit must be included even if a previous deployment folder exists.
        target = prepare(root, profile="dev")
        (root / "function/main.py").write_text('def main(args): return {"status": "new-source"}\n')
        with patch.object(workflow,"cli_path",return_value="/tools/ubidots"),patch.object(workflow,"invoke") as invoke:
            workflow.main(["push","--project","next-function","--profile","dev"])
            self.assertEqual(invoke.call_count,2)
            self.assertIn("unittest",invoke.call_args_list[0].args[0])
            self.assertEqual(invoke.call_args_list[1].args[0],["/tools/ubidots","functions","push","--profile","dev"])
        self.assertIn("new-source",(target / "main.py").read_text())


if __name__ == "__main__": unittest.main()
