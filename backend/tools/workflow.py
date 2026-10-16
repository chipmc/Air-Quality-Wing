"""VS Code/terminal workflow: tests and staging are local; push/run are explicit."""
import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

from ubifunction_project import SLUG, prepare, read_project

BACKEND = Path(__file__).resolve().parents[1]


def project_path(name):
    if not SLUG.fullmatch(name):
        raise ValueError("Use a project name, not a path")
    root = BACKEND / name
    if not root.resolve().is_relative_to(BACKEND.resolve()):
        raise ValueError("Project must remain inside backend/")
    return root


def cli_path():
    path = Path(sys.executable).parent / ("ubidots.exe" if sys.platform == "win32" else "ubidots")
    if not path.is_file():
        raise ValueError("Activate the backend tooling environment first; see backend/README.md")
    return str(path)


def invoke(command, cwd=None):
    return subprocess.run(command, cwd=cwd, check=True)


def scaffold(name):
    root = project_path(name)
    if root.exists():
        raise ValueError("Project already exists; existing code was not changed")
    root.mkdir()
    (root / "function").mkdir()
    (root / "tests").mkdir()
    metadata = {"label": name, "runtime": "python3.11:lite", "cron": "", "http_enabled": False,
                "requires_device_label": False, "files": ["main.py", "config.json"]}
    (root / "project.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (root / "function/config.json").write_text('{"mode": "preview"}\n')
    (root / "function/main.py").write_text('''"""Starter function: no network access or writes. Add scoped behavior and tests."""
def main(args):
    if not isinstance(args, dict):
        return {"status": "error", "reason": "json_object_required"}
    # Never echo args: platform-injected credentials can appear there.
    return {"status": "preview", "message": "Implement this function and its acceptance tests"}
''')
    (root / "tests/test_contract.py").write_text('''import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location("starter", Path(__file__).resolve().parents[1] / "function/main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ContractTests(unittest.TestCase):
    def test_rejects_non_object_request(self):
        self.assertEqual(module.main([])["status"], "error")

    def test_platform_credentials_are_not_echoed(self):
        result = module.main({"_auth_token": "fake-secret", "token": "fake-secret"})
        self.assertNotIn("fake-secret", str(result))
''')
    (root / "README.md").write_text(f'''# {name}

Created from the UbiFunctions workflow. See [backend workflow](../README.md).

Edit `function/main.py`, public `function/config.json`, and `tests/`.
Add acceptance tests for behavior before deploying. The starter has no network
calls or writes and is intentionally inert. `project.json` controls runtime,
public upload files, HTTP availability and scheduling; scheduling is initially off.
Store credentials only in platform secrets or private CLI profiles, never here.
''')
    print(f"Created backend/{name}; review and commit its source/tests/project.json.")
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["doctor", "new", "test", "config", "login", "list", "prepare", "push", "run", "logs"])
    parser.add_argument("--project", default="singapore-outdoor-pm25")
    parser.add_argument("--profile", default="aqw-dev")
    parser.add_argument("--device-label")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--enable-schedule", action="store_true")
    args = parser.parse_args(argv)
    if not SLUG.fullmatch(args.profile):
        parser.error("Use a lowercase profile name with optional hyphens")
    if args.action == "doctor":
        version = importlib.metadata.version("ubidots-cli")
        if sys.version_info < (3, 12) or version != "2.1.2":
            raise ValueError("Use Python 3.12+ and ubidots-cli 2.1.2; setup instructions are in backend/README.md")
        print(f"Python {sys.version.split()[0]}; Ubidots CLI {version}; tooling available.")
        print("Account authentication and live runtime access have not been checked.")
    elif args.action == "new":
        scaffold(args.project)
    elif args.action == "test":
        root = project_path(args.project)
        read_project(root)
        invoke([sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-v"])
    elif args.action == "config":
        # CLI 2.1.2 asks for the profile interactively and ignores --profile in this mode.
        print(f"At the Profile prompt enter: {args.profile}. Enter the token only in the hidden Access Token prompt.", flush=True)
        invoke([cli_path(), "config"])
    elif args.action == "login":
        invoke([cli_path(), "login", "--profile", args.profile])
    elif args.action == "list":
        # Names only: avoid requesting environment/secret/serverless metadata.
        invoke([cli_path(), "functions", "list", "--profile", args.profile, "--fields", "id,label,name"])
    else:
        root = project_path(args.project)
        metadata = read_project(root)
        label = metadata["label"] + "-" + args.profile
        if args.action == "prepare":
            prepare(root, args.device_label, args.live, args.enable_schedule, args.profile)
        elif args.action == "push":
            # Rebuild from current tracked source on every push; never upload a stale staging folder.
            invoke([sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-v"])
            target = prepare(root, args.device_label, args.live, args.enable_schedule, args.profile)
            print(f"Uploading {label} with profile {args.profile}; the Ubidots CLI will ask before overwriting.", flush=True)
            invoke([cli_path(), "functions", "push", "--profile", args.profile], cwd=target)
        else:
            command = [cli_path(), "functions", args.action, "--label", label, "--profile", args.profile]
            if args.action == "run":
                command += ["--payload", "{}"]
            invoke(command)
            if args.action == "run":
                invoke([cli_path(), "functions", "logs", "--label", label, "--profile", args.profile])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, importlib.metadata.PackageNotFoundError) as exc:
        raise SystemExit(str(exc)) from None
