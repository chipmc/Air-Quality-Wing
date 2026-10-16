"""Credential-free project staging for the pinned Ubidots CLI."""
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,59}")


def read_project(root):
    root = Path(root)
    metadata = json.loads((root / "project.json").read_text())
    if not SLUG.fullmatch(metadata.get("label", "")):
        raise ValueError("Project label must be a lowercase name with optional hyphens")
    files = metadata.get("files")
    if not isinstance(files, list) or not files or len(files) != len(set(files)) or not {"main.py", "config.json"}.issubset(files):
        raise ValueError("Files must be a unique allowlist including main.py")
    for name in files:
        path = Path(name)
        if (path.is_absolute() or ".." in path.parts or not path.parts
                or any(part.startswith(".") for part in path.parts)
                or path.suffix.lower() in {".pem", ".key", ".der"}):
            raise ValueError("Only public source/data files belong in the upload allowlist")
        source = root / "function" / path
        if (not source.is_file() or source.is_symlink()
                or not source.resolve().is_relative_to((root / "function").resolve())):
            raise ValueError("Every allowlisted source must be a regular file within function/")
    return metadata


def prepare(root, device_label=None, live=False, schedule=False, profile=None):
    if sys.version_info < (3, 12):
        raise RuntimeError("Use Python 3.12+ for Ubidots CLI 2.1.2; Python 3.12 is recommended")
    import yaml
    from cli.functions.helpers import read_manifest_project_file

    root = Path(root)
    metadata = read_project(root)
    if profile is not None and not SLUG.fullmatch(profile):
        raise ValueError("Profile must be a lowercase name with optional hyphens")
    label = metadata["label"] + ("-" + profile if profile else "")
    cron = metadata.get("cron", "")
    if schedule and not cron:
        raise ValueError("Set a project cron expression before enabling its schedule")
    config = json.loads((root / "function/config.json").read_text())
    config["mode"] = "live" if live else "preview"
    if metadata.get("requires_device_label"):
        if (not isinstance(device_label, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", device_label)
                or device_label.lower() in {"configure-device-label", "your-device-label"}
                or device_label.startswith("BBFF")):
            raise ValueError("Supply the actual device API label, never a credential or template")
        config["device_label"] = device_label
    target = root / ".deploy"
    if profile:
        target /= profile
    target /= metadata["label"]
    for location in [root / ".deploy", root / ".deploy" / profile if profile else target, target]:
        if location.is_symlink():
            raise ValueError("Private staging paths must not be symbolic links")
    manifest_path = target / ".manifest.yaml"
    if manifest_path.is_symlink():
        raise ValueError("Private manifest must not be a symbolic link")
    try:
        old = yaml.safe_load(manifest_path.read_text()) if manifest_path.exists() else None
    except yaml.YAMLError:
        raise ValueError("Invalid private manifest; inspect its format locally") from None
    if old:
        if not isinstance(old, dict) or old.get("function", {}).get("label") != label:
            raise ValueError("Unexpected deployment binding; inspect .deploy before proceeding")
        manifest = old
    else:
        runtime = metadata.get("runtime", "python3.11:lite")
        manifest = {
            "globals": {"engine": "DOCKER", "label": label},
            "project": {"createdAt": datetime.now(timezone.utc).isoformat(), "name": label,
                        "language": "python", "runtime": runtime},
            "function": {"id": "", "label": label,
                         "serverless": {"runtime": runtime, "params": "{}", "authToken": "",
                                        "isRawFunction": False, "timeout": 30},
                         "triggers": {}},
        }
    manifest["function"]["serverless"]["runtime"] = metadata.get("runtime", "python3.11:lite")
    manifest["function"]["triggers"].update(
        schedulerEnabled=schedule, schedulerCron=cron,
        httpEnabled=metadata.get("http_enabled", False), httpMethods=["POST"],
        httpIsSecure=True, httpHasCors=False)
    # Preserve existing id/account-token binding. Private manifest is not uploaded by CLI.
    allowed = set(metadata["files"]) | {".manifest.yaml"}
    if target.exists():
        if any(path.is_symlink() for path in target.rglob("*")):
            raise ValueError("Deployment folder must not contain symbolic links")
        extras = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()} - allowed
        if extras:
            raise ValueError("Deployment folder has extra files; remove them before preparing")
    target.mkdir(parents=True, exist_ok=True)
    for name in metadata["files"]:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if name == "config.json":
            destination.write_text(json.dumps(config, indent=2) + "\n")
        else:
            shutil.copyfile(root / "function" / name, destination)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    read_manifest_project_file(target)
    print(f"Prepared {label}; mode={config['mode']}; schedule={schedule}. Nothing deployed.")
    return target
