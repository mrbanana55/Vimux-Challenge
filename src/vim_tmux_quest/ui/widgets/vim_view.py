"""VIM buffer renderer widget."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from vim_tmux_quest.engine.vim_engine import VimEngine


def _cursor_style(mode: str, active: bool) -> str:
    if not active:
        return "reverse dim"
    if mode == "INSERT":
        return "bold #0d1117 on #d29922"
    if mode in ("VISUAL", "VISUAL_LINE"):
        return "bold #0d1117 on #bc8cff"
    return "bold #0d1117 on #58a6ff"


def render_vim_text(vim: VimEngine, active: bool = True) -> Text:
    """Render a VimEngine buffer, cursor, visual selection, and status line."""
    text = Text()
    visual_bounds = vim._visual_bounds() if vim.mode in ("VISUAL", "VISUAL_LINE") else None
    cursor_style = _cursor_style(vim.mode, active)
    sel_style = "on #3b2e58"

    for r, line in enumerate(vim.lines):
        text.append(f"{r + 1:>3} │ ", style="#6e7681")
        if not line:
            if r == vim.row:
                text.append(" ", style=cursor_style)
            elif visual_bounds is not None and vim.mode == "VISUAL_LINE":
                s_pos, e_pos = visual_bounds
                if s_pos[0] <= r <= e_pos[0]:
                    text.append(" ", style=sel_style)
        else:
            for c, ch in enumerate(line):
                is_cursor = r == vim.row and c == vim.col
                is_selected = False
                if visual_bounds is not None:
                    s_pos, e_pos = visual_bounds
                    if vim.mode == "VISUAL_LINE":
                        is_selected = s_pos[0] <= r <= e_pos[0]
                    else:
                        is_selected = s_pos <= (r, c) <= e_pos
                if is_cursor:
                    text.append(ch, style=cursor_style)
                elif is_selected:
                    text.append(ch, style=sel_style)
                else:
                    text.append(ch, style="#e6edf3")

            if r == vim.row and vim.col >= len(line):
                text.append(" ", style=cursor_style)

        text.append("\n")

    text.append("\n")
    if vim.mode == "COMMAND":
        text.append(f"{vim.command_prefix}{vim.command_buffer}", style="bold #f0c674")
        text.append(" ", style="bold #0d1117 on #f0c674")
    else:
        mode_colors = {
            "NORMAL": "bold #58a6ff",
            "INSERT": "bold #d29922",
            "VISUAL": "bold #bc8cff",
            "VISUAL_LINE": "bold #bc8cff",
        }
        text.append(f"-- {vim.mode} --", style=mode_colors.get(vim.mode, "bold"))
        if vim.recording_register:
            text.append(f"  recording @{vim.recording_register}", style="bold #f85149")
        pending = f"{vim.pending_count}{vim.pending_op}"
        if pending:
            text.append(f"  [{pending}]", style="#79c0ff")
        if vim.saved:
            text.append("  [written]", style="#39d353")
        if vim.status_message:
            text.append(f"  {vim.status_message}", style="#8b949e")
        text.append(f"   Ln {vim.row + 1}, Col {vim.col + 1}", style="#6e7681")

    return text


class VimView(Static):
    """Focusable Textual widget displaying a simulated VIM buffer."""

    can_focus = True

    def __init__(self, engine: VimEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._engine = engine

    def set_engine(self, engine: VimEngine) -> None:
        self._engine = engine
        self.refresh_buffer()

    def refresh_buffer(self) -> None:
        if self._engine is None:
            self.update("")
            return
        self.update(render_vim_text(self._engine, active=True))
