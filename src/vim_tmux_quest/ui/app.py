"""Main Textual application class for VIM & TMUX Quest."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

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
