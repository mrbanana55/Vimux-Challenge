"""Unit tests for the SQLite persistence layer."""

from pathlib import Path

from vim_tmux_quest.db.database import Database


def test_database_settings_and_progress(tmp_path: Path):
    db_file = tmp_path / "test_progress.db"
    db = Database(db_path=db_file)

    assert db.get_setting("tmux_prefix") == "ctrl+b"
    db.set_setting("tmux_prefix", "ctrl+a")
    assert db.get_setting("tmux_prefix") == "ctrl+a"

    res1 = db.record_level_attempt("vim_1_1", completed=True, keystrokes=12, time_ms=4200, stars=2, xp_earned=50)
    assert res1["completed"] == 1
    assert res1["stars"] == 2
    assert res1["best_keystrokes"] == 12
    assert res1["xp_delta"] == 50

    # Better run updates stars and lowers best_keystrokes
    res2 = db.record_level_attempt("vim_1_1", completed=True, keystrokes=8, time_ms=2500, stars=3, xp_earned=50)
    assert res2["stars"] == 3
    assert res2["best_keystrokes"] == 8
    assert res2["best_time_ms"] == 2500
    assert res2["attempts"] == 2
    assert res2["xp_delta"] > 0

    # Worse run preserves bests
    res3 = db.record_level_attempt("vim_1_1", completed=True, keystrokes=20, time_ms=9000, stars=1, xp_earned=50)
    assert res3["stars"] == 3
    assert res3["best_keystrokes"] == 8
    assert res3["xp_delta"] == 0

    stats = db.get_player_stats()
    assert stats["levels_completed"] == 1
    assert stats["total_stars"] == 3
    assert stats["total_xp"] == res1["xp_delta"] + res2["xp_delta"]


def test_command_stats_weakest_and_reset(tmp_path: Path):
    db = Database(db_path=tmp_path / "drills.db")
    db.record_command_practice("vim", "vim_ciw", True)
    db.record_command_practice("vim", "vim_ciw", True)
    db.record_command_practice("tmux", "tmux_split_v", False)
    db.record_command_practice("tmux", "tmux_split_v", False)
    db.record_command_practice("tmux", "tmux_split_v", True)

    weak = db.get_weakest_commands(limit=5)
    assert weak[0]["command_key"] == "tmux_split_v"

    db.update_drill_stats(completed_delta=3, streak=3, xp_delta=35)
    stats = db.get_player_stats()
    assert stats["drills_completed"] == 3
    assert stats["best_drill_streak"] == 3
    assert stats["total_xp"] >= 35

    db.reset_all_progress()
    stats_after = db.get_player_stats()
    assert stats_after["total_xp"] == 0
    assert stats_after["levels_completed"] == 0
    assert db.get_command_stats() == []


def test_campaign_replay_preserves_new_run_and_global_stars(tmp_path: Path):
    db = Database(db_path=tmp_path / "replay.db")
    level_ids = ["vim_1_1", "vim_1_2", "vim_1_3", "vim_1_4"]

    # Complete all levels with 3 stars in first run
    for lid in level_ids:
        db.record_level_attempt(lid, completed=True, keystrokes=5, time_ms=1000, stars=3, xp_earned=50)

    assert db.are_all_run_levels_completed(level_ids) is True
    # Starting next campaign run goes back to level 1 without losing global stars/XP
    assert db.get_campaign_resume_level_id(level_ids) == "vim_1_1"
    stats = db.get_player_stats()
    assert stats["levels_completed"] == 4
    assert stats["total_stars"] == 12
    assert stats["total_xp"] == 200

    # Replay level 1 with worse performance (1 star), advance to level 2, quit on level 3
    db.set_campaign_level("vim_1_1")
    db.record_level_attempt("vim_1_1", completed=True, keystrokes=25, time_ms=9000, stars=1, xp_earned=50)
    db.set_campaign_level("vim_1_2")
    db.record_level_attempt("vim_1_2", completed=True, keystrokes=20, time_ms=8000, stars=2, xp_earned=50)
    db.set_campaign_level("vim_1_3")

    # Reopening DB resumes at level 3 (not level 1!) and keeps global 3 stars & best keystrokes
    db_reopened = Database(db_path=tmp_path / "replay.db")
    assert db_reopened.get_campaign_resume_level_id(level_ids) == "vim_1_3"

    p1 = db_reopened.get_level_progress("vim_1_1")
    assert p1 is not None
    assert p1["stars"] == 3
    assert p1["best_keystrokes"] == 5
    assert p1["completed"] == 1
    assert p1["run_completed"] == 1

    stats_after = db_reopened.get_player_stats()
    assert stats_after["levels_completed"] == 4
    assert stats_after["total_stars"] == 12
    assert stats_after["total_xp"] == 200


