"""Practice & speed-drill flashcard screen."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from vim_tmux_quest.curriculum.drills import select_next_drill
from vim_tmux_quest.curriculum.models import DrillItem
from vim_tmux_quest.engine.key_utils import format_key_for_display, normalize_key

FILTER_CYCLE = ["all", "vim", "tmux", "weak"]
FILTER_LABELS = {
    "all": "All Commands",
    "vim": "VIM Only",
    "tmux": "TMUX Only",
    "weak": "Weakest Commands",
}


class DrillScreen(Screen):
    """Rapid-fire command recall & muscle memory drill mode."""

    def __init__(self) -> None:
        super().__init__()
        self.tool_filter: str = "all"
        self.current_drill: DrillItem | None = None
        self.typed_keys: list[str] = []
        self.streak: int = 0
        self.session_done: int = 0
        self.session_correct: int = 0
        self.had_mistake: bool = False
        self.feedback_msg: str = ""
        self.feedback_style: str = "#8b949e"

    def compose(self):
        yield Static("PRACTICE & SPEED DRILLS", classes="screen-header")
        with Vertical(id="drill-card"):
            yield Static("", id="drill-meta")
            yield Static("", id="drill-prompt")
            yield Static("", id="drill-typed")
            yield Static("", id="drill-feedback")
            with Horizontal(classes="fn-controls-row"):
                yield Static(
                    "Switch Filter\n[bold #58a6ff][F1 / Fn+F1][/bold #58a6ff]",
                    classes="fn-control-item",
                )
                yield Static(
                    "Reveal Answer\n[bold #d29922][F2 / Fn+F2][/bold #d29922]",
                    classes="fn-control-item",
                )
                yield Static(
                    "Exit Drills\n[bold #f85149][F3 / Fn+F3][/bold #f85149]",
                    classes="fn-control-item fn-control-last",
                )
        yield Static("[F1] Switch Filter (All/VIM/TMUX/Weak)   [F2] Reveal Answer   [F3] Back to Menu", classes="footer-bar")

    def on_mount(self) -> None:
        self._load_next_drill()

    def _display_answer_for_user(self, item: DrillItem) -> str:
        prefix = self.app.db.get_setting("tmux_prefix", "ctrl+b") or "ctrl+b"  # type: ignore[attr-defined]
        pretty_prefix = "Ctrl-a" if prefix.lower() == "ctrl+a" else "Ctrl-b"
        return item.display_answer.replace("Prefix", pretty_prefix)

    def _load_next_drill(self) -> None:
        exclude = self.current_drill.id if self.current_drill else None
        self.current_drill = select_next_drill(
            self.app.db,  # type: ignore[attr-defined]
            tool_filter=self.tool_filter,
            exclude_id=exclude,
        )
        self.typed_keys = []
        self.had_mistake = False
        self._refresh_view()

    def _refresh_view(self) -> None:
        item = self.current_drill
        if item is None:
            return
        acc = int((self.session_correct / self.session_done) * 100) if self.session_done else 100
        meta = (
            f"Filter: {FILTER_LABELS[self.tool_filter]}   |   "
            f"Tool: {item.tool.upper()} ({item.category})   |   "
            f"Streak: {self.streak}   |   Session: {self.session_correct}/{self.session_done} ({acc}%)"
        )
        self.query_one("#drill-meta", Static).update(meta)
        self.query_one("#drill-prompt", Static).update(item.prompt)

        typed_str = (
            " ".join(f"[{format_key_for_display(k)}]" for k in self.typed_keys)
            if self.typed_keys
            else "(type the command keys now...)"
        )
        self.query_one("#drill-typed", Static).update(typed_str)

        fb = Text()
        if self.feedback_msg:
            fb.append(self.feedback_msg, style=self.feedback_style)
        else:
            fb.append("Type the exact key sequence from memory.", style="#8b949e")
        self.query_one("#drill-feedback", Static).update(fb)

    def on_key(self, event: events.Key) -> None:
        if event.key == "f1":
            event.stop()
            event.prevent_default()
            idx = FILTER_CYCLE.index(self.tool_filter)
            self.tool_filter = FILTER_CYCLE[(idx + 1) % len(FILTER_CYCLE)]
            self.feedback_msg = f"Switched filter to: {FILTER_LABELS[self.tool_filter]}"
            self.feedback_style = "#58a6ff"
            self._load_next_drill()
            return

        if event.key == "f2":
            event.stop()
            event.prevent_default()
            if self.current_drill is not None:
                if not self.had_mistake:
                    self.app.db.record_command_practice(self.current_drill.tool, self.current_drill.id, False)  # type: ignore[attr-defined]
                    self.session_done += 1
                self.had_mistake = True
                self.streak = 0
                self.typed_keys = []
                ans = self._display_answer_for_user(self.current_drill)
                self.feedback_msg = f"Answer: {ans} — {self.current_drill.explanation} (Type it to continue)"
                self.feedback_style = "#d29922"
                self._refresh_view()
            return

        if event.key == "f3":
            event.stop()
            event.prevent_default()
            self.app.pop_screen()
            return

        item = self.current_drill
        if item is None:
            return

        event.stop()
        event.prevent_default()
        key = normalize_key(event.key, event.character)
        self.typed_keys.append(key)

        # Check exact match
        if any(self.typed_keys == seq for seq in item.accepted_keys):
            ans = self._display_answer_for_user(item)
            if not self.had_mistake:
                self.streak += 1
                self.session_done += 1
                self.session_correct += 1
                xp = 10 + min(self.streak, 10)
                self.app.db.record_command_practice(item.tool, item.id, True)  # type: ignore[attr-defined]
                self.app.db.update_drill_stats(1, self.streak, xp)  # type: ignore[attr-defined]
                self.feedback_msg = f"✓ {ans} — {item.explanation} (+{xp} XP)"
                self.feedback_style = "bold #39d353"
            else:
                self.app.db.update_drill_stats(1, self.streak, 2)  # type: ignore[attr-defined]
                self.feedback_msg = f"✓ Reinforced: {ans} (+2 XP)"
                self.feedback_style = "#39d353"
            self._load_next_drill()
            return

        # Check if still a valid prefix
        if any(seq[: len(self.typed_keys)] == self.typed_keys for seq in item.accepted_keys):
            self._refresh_view()
            return

        # Mismatch
        if not self.had_mistake:
            self.app.db.record_command_practice(item.tool, item.id, False)  # type: ignore[attr-defined]
            self.session_done += 1
        self.had_mistake = True
        self.streak = 0
        bad_seq = " ".join(format_key_for_display(k) for k in self.typed_keys)
        self.typed_keys = []
        ans = self._display_answer_for_user(item)
        self.feedback_msg = f"✗ Got [{bad_seq}]. Expected: {ans} — {item.explanation}"
        self.feedback_style = "bold #f85149"
        self._refresh_view()
