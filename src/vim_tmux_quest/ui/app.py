"""Main Textual application class for VIM & TMUX Quest."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("TEXTUAL_DISABLE_KITTY_KEY", "1")

import textual.constants
from textual.app import App

textual.constants.DISABLE_KITTY_KEY = True  # type: ignore[misc]

from vim_tmux_quest.db.database import Database
from vim_tmux_quest.ui.screens.main_menu import MainMenuScreen


class VimTmuxQuestApp(App):
    """Interactive terminal game and tutorial for mastering VIM and TMUX."""

    TITLE = "Vimux Challenge"
    CSS_PATH = Path(__file__).parent / "styles.tcss"

    def __init__(self, db_path: Path | str | None = None) -> None:
        super().__init__()
        self.db = Database(db_path=db_path)

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())
