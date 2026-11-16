"""Async TUI integration tests using Textual's Pilot."""

import asyncio
from pathlib import Path

from vim_tmux_quest.curriculum.drills import DRILL_BANK
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
