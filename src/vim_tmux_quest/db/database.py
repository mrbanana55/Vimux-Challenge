"""SQLite persistence layer for player progress, stats, and settings."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_default_db_path() -> Path:
    """Resolve the default SQLite database path.

    Priority:
    1. ``VIM_TMUX_QUEST_DB`` environment variable.
    2. ``<repo_root>/.data/progress.db`` if running inside a repository checkout.
    3. ``~/.vim_tmux_quest/progress.db`` if writable.
    4. ``/tmp/vim_tmux_quest/progress.db`` fallback.
    """
    env_path = os.environ.get("VIM_TMUX_QUEST_DB")
    if env_path:
        return Path(env_path).expanduser()

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            data_dir = parent / ".data"
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
                probe = data_dir / ".write_probe"
                probe.touch()
                probe.unlink()
                return data_dir / "progress.db"
            except OSError:
                break

    home_dir = Path.home() / ".vim_tmux_quest"
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        probe = home_dir / ".write_probe"
        probe.touch()
        probe.unlink()
        return home_dir / "progress.db"
    except OSError:
        return Path("/tmp/vim_tmux_quest/progress.db")


class Database:
    """SQLite database wrapper for VIM & TMUX Quest."""

    DEFAULT_SETTINGS = {
        "tmux_prefix": "ctrl+b",
        "show_hints": "0",
        "campaign_level_id": "",
    }

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create database schema and default rows if they do not exist."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS level_progress (
                    level_id TEXT PRIMARY KEY,
                    completed INTEGER NOT NULL DEFAULT 0,
                    run_completed INTEGER NOT NULL DEFAULT 0,
                    stars INTEGER NOT NULL DEFAULT 0,
                    best_keystrokes INTEGER,
                    best_time_ms INTEGER,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_played_at TEXT
                );

                CREATE TABLE IF NOT EXISTS command_stats (
                    tool TEXT NOT NULL,
                    command_key TEXT NOT NULL,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    mistake_count INTEGER NOT NULL DEFAULT 0,
                    last_practiced_at TEXT,
                    PRIMARY KEY (tool, command_key)
                );

                CREATE TABLE IF NOT EXISTS player_stats (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_xp INTEGER NOT NULL DEFAULT 0,
                    drills_completed INTEGER NOT NULL DEFAULT 0,
                    best_drill_streak INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            for key, value in self.DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )
            conn.execute(
                "INSERT OR IGNORE INTO player_stats (id, total_xp, drills_completed, best_drill_streak) "
                "VALUES (1, 0, 0, 0)"
            )
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(level_progress)").fetchall()
            }
            if "run_completed" not in cols:
                conn.execute(
                    "ALTER TABLE level_progress ADD COLUMN run_completed INTEGER NOT NULL DEFAULT 0"
                )
                conn.execute("UPDATE level_progress SET run_completed = completed")

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Fetch a single setting value."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                return str(row["value"])
            return default if default is not None else self.DEFAULT_SETTINGS.get(key)

    def set_setting(self, key: str, value: str) -> None:
        """Persist a single setting value."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def record_level_attempt(
        self,
        level_id: str,
        completed: bool,
        keystrokes: int,
        time_ms: int,
        stars: int,
        xp_earned: int,
    ) -> dict[str, Any]:
        """Record a level attempt and return the updated level progress row."""
        now = _utc_now_iso()
        clamped_stars = max(0, min(3, stars)) if completed else 0

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM level_progress WHERE level_id = ?",
                (level_id,),
            ).fetchone()

            xp_delta = 0
            if existing is None:
                best_k = keystrokes if completed else None
                best_t = time_ms if completed else None
                comp_int = 1 if completed else 0
                if completed:
                    xp_delta = xp_earned
                conn.execute(
                    """
                    INSERT INTO level_progress (
                        level_id, completed, run_completed, stars, best_keystrokes,
                        best_time_ms, attempts, last_played_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (level_id, comp_int, comp_int, clamped_stars, best_k, best_t, now),
                )
            else:
                was_completed = bool(existing["completed"])
                was_run_completed = bool(existing["run_completed"])
                old_stars = int(existing["stars"])
                new_completed = 1 if (was_completed or completed) else 0
                new_run_completed = 1 if (was_run_completed or completed) else 0
                new_stars = max(old_stars, clamped_stars)
                attempts = int(existing["attempts"]) + 1

                best_k = existing["best_keystrokes"]
                best_t = existing["best_time_ms"]
                if completed:
                    best_k = keystrokes if best_k is None else min(int(best_k), keystrokes)
                    best_t = time_ms if best_t is None else min(int(best_t), time_ms)
                    if not was_completed:
                        xp_delta = xp_earned
                    elif new_stars > old_stars:
                        xp_delta = max(5, int(xp_earned * (new_stars - old_stars) / 3))

                conn.execute(
                    """
                    UPDATE level_progress
                    SET completed = ?, run_completed = ?, stars = ?, best_keystrokes = ?,
                        best_time_ms = ?, attempts = ?, last_played_at = ?
                    WHERE level_id = ?
                    """,
                    (new_completed, new_run_completed, new_stars, best_k, best_t, attempts, now, level_id),
                )

            if xp_delta > 0:
                conn.execute(
                    "UPDATE player_stats SET total_xp = total_xp + ? WHERE id = 1",
                    (xp_delta,),
                )

            updated = conn.execute(
                "SELECT * FROM level_progress WHERE level_id = ?",
                (level_id,),
            ).fetchone()
            result = dict(updated)
            result["xp_delta"] = xp_delta
            return result

    def get_level_progress(self, level_id: str) -> dict[str, Any] | None:
        """Return stored progress for one level, or None if never played."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM level_progress WHERE level_id = ?",
                (level_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_all_level_progress(self) -> dict[str, dict[str, Any]]:
        """Return a mapping of level_id -> progress dictionary."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM level_progress").fetchall()
            return {row["level_id"]: dict(row) for row in rows}

    def record_command_practice(self, tool: str, command_key: str, success: bool) -> None:
        """Update drill statistics for a specific VIM or TMUX command."""
        now = _utc_now_iso()
        succ_inc = 1 if success else 0
        mist_inc = 0 if success else 1
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO command_stats (tool, command_key, success_count, mistake_count, last_practiced_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tool, command_key) DO UPDATE SET
                    success_count = success_count + excluded.success_count,
                    mistake_count = mistake_count + excluded.mistake_count,
                    last_practiced_at = excluded.last_practiced_at
                """,
                (tool, command_key, succ_inc, mist_inc, now),
            )

    def get_command_stats(self) -> list[dict[str, Any]]:
        """Return all practiced command stats ordered by tool and command."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM command_stats ORDER BY tool, command_key"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_weakest_commands(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return commands sorted by highest mistake rate and mistake count."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *,
                    CAST(mistake_count AS REAL) / MAX(1, success_count + mistake_count) AS error_rate
                FROM command_stats
                WHERE mistake_count > 0 OR success_count > 0
                ORDER BY error_rate DESC, mistake_count DESC, success_count ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_player_stats(self) -> dict[str, Any]:
        """Return aggregated player statistics."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM player_stats WHERE id = 1").fetchone()
            stats = dict(row) if row is not None else {
                "id": 1,
                "total_xp": 0,
                "drills_completed": 0,
                "best_drill_streak": 0,
            }
            agg = conn.execute(
                """
                SELECT
                    COUNT(CASE WHEN completed = 1 THEN 1 END) AS levels_completed,
                    COUNT(CASE WHEN run_completed = 1 THEN 1 END) AS run_levels_completed,
                    COALESCE(SUM(stars), 0) AS total_stars
                FROM level_progress
                """
            ).fetchone()
            stats["levels_completed"] = int(agg["levels_completed"])
            stats["run_levels_completed"] = int(agg["run_levels_completed"])
            stats["total_stars"] = int(agg["total_stars"])
            return stats

    def is_level_run_completed(self, level_id: str) -> bool:
        """Return whether a level has been completed in the current campaign run."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT run_completed FROM level_progress WHERE level_id = ?",
                (level_id,),
            ).fetchone()
            return bool(row["run_completed"]) if row is not None else False

    def are_all_run_levels_completed(self, level_ids: Sequence[str]) -> bool:
        """Return True when every given level ID is completed in the current run."""
        if not level_ids:
            return False
        with self._connect() as conn:
            rows = conn.execute("SELECT level_id, run_completed FROM level_progress").fetchall()
            run_map = {str(r["level_id"]): bool(r["run_completed"]) for r in rows}
            return all(run_map.get(lid, False) for lid in level_ids)

    def set_campaign_level(self, level_id: str) -> None:
        """Persist the active campaign resume level ID."""
        self.set_setting("campaign_level_id", level_id)

    def reset_campaign_run(self) -> None:
        """Reset current campaign run progress while preserving global stars, bests, and XP."""
        with self._connect() as conn:
            conn.execute("UPDATE level_progress SET run_completed = 0")
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('campaign_level_id', '') "
                "ON CONFLICT(key) DO UPDATE SET value = ''"
            )

    def get_campaign_resume_level_id(
        self,
        level_ids: Sequence[str],
        *,
        auto_reset_if_finished: bool = True,
    ) -> str:
        """Return the level ID where the current campaign run should resume.

        If every level in ``level_ids`` has been completed in the current run,
        optionally starts a fresh run (preserving global stars/stats) and returns
        the first level ID.
        """
        if not level_ids:
            raise ValueError("level_ids must not be empty")

        progress = self.get_all_level_progress()
        all_run_done = all(
            bool((progress.get(lid) or {}).get("run_completed"))
            for lid in level_ids
        )
        if all_run_done:
            if auto_reset_if_finished:
                self.reset_campaign_run()
            return level_ids[0]

        saved_id = self.get_setting("campaign_level_id", "") or ""
        if saved_id in level_ids and not bool((progress.get(saved_id) or {}).get("run_completed")):
            return saved_id

        for lid in level_ids:
            if not bool((progress.get(lid) or {}).get("run_completed")):
                return lid
        return level_ids[0]

    def update_drill_stats(self, completed_delta: int, streak: int, xp_delta: int) -> dict[str, Any]:
        """Update drill completion counters, best streak, and XP."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE player_stats
                SET
                    total_xp = total_xp + ?,
                    drills_completed = drills_completed + ?,
                    best_drill_streak = MAX(best_drill_streak, ?)
                WHERE id = 1
                """,
                (xp_delta, completed_delta, streak),
            )
        return self.get_player_stats()

    def reset_all_progress(self) -> None:
        """Clear all campaign progress, command stats, and player stats."""
        with self._connect() as conn:
            conn.execute("DELETE FROM level_progress")
            conn.execute("DELETE FROM command_stats")
            conn.execute(
                "UPDATE player_stats SET total_xp = 0, drills_completed = 0, best_drill_streak = 0 WHERE id = 1"
            )
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('campaign_level_id', '') "
                "ON CONFLICT(key) DO UPDATE SET value = ''"
            )
