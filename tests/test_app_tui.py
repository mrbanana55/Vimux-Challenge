"""Async TUI integration tests using Textual's Pilot."""

import asyncio
from pathlib import Path

from vim_tmux_quest.curriculum import get_all_levels
from vim_tmux_quest.curriculum.drills import DRILL_BANK
from vim_tmux_quest.db.database import Database
from vim_tmux_quest.ui.app import VimTmuxQuestApp
from vim_tmux_quest.ui.screens.cheatsheet import CheatSheetScreen
from vim_tmux_quest.ui.screens.drill_screen import DrillScreen
from vim_tmux_quest.ui.screens.game_screen import GameScreen
from vim_tmux_quest.ui.screens.help_screen import HelpScreen
from vim_tmux_quest.ui.screens.level_select import LevelSelectScreen
from vim_tmux_quest.ui.screens.main_menu import MainMenuScreen
from vim_tmux_quest.ui.screens.settings import SettingsScreen
from vim_tmux_quest.ui.widgets.modals import LevelCompleteModal


def test_tui_navigation_and_gameplay(tmp_path: Path):
    async def _run() -> None:
        db_path = tmp_path / "tui.db"
        app = VimTmuxQuestApp(db_path=db_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, MainMenuScreen)

            # Open Level Select via hotkey 2
            await pilot.press("2")
            await pilot.pause()
            assert isinstance(app.screen, LevelSelectScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, MainMenuScreen)

            # Open Drills via hotkey 3
            await pilot.press("3")
            await pilot.pause()
            assert isinstance(app.screen, DrillScreen)
            await pilot.press("f3")
            await pilot.pause()
            assert isinstance(app.screen, MainMenuScreen)

            # Open Cheat Sheet via hotkey 4
            await pilot.press("4")
            await pilot.pause()
            assert isinstance(app.screen, CheatSheetScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, MainMenuScreen)

            # Open Settings via hotkey 5
            await pilot.press("5")
            await pilot.pause()
            assert isinstance(app.screen, SettingsScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, MainMenuScreen)

            # Open Help & Controls via hotkey 6
            await pilot.press("6")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, MainMenuScreen)

            # Launch Level 1 via hotkey 1 and solve it
            await pilot.press("1")
            await pilot.pause()
            assert isinstance(app.screen, GameScreen)
            assert app.screen.level.id == "vim_1_1"

            for key in ["j", "j", "j", "l", "l", "l", "l", "l", "l"]:
                await pilot.press(key)
            await pilot.pause()
            assert isinstance(app.screen, LevelCompleteModal)

            # Advance to Level 2 (vim_1_2)
            await pilot.press("n")
            await pilot.pause()
            assert isinstance(app.screen, GameScreen)
            assert app.screen.level.id == "vim_1_2"

            # Verify persistence in DB
            prog = app.db.get_level_progress("vim_1_1")
            assert prog is not None
            assert prog["completed"] == 1
            assert prog["stars"] == 3

    asyncio.run(_run())


