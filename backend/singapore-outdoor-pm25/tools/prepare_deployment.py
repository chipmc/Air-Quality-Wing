"""Backwards-compatible entry point for preparing the PM2.5 function."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "tools"))
from ubifunction_project import prepare as prepare_project


def prepare(device_label, live=False, schedule=False):
    return prepare_project(ROOT, device_label=device_label, live=live, schedule=schedule)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-label", required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--enable-schedule", action="store_true")
    args = parser.parse_args()
    prepare(args.device_label, args.live, args.enable_schedule)
