"""Build an allowlisted CLI project. No credentials are read or written."""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(device_label, live=False, schedule=False):
    if sys.version_info < (3, 12):
        raise RuntimeError("Ubidots CLI 2.1.2 requires Python 3.12+; use the documented tooling environment")
    import yaml  # Provided by the pinned CLI; not needed by the deployed function.
    target = ROOT / ".deploy" / "singapore-outdoor-pm25"
    manifest_path = target / ".manifest.yaml"
    old = yaml.safe_load(manifest_path.read_text()) if manifest_path.exists() else None
    if old:
        if not isinstance(old, dict) or old.get("function", {}).get("label") != "singapore-outdoor-pm25":
            raise ValueError("Unexpected deployment binding; inspect .deploy before proceeding")
        manifest = old
        # Preserve remote identity and any private CLI-managed account-token binding.
        manifest["function"]["triggers"]["schedulerEnabled"] = schedule
        manifest["function"]["triggers"]["schedulerCron"] = "*/15 * * * *"
        manifest["function"]["triggers"]["httpEnabled"] = False
    else:
        manifest = {
            "globals": {"engine": "DOCKER", "label": "singapore-outdoor-pm25"},
            "project": {"createdAt": datetime.now(timezone.utc).isoformat(), "name": "singapore-outdoor-pm25",
                        "language": "python", "runtime": "python3.11:lite"},
            "function": {"id": "", "label": "singapore-outdoor-pm25",
                         "serverless": {"runtime": "python3.11:lite", "params": "{}", "authToken": "",
                                        "isRawFunction": False, "timeout": 30},
                         "triggers": {"httpMethods": ["POST"], "httpHasCors": False, "httpIsSecure": True,
                                      "httpEnabled": False, "schedulerCron": "*/15 * * * *",
                                      "schedulerEnabled": schedule}},
        }
    # Refuse extra files because the CLI zips files that Git may ignore (e.g. .env).
    if target.exists():
        extras = {p.name for p in target.iterdir()} - {"main.py", "config.json", ".manifest.yaml"}
        if extras:
            raise ValueError("Deployment folder has extra files; remove them before preparing")
    target.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "function/config.json").read_text())
    config.update(device_label=device_label, mode="live" if live else "preview")
    # Validate before creating an uploadable project.
    import re
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", device_label)
            or device_label in {"configure-device-label", "your-device-label"}
            or device_label.startswith("BBFF")):
        raise ValueError("Supply the actual device API label, never a credential or template")
    shutil.copyfile(ROOT / "function/main.py", target / "main.py")
    (target / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    from cli.functions.helpers import read_manifest_project_file
    read_manifest_project_file(target)  # Validate against the installed CLI schema.
    print(f"Prepared {target}; mode={'live' if live else 'preview'}; schedule={schedule}. Nothing deployed.")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-label", required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--enable-schedule", action="store_true")
    args = parser.parse_args()
    prepare(args.device_label, args.live, args.enable_schedule)
