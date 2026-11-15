"""Unit tests for the TMUX simulation engine."""

from vim_tmux_quest.engine.tmux_engine import TmuxEngine
from vim_tmux_quest.engine.vim_engine import VimEngine


def test_splits_navigation_zoom_and_close():
    eng = TmuxEngine()
    assert len(eng.active_window.panes()) == 1

    eng.handle_keys(["Ctrl-b", "%"])
    assert len(eng.active_window.panes()) == 2
    eng.handle_keys(["Ctrl-b", '"'])
    assert len(eng.active_window.panes()) == 3

    first_id = eng.active_window.panes()[0].pane_id
    eng.handle_keys(["Ctrl-b", "o"])
    assert eng.active_pane.pane_id == first_id

    eng.handle_keys(["Ctrl-b", "z"])
    assert eng.active_window.zoomed_pane_id == first_id
    eng.handle_keys(["Ctrl-b", "z"])
    assert eng.active_window.zoomed_pane_id is None

    eng.handle_keys(["Ctrl-b", "x"])
    assert len(eng.active_window.panes()) == 2


def test_swap_break_and_resize():
    eng = TmuxEngine()
    eng.handle_keys(["Ctrl-b", "%"])
    p0_id = eng.active_window.panes()[0].pane_id
    p1_id = eng.active_window.panes()[1].pane_id
    assert eng.active_pane.pane_id == p1_id

    eng.handle_keys(["Ctrl-b", "{"])
    assert eng.active_window.panes()[0].pane_id == p1_id

    eng.handle_keys(["Ctrl-b", "L", "Ctrl-b", "L"])
    assert eng.active_window.panes()[0].width_pct >= 70

    eng.handle_keys(["Ctrl-b", "!"])
    assert len(eng.active_session.windows) == 2
    assert eng.active_pane.pane_id == p1_id
    assert eng.active_session.windows[0].panes()[0].pane_id == p0_id


def test_windows_sessions_and_prefix_config():
    eng = TmuxEngine(prefix_key="ctrl+a")
    eng.handle_keys(["Ctrl-a", "c", "Ctrl-a", ",", "l", "o", "g", "s", "Enter"])
    assert len(eng.active_session.windows) == 2
    assert eng.active_window.name == "logs"

    eng.handle_keys(["Ctrl-a", "p"])
    assert eng.active_window.index == 0

    eng.handle_keys(["Ctrl-a", "$", "p", "r", "o", "d", "Enter"])
    assert eng.active_session.name == "prod"

    eng.handle_keys(["Ctrl-a", ":", "n", "e", "w", " ", "-", "s", " ", *list("dev"), "Enter"])
    assert len(eng.sessions) == 2
    assert eng.active_session.name == "dev"

    eng.handle_keys(["Ctrl-a", "s", "k", "Enter"])
    assert eng.active_session.name == "prod"

    eng.handle_keys(["Ctrl-a", "d"])
    assert eng.detached is True


def test_copy_mode_and_vim_routing():
    eng = TmuxEngine()
    eng.active_pane.content_lines = ["line zero", "SECRET=1234"]
    eng.handle_keys(["Ctrl-b", "%"])
    eng.handle_keys(["Ctrl-b", "o"])  # back to pane 1
    eng.handle_keys(["Ctrl-b", "[", "j", " ", "$", "Enter"])
    assert eng.paste_buffer == "SECRET=1234"
    eng.handle_keys(["Ctrl-b", "o", "Ctrl-b", "]"])
    assert "SECRET=1234" in "\n".join(eng.active_pane.content_lines)

    # Embedded VimEngine receives non-prefix keys
    vim = VimEngine.from_text("hello")
    eng.active_pane.vim_engine = vim
    eng.handle_keys(["A", "!", "Esc"])
    assert vim.get_text() == "hello!"
