"""Right-hand mission HUD widget for gameplay."""

from __future__ import annotations

from rich.text import Text
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from vim_tmux_quest.curriculum.models import Level
from vim_tmux_quest.engine.key_utils import format_key_for_display


class HudWidget(Vertical):
    """Displays mission info, live objective checklist, keystroke tape, and hints."""

    def compose(self):
        with Vertical(classes="hud-section"):
            yield Static("MISSION", classes="hud-title")
            yield Static("", id="hud-description")
        with Vertical(classes="hud-section"):
            yield Static("OBJECTIVES", classes="hud-title")
            yield Static("", id="hud-checklist")
        with Vertical(classes="hud-section"):
            yield Static("KEYSTROKE TAPE", classes="hud-title")
            yield Static("", id="hud-tape")
        with Vertical(id="hint-box", classes="hud-section hidden"):
            yield Static("HINT (Max 2★ if used)", classes="hud-title")
            yield Static("", id="hud-hint-text")
        with Vertical(classes="hud-section", id="hud-controls"):
            yield Static("CONTROLS", classes="hud-title")
            with Horizontal(classes="fn-controls-row"):
                yield Static(
                    "Toggle Hint\n[bold #58a6ff][F1 / Fn+F1][/bold #58a6ff]",
                    classes="fn-control-item",
                )
                yield Static(
                    "Reset Level\n[bold #d29922][F2 / Fn+F2][/bold #d29922]",
                    classes="fn-control-item",
                )
                yield Static(
                    "Exit Level\n[bold #f85149][F3 / Fn+F3][/bold #f85149]",
                    classes="fn-control-item fn-control-last",
                )

    def update_state(
        self,
        level: Level,
        checklist: list[tuple[str, bool]],
        key_history: list[str],
        show_hint: bool,
    ) -> None:
        desc = self.query_one("#hud-description", Static)
        desc.update(f"{level.description}\n\nGoal: {level.objective_text}")

        chk_text = Text()
        for label, done in checklist:
            if done:
                chk_text.append("[✓] ", style="bold #39d353")
                chk_text.append(f"{label}\n", style="#39d353")
            else:
                chk_text.append("[ ] ", style="#8b949e")
                chk_text.append(f"{label}\n", style="#e6edf3")
        self.query_one("#hud-checklist", Static).update(chk_text)

        recent = [format_key_for_display(k) for k in key_history[-10:]]
        tape = " ".join(f"[{k}]" for k in recent) if recent else "(waiting for input...)"
        self.query_one("#hud-tape", Static).update(tape)

        hint_box = self.query_one("#hint-box", Vertical)
        self.query_one("#hud-hint-text", Static).update(level.hint)
        if show_hint:
            hint_box.remove_class("hidden")
        else:
            hint_box.add_class("hidden")
