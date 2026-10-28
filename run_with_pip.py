"""Install the pinned app dependencies with pip, then start the offline judge launcher.

From the repository root: python run_with_pip.py
Requires Python 3.11, 3.12, or 3.13. No uv installation is needed.
"""

import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def environment_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def dependency_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for filename in ("pyproject.toml", "requirements-pip.txt"):
        digest.update((root / filename).read_bytes())
    digest.update(f"{sys.version_info.major}.{sys.version_info.minor}".encode())
    return digest.hexdigest()


def prepare_pip_environment(root: Path) -> Path:
    environment = root / ".venv-pip"
    python = environment_python(environment)
    marker = environment / ".saifa-pip-dependencies"
    fingerprint = dependency_fingerprint(root)
    if not python.exists():
        print("Creating an isolated pip environment...", flush=True)
        venv.create(environment, with_pip=True)
    if not marker.exists() or marker.read_text().strip() != fingerprint:
        print(
            "Installing pinned dependencies with pip (first run may take a few minutes)...",
            flush=True,
        )
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "-r",
                str(root / "requirements-pip.txt"),
                "-e",
                str(root),
            ],
            cwd=root,
            check=True,
        )
        marker.write_text(fingerprint + "\n")
    return python


def main() -> int:
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        print("SAIFA requires Python 3.11, 3.12, or 3.13.", file=sys.stderr)
        return 1
    try:
        python = prepare_pip_environment(ROOT)
        return subprocess.call([str(python), str(ROOT / "commands/run_judge_app.py")], cwd=ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"pip setup or app launch failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
