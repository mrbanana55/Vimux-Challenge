"""Modal dialogs for level completion and confirmations."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from vim_tmux_quest.curriculum.models import Level


class LevelCompleteModal(ModalScreen[str]):
    """Displays level completion summary, star rating, and next actions."""

    def __init__(
        self,
        level: Level,
        stars: int,
        keystrokes: int,
        time_ms: int,
        xp_gained: int,
        has_next_level: bool,
    ) -> None:
        super().__init__()
        self.level = level
        self.stars = stars
        self.keystrokes = keystrokes
        self.time_ms = time_ms
        self.xp_gained = xp_gained
        self.has_next_level = has_next_level

    def compose(self):
        star_str = "★" * self.stars + "☆" * (3 - self.stars)
        secs = self.time_ms / 1000.0
        with Vertical(classes="modal-overlay"):
            with Vertical(classes="modal-box"):
                yield Static(f"LEVEL COMPLETE!  {star_str}", classes="modal-title", markup=False)
                yield Static(
                    f"Level: {self.level.title}\n"
                    f"Keystrokes: {self.keystrokes}  (Par: {self.level.par_keystrokes})\n"
                    f"Time: {secs:.1f}s   |   XP Gained: +{self.xp_gained}\n\n"
                    f"Optimal Solution:\n  {self.level.optimal_solution}",
                    id="modal-summary",
                    markup=False,
                )
                with Horizontal(classes="modal-buttons"):
                    if self.has_next_level:
                        yield Button(Text("Next Level [n]"), variant="success", id="btn-next")
                    yield Button(Text("Retry [r]"), variant="primary", id="btn-retry")
                    yield Button(Text("Level Select [m]"), id="btn-menu")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            self.dismiss("next")
        elif event.button.id == "btn-retry":
            self.dismiss("retry")
        else:
            self.dismiss("menu")

    def on_key(self, event: events.Key) -> None:
        if event.key in ("n", "enter") and self.has_next_level:
            event.stop()
            self.dismiss("next")
        elif event.key == "r":
            event.stop()
            self.dismiss("retry")
        elif event.key in ("escape", "m"):
            event.stop()
            self.dismiss("menu")


class ConfirmModal(ModalScreen[bool]):
    """Simple Yes/No confirmation modal."""

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self):
        with Vertical(classes="modal-overlay"):
            with Vertical(classes="modal-box"):
                yield Static(self._title, classes="modal-title", markup=False)
                yield Static(self._message, markup=False)
                with Horizontal(classes="modal-buttons"):
                    yield Button(Text("Confirm [y]"), variant="error", id="btn-yes")
                    yield Button(Text("Cancel [n]"), variant="primary", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")

    def on_key(self, event: events.Key) -> None:
        if event.key == "y":
            event.stop()
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            event.stop()
            self.dismiss(False)
