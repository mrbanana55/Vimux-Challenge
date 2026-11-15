"""Level selector screen grouped by curriculum track."""

from __future__ import annotations

from textual import events
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from vim_tmux_quest.curriculum import TRACKS, get_all_levels
from vim_tmux_quest.curriculum.models import Level


class LevelSelectScreen(Screen):
    """Browse all 4 curriculum tracks and launch any level."""

    def __init__(self) -> None:
        super().__init__()
        self._selected_track: int = 0  # 0 = All
        self._visible_levels: list[Level] = []

    def compose(self):
        yield Static("CAMPAIGN LEVEL SELECT — 4 Tracks, 28 Levels", classes="screen-header")
        with Horizontal(id="track-tabs"):
            yield Button("All Tracks", id="track-0", variant="success", classes="track-btn")
            for t in TRACKS:
                yield Button(f"Track {t.id}: {t.name}", id=f"track-{t.id}", classes="track-btn")
        yield OptionList(id="level-list")
        yield Static("Enter: Play Level | 0-4: Filter Track | j/k: Navigate | Esc/q: Back", classes="footer-bar")

    def on_mount(self) -> None:
        self._populate_levels()
        self.query_one("#level-list", OptionList).focus()

    def on_screen_resume(self) -> None:
        self._populate_levels()

    def _populate_levels(self) -> None:
        all_levels = get_all_levels()
        progress = self.app.db.get_all_level_progress()  # type: ignore[attr-defined]
        ol = self.query_one("#level-list", OptionList)
        ol.clear_options()
        self._visible_levels = []

        for lvl in all_levels:
            if self._selected_track != 0 and lvl.track_id != self._selected_track:
                continue
            row = progress.get(lvl.id)
            if row and row["completed"]:
                stars = int(row["stars"])
                star_txt = "★" * stars + "☆" * (3 - stars)
                best_k = row["best_keystrokes"]
                meta = f"Best: {best_k} / Par: {lvl.par_keystrokes}"
            else:
                star_txt = "☆☆☆"
                meta = f"Par: {lvl.par_keystrokes}"
            label = f"[{star_txt}] T{lvl.track_id}.{lvl.number}  {lvl.title:<38} ({lvl.mode.upper():<5})  {meta}"
            ol.add_option(Option(label, id=lvl.id))
            self._visible_levels.append(lvl)

        for tid in [0, 1, 2, 3, 4]:
            btn = self.query_one(f"#track-{tid}", Button)
            btn.variant = "success" if tid == self._selected_track else "default"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("track-"):
            self._selected_track = int(bid.split("-")[1])
            self._populate_levels()
            self.query_one("#level-list", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        from vim_tmux_quest.ui.screens.game_screen import GameScreen

        if event.option.id:
            self.app.push_screen(GameScreen(str(event.option.id)))

    def on_key(self, event: events.Key) -> None:
        ol = self.query_one("#level-list", OptionList)
        if event.key in ("escape", "q"):
            event.stop()
            self.app.pop_screen()
        elif event.key in ("0", "1", "2", "3", "4"):
            event.stop()
            self._selected_track = int(event.key)
            self._populate_levels()
            ol.focus()
        elif event.key == "j":
            ol.action_cursor_down()
        elif event.key == "k":
            ol.action_cursor_up()
