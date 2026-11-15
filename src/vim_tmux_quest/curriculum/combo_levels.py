"""Track 4 (Part 2): Combined VIM + TMUX workflow levels."""

from __future__ import annotations

from vim_tmux_quest.curriculum.models import Level
from vim_tmux_quest.engine.tmux_engine import SplitNode, TmuxEngine, TmuxPane, TmuxSession, TmuxWindow
from vim_tmux_quest.engine.vim_engine import VimEngine


def get_combo_levels() -> list[Level]:
    levels: list[Level] = []

    # ------------------------------------------------------------------
    # combo_4_5: Split & Fix
    # ------------------------------------------------------------------
    def setup_4_5() -> TmuxEngine:
        vim = VimEngine.from_text(
            "{\n"
            '  "service": "auth",\n'
            '  "status": "error"\n'
            "}",
            row=1,
            col=2,
        )
        p1 = TmuxPane(pane_id=1, title="app.json", vim_engine=vim)
        win = TmuxWindow(window_id=1, index=0, name="config", root=SplitNode(pane=p1), active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="dev", windows=[win])])

    def check_4_5(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        panes = eng.active_window.panes()
        has_split = len(panes) >= 2
        editor = next((p for p in panes if p.title == "app.json" and p.vim_engine is not None), None)
        expected = '{\n  "service": "auth",\n  "status": "ok"\n}'
        fixed = editor is not None and editor.vim_engine is not None and editor.vim_engine.get_text() == expected
        normal = editor is not None and editor.vim_engine is not None and editor.vim_engine.mode == "NORMAL"
        return (has_split and fixed and normal), [
            ("Split a second pane vertically (Prefix + %)", has_split),
            ('Switch back to app.json and change "error" to "ok"', fixed),
            ("Return VIM to NORMAL mode", normal),
        ]

    levels.append(
        Level(
            id="combo_4_5",
            track_id=4,
            track_name="TMUX Mastery & Combo",
            number=5,
            title="Split & Fix (TMUX + VIM)",
            mode="combo",
            description=(
                "Real terminal mastery means combining TMUX and VIM seamlessly.\n"
                "Non-prefix keys go straight to VIM inside the active pane, while Prefix keys control TMUX."
            ),
            objective_text='Split vertically (Prefix + %), switch back to app.json, and change "error" to "ok".',
            hint='Press Ctrl-b %, then Ctrl-b o, then j f: ci" ok Esc.',
            optimal_solution='Ctrl-b % Ctrl-b o j f: ci"ok<Esc> (13 keys)',
            par_keystrokes=15,
            xp_reward=130,
            setup_fn=setup_4_5,
            check_fn=check_4_5,
        )
    )

    # ------------------------------------------------------------------
    # combo_4_6: Multi-Pane Refactor
    # ------------------------------------------------------------------
    def setup_4_6() -> TmuxEngine:
        v1 = VimEngine.from_text("PORT = 5000", row=0, col=0)
        v2 = VimEngine.from_text("DEFAULT_PORT = 5000", row=0, col=0)
        p1 = TmuxPane(pane_id=1, title="api.py", vim_engine=v1)
        p2 = TmuxPane(pane_id=2, title="config.py", vim_engine=v2)
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), SplitNode(pane=p2)], ratios=[50, 50])
        win = TmuxWindow(window_id=1, index=0, name="refactor", root=root, active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="backend", windows=[win])])

    def check_4_6(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        panes = eng.active_window.panes()
        api = next((p for p in panes if p.title == "api.py"), None)
        cfg = next((p for p in panes if p.title == "config.py"), None)
        api_ok = bool(api and api.vim_engine and api.vim_engine.get_text() == "PORT = 8080" and api.vim_engine.saved)
        cfg_ok = bool(cfg and cfg.vim_engine and cfg.vim_engine.get_text() == "DEFAULT_PORT = 8080" and cfg.vim_engine.saved)
        return (api_ok and cfg_ok), [
            ("Update api.py to 'PORT = 8080' and save (:w)", api_ok),
            ("Switch pane and update config.py to 'DEFAULT_PORT = 8080' (:w)", cfg_ok),
        ]

    levels.append(
        Level(
            id="combo_4_6",
            track_id=4,
            track_name="TMUX Mastery & Combo",
            number=6,
            title="Multi-Pane Refactor (TMUX + VIM)",
            mode="combo",
            description=(
                "Edit multiple files side-by-side in separate TMUX panes using VIM.\n"
                "Remember: :w saves the active VIM buffer."
            ),
            objective_text="Change port 5000 to 8080 and save (:w) in BOTH api.py and config.py.",
            hint="In api.py: f5 ciw 8080 Esc :w Enter. Then Ctrl-b o, repeat in config.py.",
            optimal_solution="f5ciw8080<Esc>:w<Enter> Ctrl-b o f5ciw8080<Esc>:w<Enter>",
            par_keystrokes=30,
            xp_reward=150,
            setup_fn=setup_4_6,
            check_fn=check_4_6,
        )
    )

    # ------------------------------------------------------------------
    # combo_4_7: Final Boss
    # ------------------------------------------------------------------
    def setup_4_7() -> TmuxEngine:
        vim = VimEngine.from_text(
            'HOST = "0.0.0.0"\n'
            "DEBUG = True\n"
            'URL = "http://broken.local"',
            row=0,
            col=0,
        )
        p1 = TmuxPane(pane_id=1, title="server.py", vim_engine=vim)
        p2 = TmuxPane(pane_id=2, title="[CRASHED WORKER]", content_lines=["Process exited with code 137"])
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), SplitNode(pane=p2)], ratios=[60, 40])
        win = TmuxWindow(window_id=1, index=0, name="zsh", root=root, active_pane_id=2)
        return TmuxEngine(sessions=[TmuxSession(name="prod", windows=[win])])

    def check_4_7(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        win = eng.active_window
        panes = win.panes()
        renamed = win.name == "hotfix"
        crashed_closed = len(panes) == 1 and all(p.title != "[CRASHED WORKER]" for p in panes)
        srv = next((p for p in panes if p.title == "server.py" and p.vim_engine is not None), None)
        expected = 'HOST = "0.0.0.0"\nURL = "https://prod.io"'
        vim_fixed = bool(srv and srv.vim_engine and srv.vim_engine.get_text() == expected)
        vim_saved = bool(srv and srv.vim_engine and srv.vim_engine.saved)
        return (renamed and crashed_closed and vim_fixed and vim_saved), [
            ("Rename window to 'hotfix' (Prefix + ,)", renamed),
            ("Close [CRASHED WORKER] pane (Prefix + x)", crashed_closed),
            ("Remove DEBUG line and change URL to https://prod.io", vim_fixed),
            ("Save server.py (:w)", vim_saved),
        ]

    levels.append(
        Level(
            id="combo_4_7",
            track_id=4,
            track_name="TMUX Mastery & Combo",
            number=7,
            title="Final Boss: Full Stack Rescue",
            mode="combo",
            description=(
                "Put everything together in a live incident simulation!\n"
                "Manage your TMUX workspace, remove the dead worker, patch the config in VIM, and save."
            ),
            objective_text=(
                "1) Rename window to 'hotfix', 2) Close [CRASHED WORKER], "
                "3) Delete 'DEBUG = True' and update URL to 'https://prod.io', 4) Save with :w."
            ),
            hint='Ctrl-b , hotfix Enter -> Ctrl-b x -> jdd -> ci"https://prod.io Esc -> :w Enter.',
            optimal_solution='Ctrl-b , hotfix Enter Ctrl-b x jdd ci"https://prod.io<Esc> :w<Enter>',
            par_keystrokes=40,
            xp_reward=200,
            setup_fn=setup_4_7,
            check_fn=check_4_7,
        )
    )

    return levels
