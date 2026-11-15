"""Track 3 (TMUX Foundations) and Track 4 (TMUX Mastery) levels."""

from __future__ import annotations

from vim_tmux_quest.curriculum.models import Level
from vim_tmux_quest.engine.tmux_engine import SplitNode, TmuxEngine, TmuxPane, TmuxSession, TmuxWindow


def _has_split_direction(node: SplitNode, direction: str) -> bool:
    if node.is_leaf:
        return False
    if node.direction == direction:
        return True
    return any(_has_split_direction(child, direction) for child in node.children)


def get_tmux_levels() -> list[Level]:
    levels: list[Level] = []

    # ------------------------------------------------------------------
    # Track 3: TMUX Foundations
    # ------------------------------------------------------------------
    def setup_3_1() -> TmuxEngine:
        return TmuxEngine()

    def check_3_1(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        win = eng.active_window
        panes_ok = len(win.panes()) >= 2
        vert_ok = _has_split_direction(win.root, "vertical")
        return (panes_ok and vert_ok), [
            ("Have at least 2 panes open", panes_ok),
            ("Split vertically left/right (Prefix + %)", vert_ok),
        ]

    levels.append(
        Level(
            id="tmux_3_1",
            track_id=3,
            track_name="TMUX Foundations",
            number=1,
            title="Prefix & Vertical Split (%)",
            mode="tmux",
            description=(
                "Every TMUX command starts with the Prefix key (default Ctrl-b, configurable in Settings).\n"
                "Press Prefix, release it, then press:\n"
                "  % = split current pane vertically (left | right)"
            ),
            objective_text="Split the terminal vertically into two side-by-side panes.",
            hint="Press Ctrl-b, release, then press %.",
            optimal_solution="Ctrl-b % (2 keys)",
            par_keystrokes=3,
            xp_reward=60,
            setup_fn=setup_3_1,
            check_fn=check_3_1,
        )
    )

    def setup_3_2() -> TmuxEngine:
        return TmuxEngine()

    def check_3_2(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        win = eng.active_window
        panes_ok = len(win.panes()) >= 3
        vert_ok = _has_split_direction(win.root, "vertical")
        horiz_ok = _has_split_direction(win.root, "horizontal")
        return (panes_ok and vert_ok and horiz_ok), [
            ("Create a vertical split (Prefix + %)", vert_ok),
            ('Create a horizontal split (Prefix + ")', horiz_ok),
            ("Have at least 3 panes in the window", panes_ok),
        ]

    levels.append(
        Level(
            id="tmux_3_2",
            track_id=3,
            track_name="TMUX Foundations",
            number=2,
            title='Horizontal Split (")',
            mode="tmux",
            description=(
                "Combine vertical and horizontal splits to build custom terminal dashboards:\n"
                "  Prefix + % = split left | right\n"
                '  Prefix + " = split top / bottom'
            ),
            objective_text="Create a 3-pane workspace with both a vertical split and a horizontal split.",
            hint='Press Ctrl-b %, then press Ctrl-b ".',
            optimal_solution='Ctrl-b % Ctrl-b " (4 keys)',
            par_keystrokes=5,
            xp_reward=75,
            setup_fn=setup_3_2,
            check_fn=check_3_2,
        )
    )

    def setup_3_3() -> TmuxEngine:
        p1 = TmuxPane(pane_id=1, title="logs", content_lines=["[logs] tail -f app.log", "INFO Server healthy"])
        p2 = TmuxPane(pane_id=2, title="metrics", content_lines=["[metrics] CPU: 14%", "MEM: 512MB"])
        p3 = TmuxPane(pane_id=3, title="[TARGET PANE]", content_lines=["[TARGET PANE] db-shell", "postgres=# SELECT 1;"])
        right_split = SplitNode(direction="horizontal", children=[SplitNode(pane=p2), SplitNode(pane=p3)], ratios=[50, 50])
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), right_split], ratios=[50, 50])
        win = TmuxWindow(window_id=1, index=0, name="ops", root=root, active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="main", windows=[win])])

    def check_3_3(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        focused = eng.active_pane.title == "[TARGET PANE]"
        return focused, [
            ("Focus the [TARGET PANE] pane", focused),
        ]

    levels.append(
        Level(
            id="tmux_3_3",
            track_id=3,
            track_name="TMUX Foundations",
            number=3,
            title="Pane Navigation (o / Arrows)",
            mode="tmux",
            description=(
                "Move focus across panes without touching the mouse:\n"
                "  Prefix + o = cycle to next pane\n"
                "  Prefix + Arrow (or h/j/k/l) = move focus directionally"
            ),
            objective_text="Move active focus from 'logs' to [TARGET PANE].",
            hint="Press Ctrl-b o twice (or Ctrl-b Right then Ctrl-b Down).",
            optimal_solution="Ctrl-b o Ctrl-b o (4 keys)",
            par_keystrokes=5,
            xp_reward=75,
            setup_fn=setup_3_3,
            check_fn=check_3_3,
        )
    )

    def setup_3_4() -> TmuxEngine:
        p1 = TmuxPane(pane_id=1, title="editor", content_lines=["vim app.py"])
        p2 = TmuxPane(pane_id=2, title="[INSPECT LOGS]", content_lines=["ERROR 502 Bad Gateway", "Retry in 5s..."])
        p3 = TmuxPane(pane_id=3, title="shell", content_lines=["$ pytest"])
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), SplitNode(pane=p2), SplitNode(pane=p3)], ratios=[34, 33, 33])
        win = TmuxWindow(window_id=1, index=0, name="dev", root=root, active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="main", windows=[win])])

    def check_3_4(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        win = eng.active_window
        on_logs = eng.active_pane.title == "[INSPECT LOGS]"
        zoomed = win.zoomed_pane_id == eng.active_pane.pane_id
        return (on_logs and zoomed), [
            ("Focus [INSPECT LOGS] pane", on_logs),
            ("Toggle zoom on it (Prefix + z)", zoomed),
        ]

    levels.append(
        Level(
            id="tmux_3_4",
            track_id=3,
            track_name="TMUX Foundations",
            number=4,
            title="Zoom & Inspect (z)",
            mode="tmux",
            description=(
                "Need full-screen space for a cramped pane temporarily?\n"
                "  Prefix + z = toggle zoom for the active pane (press again to restore layout)"
            ),
            objective_text="Focus the [INSPECT LOGS] pane and zoom it to full screen.",
            hint="Press Ctrl-b o (or Ctrl-b Right) to focus [INSPECT LOGS], then Ctrl-b z.",
            optimal_solution="Ctrl-b o Ctrl-b z (4 keys)",
            par_keystrokes=5,
            xp_reward=80,
            setup_fn=setup_3_4,
            check_fn=check_3_4,
        )
    )

    def setup_3_5() -> TmuxEngine:
        p1 = TmuxPane(pane_id=1, title="web-server", content_lines=["Listening on :8080"])
        p2 = TmuxPane(pane_id=2, title="[CRASHED WORKER]", content_lines=["Segmentation fault (core dumped)"])
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), SplitNode(pane=p2)], ratios=[50, 50])
        win = TmuxWindow(window_id=1, index=0, name="prod", root=root, active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="main", windows=[win])])

    def check_3_5(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        panes = eng.active_window.panes()
        only_one = len(panes) == 1
        server_alive = any(p.title == "web-server" for p in panes)
        crashed_gone = all(p.title != "[CRASHED WORKER]" for p in panes)
        return (only_one and server_alive and crashed_gone), [
            ("Close [CRASHED WORKER] pane (Prefix + x)", crashed_gone),
            ("Keep web-server running", server_alive and only_one),
        ]

    levels.append(
        Level(
            id="tmux_3_5",
            track_id=3,
            track_name="TMUX Foundations",
            number=5,
            title="Closing Panes (x)",
            mode="tmux",
            description=(
                "Clean up dead or unneeded panes directly from TMUX:\n"
                "  Prefix + x = close the active pane"
            ),
            objective_text="Switch to [CRASHED WORKER] and close it while keeping web-server open.",
            hint="Press Ctrl-b o to move to [CRASHED WORKER], then Ctrl-b x.",
            optimal_solution="Ctrl-b o Ctrl-b x (4 keys)",
            par_keystrokes=5,
            xp_reward=80,
            setup_fn=setup_3_5,
            check_fn=check_3_5,
        )
    )

    def setup_3_6() -> TmuxEngine:
        p1 = TmuxPane(pane_id=1, title="editor", content_lines=["nvim src/main.py"])
        win = TmuxWindow(window_id=1, index=0, name="editor", root=SplitNode(pane=p1), active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="work", windows=[win])])

    def check_3_6(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        sess = eng.active_session
        three_wins = len(sess.windows) >= 3
        back_to_zero = sess.active_window.index == 0
        return (three_wins and back_to_zero), [
            ("Have at least 3 windows open (Prefix + c)", three_wins),
            ("Return focus to Window 0 (Prefix + 0 / n / p)", back_to_zero),
        ]

    levels.append(
        Level(
            id="tmux_3_6",
            track_id=3,
            track_name="TMUX Foundations",
            number=6,
            title="Window Management (c n p 0-9)",
            mode="tmux",
            description=(
                "Windows act like full-screen tabs inside a TMUX session:\n"
                "  Prefix + c = create new window\n"
                "  Prefix + n / p = next / previous window\n"
                "  Prefix + 0..9 = jump directly to window index"
            ),
            objective_text="Create 2 new windows (3 total), then switch back to Window 0.",
            hint="Press Ctrl-b c twice, then Ctrl-b 0 (or Ctrl-b n).",
            optimal_solution="Ctrl-b c Ctrl-b c Ctrl-b 0 (6 keys)",
            par_keystrokes=7,
            xp_reward=85,
            setup_fn=setup_3_6,
            check_fn=check_3_6,
        )
    )

    def setup_3_7() -> TmuxEngine:
        p1 = TmuxPane(pane_id=1, title="zsh", content_lines=["$ git status"])
        win = TmuxWindow(window_id=1, index=0, name="code", root=SplitNode(pane=p1), active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="dev", windows=[win])])

    def check_3_7(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        sess = eng.active_session
        has_two = len(sess.windows) >= 2
        has_logs = any(w.name == "logs" for w in sess.windows)
        return (has_two and has_logs), [
            ("Create a new window (Prefix + c)", has_two),
            ("Rename a window to 'logs' (Prefix + ,)", has_logs),
        ]

    levels.append(
        Level(
            id="tmux_3_7",
            track_id=3,
            track_name="TMUX Foundations",
            number=7,
            title="Naming Windows (,)",
            mode="tmux",
            description=(
                "Meaningful window names keep multi-project workflows organized:\n"
                "  Prefix + , = rename the current window (type name and press Enter)"
            ),
            objective_text="Create a new window and rename it to 'logs'.",
            hint="Press Ctrl-b c, then Ctrl-b , then type logs and press Enter.",
            optimal_solution="Ctrl-b c Ctrl-b , logs Enter (9 keys)",
            par_keystrokes=10,
            xp_reward=90,
            setup_fn=setup_3_7,
            check_fn=check_3_7,
        )
    )

    # ------------------------------------------------------------------
    # Track 4 (Part 1): TMUX Mastery
    # ------------------------------------------------------------------
    def setup_4_1() -> TmuxEngine:
        p1 = TmuxPane(pane_id=1, title="secondary", content_lines=["secondary pane"])
        p2 = TmuxPane(pane_id=2, title="primary", content_lines=["primary pane (active)"])
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), SplitNode(pane=p2)], ratios=[50, 50])
        win = TmuxWindow(window_id=1, index=0, name="layout", root=root, active_pane_id=2)
        return TmuxEngine(sessions=[TmuxSession(name="main", windows=[win])])

    def check_4_1(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        panes = eng.active_window.panes()
        swapped = len(panes) >= 2 and panes[0].title == "primary"
        return swapped, [
            ("Swap 'primary' into the first (left) pane slot (Prefix + {)", swapped),
        ]

    levels.append(
        Level(
            id="tmux_4_1",
            track_id=4,
            track_name="TMUX Mastery & Combo",
            number=1,
            title="Swapping & Breaking Panes ({ } !)",
            mode="tmux",
            description=(
                "Reorganize panes without closing anything:\n"
                "  Prefix + { = swap active pane with previous pane\n"
                "  Prefix + } = swap active pane with next pane\n"
                "  Prefix + ! = break active pane out into its own window"
            ),
            objective_text="Move the active 'primary' pane into the left slot by swapping panes.",
            hint="Press Ctrl-b { to swap the active pane leftward.",
            optimal_solution="Ctrl-b { (2 keys)",
            par_keystrokes=3,
            xp_reward=95,
            setup_fn=setup_4_1,
            check_fn=check_4_1,
        )
    )

    def setup_4_2() -> TmuxEngine:
        p1 = TmuxPane(pane_id=1, title="main-editor", content_lines=["# Main Editor Pane"])
        p2 = TmuxPane(pane_id=2, title="sidebar", content_lines=["# Sidebar"])
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), SplitNode(pane=p2)], ratios=[50, 50])
        win = TmuxWindow(window_id=1, index=0, name="code", root=root, active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="main", windows=[win])])

    def check_4_2(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        eng.active_window.compute_pane_rects()
        main_pane = next((p for p in eng.active_window.panes() if p.title == "main-editor"), None)
        wide_enough = main_pane is not None and main_pane.width_pct >= 70
        return wide_enough, [
            (f"Expand main-editor width to >= 70% (now {main_pane.width_pct if main_pane else 0}%)", wide_enough),
        ]

    levels.append(
        Level(
            id="tmux_4_2",
            track_id=4,
            track_name="TMUX Mastery & Combo",
            number=2,
            title="Resizing Panes (L / :resize-pane)",
            mode="tmux",
            description=(
                "Adjust pane proportions dynamically:\n"
                "  Prefix + Ctrl-Arrow (or Alt-Arrow, or H/J/K/L) = resize by 10%\n"
                "  Prefix + :resize-pane -R 20 = resize right by 20% via command prompt"
            ),
            objective_text="Resize the active 'main-editor' pane so its width is at least 70%.",
            hint="Press Ctrl-b L twice (or Ctrl-b Ctrl-Right twice, or Ctrl-b :resize-pane -R 20 Enter).",
            optimal_solution="Ctrl-b L Ctrl-b L (4 keys)",
            par_keystrokes=6,
            xp_reward=100,
            setup_fn=setup_4_2,
            check_fn=check_4_2,
        )
    )

    def setup_4_3() -> TmuxEngine:
        s1_pane = TmuxPane(pane_id=1, title="zsh", content_lines=["[default session]"])
        s1_win = TmuxWindow(window_id=1, index=0, name="app", root=SplitNode(pane=s1_pane), active_pane_id=1)
        s2_pane = TmuxPane(pane_id=2, title="zsh", content_lines=["[staging environment]"])
        s2_win = TmuxWindow(window_id=2, index=0, name="deploy", root=SplitNode(pane=s2_pane), active_pane_id=2)
        return TmuxEngine(
            sessions=[
                TmuxSession(name="default", windows=[s1_win]),
                TmuxSession(name="staging", windows=[s2_win]),
            ],
            active_session_index=0,
        )

    def check_4_3(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        renamed = any(s.name == "prod" for s in eng.sessions)
        on_staging = eng.active_session.name == "staging"
        return (renamed and on_staging), [
            ("Rename 'default' session to 'prod' (Prefix + $)", renamed),
            ("Switch active session to 'staging' (Prefix + s)", on_staging),
        ]

    levels.append(
        Level(
            id="tmux_4_3",
            track_id=4,
            track_name="TMUX Mastery & Combo",
            number=3,
            title="Session Command Center ($ s)",
            mode="tmux",
            description=(
                "Manage multiple persistent sessions cleanly:\n"
                "  Prefix + $ = rename current session\n"
                "  Prefix + s = open session picker (j/k + Enter to switch)\n"
                "  Prefix + d = detach from session"
            ),
            objective_text="Rename the 'default' session to 'prod', then switch to the 'staging' session.",
            hint="Press Ctrl-b $, type prod and Enter. Then press Ctrl-b s, j, Enter.",
            optimal_solution="Ctrl-b $ prod Enter Ctrl-b s j Enter (11 keys)",
            par_keystrokes=12,
            xp_reward=110,
            setup_fn=setup_4_3,
            check_fn=check_4_3,
        )
    )

    def setup_4_4() -> TmuxEngine:
        p1 = TmuxPane(
            pane_id=1,
            title="logs",
            content_lines=["Server output:", "TOKEN=alpha_9042", "Status: ready"],
        )
        p2 = TmuxPane(
            pane_id=2,
            title="destination",
            content_lines=["Paste token below:"],
        )
        root = SplitNode(direction="vertical", children=[SplitNode(pane=p1), SplitNode(pane=p2)], ratios=[50, 50])
        win = TmuxWindow(window_id=1, index=0, name="copy", root=root, active_pane_id=1)
        return TmuxEngine(sessions=[TmuxSession(name="main", windows=[win])])

    def check_4_4(eng: TmuxEngine) -> tuple[bool, list[tuple[str, bool]]]:
        yanked = "alpha_9042" in eng.paste_buffer
        dest = next((p for p in eng.active_window.panes() if p.title == "destination"), None)
        pasted = dest is not None and "alpha_9042" in "\n".join(dest.content_lines)
        exited = not eng.active_pane.in_copy_mode
        return (yanked and pasted and exited), [
            ("Yank alpha_9042 in copy-mode (Prefix + [)", yanked),
            ("Switch to destination pane & paste (Prefix + ])", pasted),
            ("Exit copy-mode cleanly", exited),
        ]

    levels.append(
        Level(
            id="tmux_4_4",
            track_id=4,
            track_name="TMUX Mastery & Combo",
            number=4,
            title="Copy Mode Ninja ([ Space Enter ])",
            mode="tmux",
            description=(
                "Scroll back and copy terminal output using VIM-style keys inside TMUX:\n"
                "  Prefix + [ = enter copy-mode\n"
                "  h/j/k/l    = move cursor | Space = start selection | Enter = yank & exit\n"
                "  Prefix + ] = paste yanked buffer into active pane"
            ),
            objective_text="Copy 'alpha_9042' from the logs pane using copy-mode and paste it into 'destination'.",
            hint="Press Ctrl-b [, j, Enter (yanks the line), then Ctrl-b o, then Ctrl-b ].",
            optimal_solution="Ctrl-b [ j Enter Ctrl-b o Ctrl-b ] (8 keys)",
            par_keystrokes=10,
            xp_reward=120,
            setup_fn=setup_4_4,
            check_fn=check_4_4,
        )
    )

    return levels
