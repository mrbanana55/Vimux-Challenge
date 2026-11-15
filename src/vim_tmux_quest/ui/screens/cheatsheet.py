"""Searchable VIM & TMUX command reference cheat sheet screen."""

from __future__ import annotations

from textual import events
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static

CHEATSHEET_ENTRIES: list[tuple[str, str, str, str]] = [
    ("VIM", "Navigation", "h / j / k / l", "Move left / down / up / right"),
    ("VIM", "Navigation", "w / b / e", "Next word start / prev word start / word end"),
    ("VIM", "Navigation", "0 / ^ / $", "Line start (col 0) / first non-blank / line end"),
    ("VIM", "Navigation", "gg / G / 5G", "First line / last line / jump to line 5"),
    ("VIM", "Navigation", "% / { / }", "Matching bracket / prev paragraph / next paragraph"),
    ("VIM", "Search", "f<c> / t<c> / ; / ,", "Find char on line / till before char / repeat / reverse"),
    ("VIM", "Search", "/text / n / N / *", "Search pattern / next / prev / word under cursor"),
    ("VIM", "Insert", "i / I / a / A", "Insert before / line start / append after / line end"),
    ("VIM", "Insert", "o / O / Esc", "Open line below / open line above / exit to NORMAL"),
    ("VIM", "Editing", "x / r<c> / J / ~", "Delete char / replace char / join lines / toggle case"),
    ("VIM", "Operators", "dd / cc / yy / p / P", "Delete line / change line / yank line / put after / before"),
    ("VIM", "Operators", "dw / d$ / cw / C", "Delete word / delete EOL / change word / change EOL"),
    ("VIM", "Text Objects", 'ciw / di" / ci( / da{', "Change inner word / del inside quotes / change parens / del braces"),
    ("VIM", "Visual", "v / V", "Character-wise visual / line-wise visual selection"),
    ("VIM", "History & Macros", "u / Ctrl-r / .", "Undo / redo / repeat last change"),
    ("VIM", "History & Macros", "qa ... q / @a / @@", "Record macro 'a' / stop / play macro 'a' / replay last"),
    ("VIM", "Commands", ":w / :q / :wq", "Save buffer / quit / save and quit"),
    ("TMUX", "Panes", 'Prefix + % / "', "Split vertically (left|right) / horizontally (top/bottom)"),
    ("TMUX", "Panes", "Prefix + o / Arrows", "Cycle next pane / move focus directionally"),
    ("TMUX", "Panes", "Prefix + z / x", "Toggle pane zoom / close active pane"),
    ("TMUX", "Panes", "Prefix + { / } / !", "Swap pane prev / next / break pane to new window"),
    ("TMUX", "Panes", "Prefix + H/J/K/L or :resize-pane", "Resize active pane (also Ctrl-Arrow / Alt-Arrow)"),
    ("TMUX", "Windows", "Prefix + c / n / p / 0-9", "Create window / next / prev / jump to window index"),
    ("TMUX", "Windows", "Prefix + , / &", "Rename active window / kill active window"),
    ("TMUX", "Sessions", "Prefix + $ / s / d", "Rename session / session switcher / detach session"),
    ("TMUX", "Copy Mode", "Prefix + [ / ]", "Enter copy-mode (Space select, Enter yank) / paste"),
    ("TMUX", "Command Prompt", "Prefix + :new -s name", "Open TMUX command prompt"),
]


class CheatSheetScreen(Screen):
    """Searchable command reference for VIM and TMUX."""

    def compose(self):
        yield Static("COMMAND CHEAT SHEET — VIM & TMUX Reference", classes="screen-header")
        yield Input(placeholder="Filter commands (e.g. split, quote, macro, resize)...", id="cheatsheet-search")
        yield DataTable(id="cheatsheet-table")
        yield Static("Type to filter | Esc: Back to Main Menu", classes="footer-bar")

    def on_mount(self) -> None:
        table = self.query_one("#cheatsheet-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Tool", "Category", "Command / Key", "Description")
        self._populate("")
        self.query_one("#cheatsheet-search", Input).focus()

    def _populate(self, query: str) -> None:
        table = self.query_one("#cheatsheet-table", DataTable)
        table.clear()
        q = query.strip().lower()
        for tool, cat, cmd, desc in CHEATSHEET_ENTRIES:
            haystack = f"{tool} {cat} {cmd} {desc}".lower()
            if not q or q in haystack:
                table.add_row(tool, cat, cmd, desc)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "cheatsheet-search":
            self._populate(event.value)

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.app.pop_screen()