def test_tui_tmux_level_execution(tmp_path: Path):
    async def _run() -> None:
        db_path = tmp_path / "tui_tmux.db"
        app = VimTmuxQuestApp(db_path=db_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(GameScreen("tmux_3_1"))
            await pilot.pause()
            assert isinstance(app.screen, GameScreen)

            await pilot.press("ctrl+b")
            await pilot.press("%")
            await pilot.pause()
            assert isinstance(app.screen, LevelCompleteModal)
            prog = app.db.get_level_progress("tmux_3_1")
            assert prog is not None and prog["completed"] == 1

    asyncio.run(_run())


def test_tui_vim_1_4_uppercase_and_5g_with_modifiers(tmp_path: Path):
    async def _run() -> None:
        db_path = tmp_path / "tui_vim_1_4.db"
        app = VimTmuxQuestApp(db_path=db_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(GameScreen("vim_1_4"))
            await pilot.pause()
            assert isinstance(app.screen, GameScreen)

            for key in ["left_shift", "G", "g", "g", "5", "left_shift", "caps_lock", "G"]:
                await pilot.press(key)
            await pilot.pause()

            assert isinstance(app.screen, LevelCompleteModal)
            prog = app.db.get_level_progress("vim_1_4")
            assert prog is not None
            assert prog["completed"] == 1
            assert prog["best_keystrokes"] == 5

    asyncio.run(_run())


def test_tui_drill_screen_ignores_modifier_keys(tmp_path: Path):
    async def _run() -> None:
        db_path = tmp_path / "tui_drill.db"
        app = VimTmuxQuestApp(db_path=db_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            drill_screen = DrillScreen()
            await app.push_screen(drill_screen)
            await pilot.pause()
            assert isinstance(app.screen, DrillScreen)

            drill_screen.current_drill = next(d for d in DRILL_BANK if d.id == "vim_file_bot")
            drill_screen.typed_keys = []
            drill_screen.had_mistake = False
            drill_screen._refresh_view()

            await pilot.press("left_shift", "caps_lock", "shift+g")
            await pilot.pause()

            assert drill_screen.session_done == 1
            assert drill_screen.session_correct == 1
            assert drill_screen.streak == 1

    asyncio.run(_run())


def test_tui_slash_and_bracket_keys_do_not_raise_markup_error(tmp_path: Path):
    async def _run() -> None:
        db_path = tmp_path / "tui_markup.db"
        app = VimTmuxQuestApp(db_path=db_path)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Test GameScreen("vim_2_6") with '/', '[', ']', and then solving the level
            await app.push_screen(GameScreen("vim_2_6"))
            await pilot.pause()
            assert isinstance(app.screen, GameScreen)

            for key in ["/", "[", "]", "escape"]:
                await pilot.press(key)
            await pilot.pause()

            for key in ["A", ";", "escape", "j", ".", "j", ".", "j", "."]:
                await pilot.press(key)
            await pilot.pause()

            assert isinstance(app.screen, LevelCompleteModal)
            prog = app.db.get_level_progress("vim_2_6")
            assert prog is not None and prog["completed"] == 1

            # Return from modal/game and test DrillScreen with '/', '[', ']', 'escape'
            await pilot.press("m")
            await pilot.pause()

            drill_screen = DrillScreen()
            await app.push_screen(drill_screen)
            await pilot.pause()
            assert isinstance(app.screen, DrillScreen)

            for key in ["/", "[", "]", "escape"]:
                await pilot.press(key)
            await pilot.pause()
            assert isinstance(app.screen, DrillScreen)

    asyncio.run(_run())


def test_tui_replay_after_completing_all_levels_resumes_new_run_and_keeps_stars(tmp_path: Path):
    async def _run() -> None:
        db_path = tmp_path / "tui_replay.db"
        seed_db = Database(db_path=db_path)
        all_levels = get_all_levels()
        for lvl in all_levels:
            seed_db.record_level_attempt(
                lvl.id,
                completed=True,
                keystrokes=lvl.par_keystrokes,
                time_ms=1000,
                stars=3,
                xp_earned=lvl.xp_reward,
            )

        # Session 1: all levels were completed; Continue Campaign starts at T1.1
        app1 = VimTmuxQuestApp(db_path=db_path)
        async with app1.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app1.screen, MainMenuScreen)
            assert app1.db.get_player_stats()["levels_completed"] == len(all_levels)
            assert app1.db.get_player_stats()["total_stars"] == len(all_levels) * 3

            await pilot.press("1")
            await pilot.pause()
            assert isinstance(app1.screen, GameScreen)
            assert app1.screen.level.id == "vim_1_1"

            # Solve vim_1_1 with extra keystrokes (would only earn 1 star) and advance to vim_1_2
            for key in ["l", "h", "j", "j", "j", "l", "l", "l", "l", "l", "l"]:
                await pilot.press(key)
            await pilot.pause()
            assert isinstance(app1.screen, LevelCompleteModal)

            await pilot.press("n")
            await pilot.pause()
            assert isinstance(app1.screen, GameScreen)
            assert app1.screen.level.id == "vim_1_2"

            # Exit mid-level (F3) and quit app
            await pilot.press("f3")
            await pilot.pause()
            assert isinstance(app1.screen, MainMenuScreen)

        # Session 2: reopen and Continue Campaign -> must resume at vim_1_2 (not vim_1_1!)
        app2 = VimTmuxQuestApp(db_path=db_path)
        async with app2.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app2.screen, MainMenuScreen)

            # Global stars & completed count are preserved
            prog_1_1 = app2.db.get_level_progress("vim_1_1")
            assert prog_1_1 is not None
            assert prog_1_1["stars"] == 3
            assert app2.db.get_player_stats()["levels_completed"] == len(all_levels)
            assert app2.db.get_player_stats()["total_stars"] == len(all_levels) * 3

            await pilot.press("1")
            await pilot.pause()
            assert isinstance(app2.screen, GameScreen)
            assert app2.screen.level.id == "vim_1_2"

    asyncio.run(_run())


def test_tui_settings_restart_campaign_run_keeps_stars(tmp_path: Path):
    async def _run() -> None:
        db_path = tmp_path / "tui_reset_run.db"
        seed_db = Database(db_path=db_path)
        seed_db.record_level_attempt("vim_1_1", completed=True, keystrokes=9, time_ms=1000, stars=3, xp_earned=50)
        seed_db.record_level_attempt("vim_1_2", completed=True, keystrokes=4, time_ms=1000, stars=3, xp_earned=50)

        app = VimTmuxQuestApp(db_path=db_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("5")
            await pilot.pause()
            assert isinstance(app.screen, SettingsScreen)

            await pilot.click("#btn-reset-run")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, MainMenuScreen)

            # Global stats remain intact, but Continue Campaign starts at vim_1_1
            assert app.db.get_player_stats()["levels_completed"] == 2
            assert app.db.get_player_stats()["total_stars"] == 6
            await pilot.press("1")
            await pilot.pause()
            assert isinstance(app.screen, GameScreen)
            assert app.screen.level.id == "vim_1_1"

    asyncio.run(_run())
