#!/usr/bin/env python3
"""Cross-platform zero-setup launcher for Vimux Challenge."""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def main() -> int:
    repo_dir = Path(__file__).resolve().parent
    venv_dir = repo_dir / ".venv"
    venv_py = _venv_python(venv_dir)

    if not venv_py.exists():
        print("Creating virtual environment in .venv...")
        venv.create(venv_dir, with_pip=True)

    probe = subprocess.run(
        [str(venv_py), "-c", "import textual"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode != 0:
        print("Installing dependencies into .venv...")
        subprocess.check_call(
            [str(venv_py), "-m", "pip", "install", "--quiet", "-r", str(repo_dir / "requirements.txt")]
        )

    env = os.environ.copy()
    src_dir = str(repo_dir / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else src_dir

    result = subprocess.run([str(venv_py), "-m", "vim_tmux_quest", *sys.argv[1:]], env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