def test_legacy_db_migration_preserves_mid_campaign_and_completed_campaign(tmp_path: Path):
    import sqlite3

    # Legacy DB halfway through campaign (no run_completed column)
    mid_path = tmp_path / "legacy_mid.db"
    with sqlite3.connect(mid_path) as conn:
        conn.executescript(
            """
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE level_progress (
                level_id TEXT PRIMARY KEY,
                completed INTEGER NOT NULL DEFAULT 0,
                stars INTEGER NOT NULL DEFAULT 0,
                best_keystrokes INTEGER,
                best_time_ms INTEGER,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_played_at TEXT
            );
            CREATE TABLE command_stats (
                tool TEXT NOT NULL,
                command_key TEXT NOT NULL,
                success_count INTEGER NOT NULL DEFAULT 0,
                mistake_count INTEGER NOT NULL DEFAULT 0,
                last_practiced_at TEXT,
                PRIMARY KEY (tool, command_key)
            );
            CREATE TABLE player_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_xp INTEGER NOT NULL DEFAULT 0,
                drills_completed INTEGER NOT NULL DEFAULT 0,
                best_drill_streak INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO player_stats (id, total_xp, drills_completed, best_drill_streak) VALUES (1, 100, 0, 0);
            INSERT INTO level_progress (level_id, completed, stars, best_keystrokes, best_time_ms, attempts)
            VALUES ('vim_1_1', 1, 3, 9, 1000, 1), ('vim_1_2', 1, 2, 6, 1200, 1);
            """
        )

    db_mid = Database(db_path=mid_path)
    assert db_mid.get_campaign_resume_level_id(["vim_1_1", "vim_1_2", "vim_1_3"]) == "vim_1_3"

    # Legacy DB with all levels completed
    full_path = tmp_path / "legacy_full.db"
    with sqlite3.connect(full_path) as conn:
        conn.executescript(
            """
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE level_progress (
                level_id TEXT PRIMARY KEY,
                completed INTEGER NOT NULL DEFAULT 0,
                stars INTEGER NOT NULL DEFAULT 0,
                best_keystrokes INTEGER,
                best_time_ms INTEGER,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_played_at TEXT
            );
            CREATE TABLE command_stats (
                tool TEXT NOT NULL,
                command_key TEXT NOT NULL,
                success_count INTEGER NOT NULL DEFAULT 0,
                mistake_count INTEGER NOT NULL DEFAULT 0,
                last_practiced_at TEXT,
                PRIMARY KEY (tool, command_key)
            );
            CREATE TABLE player_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_xp INTEGER NOT NULL DEFAULT 0,
                drills_completed INTEGER NOT NULL DEFAULT 0,
                best_drill_streak INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO player_stats (id, total_xp, drills_completed, best_drill_streak) VALUES (1, 150, 0, 0);
            INSERT INTO level_progress (level_id, completed, stars, best_keystrokes, best_time_ms, attempts)
            VALUES ('vim_1_1', 1, 3, 9, 1000, 1), ('vim_1_2', 1, 2, 6, 1200, 1);
            """
        )

    db_full = Database(db_path=full_path)
    assert db_full.get_campaign_resume_level_id(["vim_1_1", "vim_1_2"]) == "vim_1_1"
    assert db_full.get_player_stats()["total_stars"] == 5
    assert db_full.get_player_stats()["levels_completed"] == 2
