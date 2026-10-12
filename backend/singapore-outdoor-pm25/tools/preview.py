"""Preview a fixture or fetch public NEA data. This tool never writes to Ubidots."""
import argparse
import importlib.util
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("outdoor_pm25", ROOT / "function/main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
parser = argparse.ArgumentParser()
parser.add_argument("--fixture", type=Path)
parser.add_argument("--at", help="Timezone-aware reference time for historical fixtures")
args = parser.parse_args()
if args.fixture:
    source = json.loads(args.fixture.read_text())
    now = module.parse_time(args.at) if args.at else datetime.now(module.timezone.utc)
    dot = module.select_observation(source, "central", now, 10800)
    print(json.dumps({module.VARIABLE: dot}, indent=2))
else:
    headers = {"Accept": "application/json"}
    if os.environ.get("DATAGOVSG_API_KEY"):
        headers["x-api-key"] = os.environ["DATAGOVSG_API_KEY"]
    status, source = module.request_json("GET", module.DGS_URL, headers)
    if status != 200:
        raise SystemExit(f"NEA HTTP {status}; no data written")
    dot = module.select_observation(source, "central", datetime.now(module.timezone.utc), 10800)
    print(json.dumps({module.VARIABLE: dot}, indent=2))
