"""Main menu screen."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from vim_tmux_quest.curriculum import get_all_levels

BANNER = r"""
 __     _____ __  __ _   ___  __   ____ _   _    _    _     _     _____ _   _  ____ _____
 \ \   / /_ _|  \/  | | | \ \/ /  / ___| | | |  / \  | |   | |   | ____| \ | |/ ___| ____|
  \ \ / / | || |\/| | | | |\  /  | |   | |_| | / _ \ | |   | |   |  _| |  \| | |  _|  _|
   \ V /  | || |  | | |_| |/  \  | |___|  _  |/ ___ \| |___| |___| |___| |\  | |_| | |___
    \_/  |___|_|  |_|\___//_/\_\  \____|_| |_/_/   \_\_____|_____|_____|_| \_|\____|_____|
"""


class MainMenuScreen(Screen):
    """Main landing screen with campaign continuation and navigation."""

    def compose(self):
        yield Static(BANNER, classes="banner", markup=False)
        yield Static(
            "Master VIM motions & TMUX commands inside an interactive terminal simulator",
            classes="subtitle",
        )
        yield Static("", id="main-stats", classes="stats-bar", markup=False)
        with Center():
            with Vertical(classes="menu-container"):
                yield Button(Text("[1] Continue Campaign"), variant="success", id="btn-continue", classes="menu-btn")
                yield Button(Text("[2] Level Select (4 Tracks)"), variant="primary", id="btn-levels", classes="menu-btn")
                yield Button(Text("[3] Practice & Speed Drills"), variant="primary", id="btn-drills", classes="menu-btn")
                yield Button(Text("[4] Command Cheat Sheet"), variant="default", id="btn-cheatsheet", classes="menu-btn")
                yield Button(Text("[5] Settings & Progress"), variant="default", id="btn-settings", classes="menu-btn")
                yield Button(Text("[6] Help & Controls (About / Fn Keys)"), variant="default", id="btn-help", classes="menu-btn")
                yield Button(Text("[q] Quit"), variant="error", id="btn-quit", classes="menu-btn")
        yield Static("Keys: [1-6] Quick Launch | j/k or Arrows: Move | Enter: Select | q: Quit", classes="footer-bar", markup=False)

    def on_mount(self) -> None:
        self._refresh_stats()

    def on_screen_resume(self) -> None:
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        db = self.app.db  # type: ignore[attr-defined]
        stats = db.get_player_stats()
        levels = get_all_levels()
        level_ids = [lvl.id for lvl in levels]
        resume_id = db.get_campaign_resume_level_id(level_ids)
        resume_lvl = next((lvl for lvl in levels if lvl.id == resume_id), levels[0])
        progress = db.get_all_level_progress()
        run_done = sum(
            1 for lvl in levels
            if bool((progress.get(lvl.id) or {}).get("run_completed"))
        )

        max_stars = len(levels) * 3
        prefix = db.get_setting("tmux_prefix", "ctrl+b")
        summary = (
            f"XP: {stats['total_xp']}   |   "
            f"Levels: {stats['levels_completed']}/{len(levels)}   |   "
            f"Stars: {stats['total_stars']}/{max_stars}   |   "
            f"Drills: {stats['drills_completed']} (Best Streak: {stats['best_drill_streak']})   |   "
            f"TMUX Prefix: {prefix}"
        )
        self.query_one("#main-stats", Static).update(summary)

        tag = f"T{resume_lvl.track_id}.{resume_lvl.number}"
        if stats["levels_completed"] >= len(levels):
            if run_done > 0:
                btn_label = f"[1] Continue Campaign ({tag} | Run {run_done}/{len(levels)})"
            else:
                btn_label = f"[1] Continue Campaign ({tag} | New Run)"
        else:
            btn_label = f"[1] Continue Campaign ({tag})"
        self.query_one("#btn-continue", Button).label = Text(btn_label)

    def _continue_campaign(self) -> None:
        from vim_tmux_quest.ui.screens.game_screen import GameScreen

        levels = get_all_levels()
        level_ids = [lvl.id for lvl in levels]
        target_id = self.app.db.get_campaign_resume_level_id(level_ids)  # type: ignore[attr-defined]
        self.app.push_screen(GameScreen(target_id, campaign_mode=True))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from vim_tmux_quest.ui.screens.cheatsheet import CheatSheetScreen
        from vim_tmux_quest.ui.screens.drill_screen import DrillScreen
        from vim_tmux_quest.ui.screens.help_screen import HelpScreen
        from vim_tmux_quest.ui.screens.level_select import LevelSelectScreen
        from vim_tmux_quest.ui.screens.settings import SettingsScreen

        bid = event.button.id
        if bid == "btn-continue":
            self._continue_campaign()
        elif bid == "btn-levels":
            self.app.push_screen(LevelSelectScreen())
        elif bid == "btn-drills":
            self.app.push_screen(DrillScreen())
        elif bid == "btn-cheatsheet":
            self.app.push_screen(CheatSheetScreen())
        elif bid == "btn-settings":
            self.app.push_screen(SettingsScreen())
        elif bid == "btn-help":
            self.app.push_screen(HelpScreen())
        elif bid == "btn-quit":
            self.app.exit()

    def on_key(self, event: events.Key) -> None:
        from vim_tmux_quest.ui.screens.cheatsheet import CheatSheetScreen
        from vim_tmux_quest.ui.screens.drill_screen import DrillScreen
        from vim_tmux_quest.ui.screens.help_screen import HelpScreen
        from vim_tmux_quest.ui.screens.level_select import LevelSelectScreen
        from vim_tmux_quest.ui.screens.settings import SettingsScreen

        if event.key == "1":
            self._continue_campaign()
        elif event.key == "2":
            self.app.push_screen(LevelSelectScreen())
        elif event.key == "3":
            self.app.push_screen(DrillScreen())
        elif event.key == "4":
            self.app.push_screen(CheatSheetScreen())
        elif event.key == "5":
            self.app.push_screen(SettingsScreen())
        elif event.key == "6":
            self.app.push_screen(HelpScreen())
        elif event.key == "q":
            self.app.exit()
        elif event.key == "j":
            self.focus_next()
        elif event.key == "k":
            self.focus_previous()
