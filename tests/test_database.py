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
