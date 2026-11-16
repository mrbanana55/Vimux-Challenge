"""CLI entry point with automatic virtual-environment bootstrap."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

os.environ.setdefault("TEXTUAL_DISABLE_KITTY_KEY", "1")


def _ensure_venv_if_needed() -> None:
    """Create/bootstrap local .venv and re-exec if textual is unavailable."""
    try:
        import textual  # noqa: F401
        return
    except ImportError:
        pass

    here = Path(__file__).resolve()
    repo_root: Path | None = None
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() or (parent / "requirements.txt").exists():
            repo_root = parent
            break

    if repo_root is None:
        return

    venv_dir = repo_root / ".venv"
    venv_python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if Path(sys.executable).resolve() == venv_python.resolve():
        return

    if not venv_python.exists():
        print("Setting up virtual environment in .venv...")
        venv.create(venv_dir, with_pip=True)

    probe = subprocess.run(
        [str(venv_python), "-c", "import textual"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode != 0 and (repo_root / "requirements.txt").exists():
        print("Installing dependencies into .venv...")
        subprocess.check_call(
            [str(venv_python), "-m", "pip", "install", "--quiet", "-r", str(repo_root / "requirements.txt")]
        )

    if venv_python.exists():
        os.execv(str(venv_python), [str(venv_python), "-m", "vim_tmux_quest", *sys.argv[1:]])


def _print_status() -> None:
    from vim_tmux_quest import __version__
    from vim_tmux_quest.curriculum import TRACKS, get_all_levels
    from vim_tmux_quest.db.database import Database

    db = Database()
    stats = db.get_player_stats()
    levels = get_all_levels()
    prefix = db.get_setting("tmux_prefix", "ctrl+b")

    print(f"Vimux Challenge v{__version__}")
    print(f"Database: {db.db_path}")
    print(
        f"Player Stats: XP={stats['total_xp']} | "
        f"Levels={stats['levels_completed']}/{len(levels)} | "
        f"Stars={stats['total_stars']}/{len(levels) * 3} | "
        f"Drills={stats['drills_completed']} (Best Streak: {stats['best_drill_streak']}) | "
        f"TMUX Prefix={prefix}"
    )
    print("\nCurriculum Tracks:")
    for t in TRACKS:
        track_lvls = [l for l in levels if l.track_id == t.id]
        print(f"  Track {t.id}: {t.name} ({len(track_lvls)} levels) — {t.description}")


def run() -> None:
    """Launch VIM & TMUX Quest CLI / TUI."""
    _ensure_venv_if_needed()

    from vim_tmux_quest import __version__

    parser = argparse.ArgumentParser(
        prog="vim-tmux-quest",
        description="Interactive terminal game to master VIM motions and TMUX commands.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print player progress and curriculum summary without launching the TUI.",
    )
    args = parser.parse_args()

    if args.status:
        _print_status()
        return

    import textual.constants

    textual.constants.DISABLE_KITTY_KEY = True  # type: ignore[misc]

    from vim_tmux_quest.ui.app import VimTmuxQuestApp

    app = VimTmuxQuestApp()
    app.run()


if __name__ == "__main__":
    run()
