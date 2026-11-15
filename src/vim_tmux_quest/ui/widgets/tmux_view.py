"""TMUX multi-pane layout, status bar, and copy-mode renderer widget."""

from __future__ import annotations

from rich.text import Text
from textual.containers import Container, Vertical
from textual.widgets import Static

from vim_tmux_quest.engine.tmux_engine import SplitNode, TmuxEngine, TmuxPane, TmuxWindow
from vim_tmux_quest.ui.widgets.vim_view import render_vim_text


def _render_copy_mode(pane: TmuxPane) -> Text:
    text = Text()
    lines = pane.get_lines() or [""]
    sel_bounds: tuple[tuple[int, int], tuple[int, int]] | None = None
    if pane.copy_anchor is not None:
        a, b = sorted([pane.copy_anchor, (pane.copy_row, pane.copy_col)])
        sel_bounds = (a, b)

    text.append("[COPY MODE] ", style="bold #d29922")
    text.append("hjkl: move | Space: select | Enter/y: yank | q: exit\n", style="#8b949e")
    for r, line in enumerate(lines):
        text.append(f"{r + 1:>3} │ ", style="#6e7681")
        if not line:
            if r == pane.copy_row:
                text.append(" ", style="bold #0d1117 on #d29922")
        else:
            for c, ch in enumerate(line):
                is_cursor = r == pane.copy_row and c == pane.copy_col
                is_sel = sel_bounds is not None and sel_bounds[0] <= (r, c) <= sel_bounds[1]
                if is_cursor:
                    text.append(ch, style="bold #0d1117 on #d29922")
                elif is_sel:
                    text.append(ch, style="on #3b2e58")
                else:
                    text.append(ch, style="#e6edf3")
        text.append("\n")
    return text


def _render_shell_pane(pane: TmuxPane, active: bool) -> Text:
    text = Text()
    for idx, line in enumerate(pane.content_lines):
        text.append(line, style="#e6edf3" if active else "#8b949e")
        if idx < len(pane.content_lines) - 1:
            text.append("\n")
    if active:
        text.append(" ", style="bold #0d1117 on #39d353")
    return text


def _tree_signature(win: TmuxWindow) -> tuple:
    def _walk(node: SplitNode) -> tuple:
        if node.is_leaf:
            assert node.pane is not None
            return ("L", node.pane.pane_id)
        return ("N", node.direction, tuple(node.ratios), tuple(_walk(c) for c in node.children))

    return (win.window_id, win.zoomed_pane_id, _walk(win.root))


class TmuxView(Vertical):
    """Focusable Textual widget rendering a simulated TMUX workspace."""

    can_focus = True

    def __init__(self, engine: TmuxEngine | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._engine = engine
        self._last_sig: tuple | None = None
        self._pane_widgets: dict[int, Static] = {}

    def compose(self):
        yield Container(id="tmux-desktop")
        yield Static("", id="tmux-promptbar", classes="hidden")
        yield Static("", id="tmux-statusbar")

    def _build_split_widget(self, node: SplitNode, win: TmuxWindow):
        if node.is_leaf:
            assert node.pane is not None
            pane = node.pane
            widget = Static("", classes="tmux-pane")
            self._pane_widgets[pane.pane_id] = widget
            return widget

        cls = "tmux-split-v" if node.direction == "vertical" else "tmux-split-h"
        child_widgets = []
        for child, ratio in zip(node.children, node.ratios):
            cw = self._build_split_widget(child, win)
            if node.direction == "vertical":
                cw.styles.width = f"{ratio}fr"
                cw.styles.height = "1fr"
            else:
                cw.styles.height = f"{ratio}fr"
                cw.styles.width = "1fr"
            child_widgets.append(cw)
        return Container(*child_widgets, classes=cls)

    async def sync_engine(self, engine: TmuxEngine) -> None:
        self._engine = engine
        win = engine.active_window
        sig = _tree_signature(win)
        desktop = self.query_one("#tmux-desktop", Container)

        if sig != self._last_sig:
            self._last_sig = sig
            self._pane_widgets.clear()
            await desktop.remove_children()
            if win.zoomed_pane_id is not None:
                zoomed_pane = win.active_pane()
                widget = Static("", classes="tmux-pane")
                widget.styles.width = "1fr"
                widget.styles.height = "1fr"
                self._pane_widgets[zoomed_pane.pane_id] = widget
                await desktop.mount(widget)
            else:
                root_widget = self._build_split_widget(win.root, win)
                root_widget.styles.width = "1fr"
                root_widget.styles.height = "1fr"
                await desktop.mount(root_widget)

        # Update pane contents, borders, and titles
        for pane in win.panes():
            widget = self._pane_widgets.get(pane.pane_id)
            if widget is None:
                continue
            is_active = pane.pane_id == win.active_pane_id
            widget.set_class(is_active and not pane.in_copy_mode, "tmux-pane-active")
            widget.set_class(pane.in_copy_mode, "tmux-pane-copy")

            badges = [f"{pane.pane_id}:{pane.title}"]
            if pane.vim_engine is not None:
                badges.append("[VIM]")
            if pane.in_copy_mode:
                badges.append("[COPY]")
            if win.zoomed_pane_id == pane.pane_id:
                badges.append("[Z]")
            badges.append(f"{pane.width_pct}%x{pane.height_pct}%")
            widget.border_title = " ".join(badges)

            if pane.in_copy_mode:
                widget.update(_render_copy_mode(pane))
            elif pane.vim_engine is not None:
                widget.update(render_vim_text(pane.vim_engine, active=is_active))
            else:
                widget.update(_render_shell_pane(pane, active=is_active))

        # Update prompt bar if active
        prompt_bar = self.query_one("#tmux-promptbar", Static)
        if engine.prompt_mode is None:
            prompt_bar.add_class("hidden")
            prompt_bar.update("")
        else:
            prompt_bar.remove_class("hidden")
            if engine.prompt_mode == "rename-window":
                prompt_bar.update(f"(rename-window) {engine.prompt_buffer}█")
            elif engine.prompt_mode == "rename-session":
                prompt_bar.update(f"(rename-session) {engine.prompt_buffer}█")
            elif engine.prompt_mode == "command":
                prompt_bar.update(f":{engine.prompt_buffer}█")
            elif engine.prompt_mode == "session-picker":
                lines = ["Session Switcher (j/k + Enter, Esc to cancel):"]
                for idx, sess in enumerate(engine.sessions):
                    marker = ">" if idx == engine.picker_index else " "
                    attached = " (attached)" if idx == engine.active_session_index else ""
                    lines.append(f"  {marker} ({idx}) {sess.name}: {len(sess.windows)} windows{attached}")
                prompt_bar.update("\n".join(lines))

        # Update TMUX status bar
        sess = engine.active_session
        win_tabs = []
        for idx, w in enumerate(sess.windows):
            flag = "*" if idx == sess.active_window_index else "-"
            zoom_flag = "Z" if w.zoomed_pane_id is not None else ""
            win_tabs.append(f"{w.index}:{w.name}{flag}{zoom_flag}")
        prefix_state = " [PREFIX ACTIVE]" if engine.prefix_active else ""
        detach_state = " [DETACHED]" if engine.detached else ""
        msg = f" | {engine.status_message}" if engine.status_message else ""
        status_txt = (
            f"[{sess.name}]  {'  '.join(win_tabs)}"
            f"   |   Prefix: {engine.prefix_key}{prefix_state}{detach_state}{msg}"
        )
        self.query_one("#tmux-statusbar", Static).update(status_txt)
