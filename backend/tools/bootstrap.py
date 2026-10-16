"""Create backend/.venv with the pinned CLI; never configure account credentials."""
import subprocess
import sys
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]


def interpreter():
    for name in ("python3.12", "python3.13", "python3.14"):
        found = which(name)
        if found:
            return found
    if sys.version_info >= (3, 12):
        return sys.executable
    raise SystemExit("Install Python 3.12, then rerun Setup Python tooling. Cloud code uses Python 3.11 separately.")


if __name__ == "__main__":
    python = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        subprocess.run([interpreter(), "-m", "venv", str(ROOT / ".venv")], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements-dev.txt")], check=True)
    subprocess.run([str(python), str(ROOT / "tools/workflow.py"), "doctor"], check=True)
