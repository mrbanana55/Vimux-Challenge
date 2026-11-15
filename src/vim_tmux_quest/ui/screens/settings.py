"""Settings, weak-command diagnostics, and progress reset screen."""

from __future__ import annotations

from textual import events
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from vim_tmux_quest.ui.widgets.modals import ConfirmModal


class SettingsScreen(Screen):
    """Configure TMUX prefix, default hint behavior, and inspect/reset saved data."""

    def compose(self):
        yield Static("SETTINGS & SAVED PROGRESS", classes="screen-header")
        with Vertical(classes="settings-card"):
            yield Static("", id="settings-db-path")
            with Horizontal(classes="settings-row"):
                yield Button("Toggle TMUX Prefix (Ctrl-b / Ctrl-a)", id="btn-prefix", variant="primary")
            with Horizontal(classes="settings-row"):
                yield Button("Toggle Default Hints (Off / On)", id="btn-hints", variant="primary")
            yield Static("", id="settings-weak-title")
            yield Static("", id="settings-weak-list")
            with Horizontal(classes="settings-row"):
                yield Button("Reset All Progress", id="btn-reset", variant="error")
                yield Button("Back [Esc]", id="btn-back", variant="default")
        yield Static("Enter: Activate | Esc/q: Back to Main Menu", classes="footer-bar")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        db = self.app.db  # type: ignore[attr-defined]
        prefix = db.get_setting("tmux_prefix", "ctrl+b")
        hints = db.get_setting("show_hints", "0") == "1"
        self.query_one("#settings-db-path", Static).update(
            f"Database Path: {db.db_path}\n"
            f"TMUX Prefix Key: {prefix}\n"
            f"Show Hints Automatically: {'ON' if hints else 'OFF'}\n"
        )
        weak = db.get_weakest_commands(limit=5)
        self.query_one("#settings-weak-title", Static).update("\nMost Practiced / Weakest Drill Commands:")
        if not weak:
            self.query_one("#settings-weak-list", Static).update("  (No drill data recorded yet.)\n")
        else:
            lines = []
            for row in weak:
                lines.append(
                    f"  - [{row['tool'].upper()}] {row['command_key']}: "
                    f"{row['success_count']} ok / {row['mistake_count']} mistakes"
                )
            self.query_one("#settings-weak-list", Static).update("\n".join(lines) + "\n")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        db = self.app.db  # type: ignore[attr-defined]
        bid = event.button.id
        if bid == "btn-prefix":
            cur = db.get_setting("tmux_prefix", "ctrl+b")
            nxt = "ctrl+a" if cur == "ctrl+b" else "ctrl+b"
            db.set_setting("tmux_prefix", nxt)
            self._refresh()
        elif bid == "btn-hints":
            cur = db.get_setting("show_hints", "0")
            nxt = "0" if cur == "1" else "1"
            db.set_setting("show_hints", nxt)
            self._refresh()
        elif bid == "btn-reset":
            def _on_confirm(confirmed: bool | None) -> None:
                if confirmed:
                    db.reset_all_progress()
                    self._refresh()

            self.app.push_screen(
                ConfirmModal(
                    "Reset All Progress?",
                    "This will permanently erase all completed levels, stars, XP, and drill stats.",
                ),
                callback=_on_confirm,
            )
        elif bid == "btn-back":
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "q"):
            event.stop()
            self.app.pop_screen()
