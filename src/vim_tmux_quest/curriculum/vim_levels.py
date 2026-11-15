"""Track 1 (VIM Foundations) and Track 2 (VIM Precision & Power) levels."""

from __future__ import annotations

from vim_tmux_quest.curriculum.models import Level
from vim_tmux_quest.engine.vim_engine import VimEngine


def _attach_milestones(engine: VimEngine, evaluator) -> VimEngine:
    engine._milestones = {}  # type: ignore[attr-defined]

    def _on_change() -> None:
        evaluator(engine, engine._milestones)  # type: ignore[attr-defined]

    engine.on_change_callback = _on_change
    return engine


def get_vim_levels() -> list[Level]:
    levels: list[Level] = []

    # ------------------------------------------------------------------
    # Track 1: VIM Foundations
    # ------------------------------------------------------------------
    def setup_1_1() -> VimEngine:
        return VimEngine.from_text(
            ". . . . . . . . . .\n"
            ". . . . . . . . . .\n"
            ". . . . . . . . . .\n"
            ". . . [X] . . . . .\n"
            ". . . . . . . . . .",
            row=0,
            col=0,
        )

    def check_1_1(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        on_row = eng.row == 3
        on_target = eng.row == 3 and 6 <= eng.col <= 8
        return on_target, [
            ("Move down to row 4 (index 3)", on_row),
            ("Place cursor on target [X]", on_target),
        ]

    levels.append(
        Level(
            id="vim_1_1",
            track_id=1,
            track_name="VIM Foundations",
            number=1,
            title="First Steps (h j k l)",
            mode="vim",
            description=(
                "In VIM Normal mode, you navigate without touching arrow keys:\n"
                "  h = left, j = down, k = up, l = right\n"
                "Tip: You can also prefix a count like 3j to jump 3 lines down."
            ),
            objective_text="Move the cursor from top-left to the [X] marker on row 4.",
            hint="Press j three times to reach row 4, then l six times to reach [X] (or 3j7l).",
            optimal_solution="jjjllllll (9 keys) or 3j7l (4 keys)",
            par_keystrokes=9,
            xp_reward=50,
            setup_fn=setup_1_1,
            check_fn=check_1_1,
        )
    )

    def setup_1_2() -> VimEngine:
        return VimEngine.from_text(
            "let base = 10;\n"
            "let bonus = 25;\n"
            "let result = base + bonus; // RETURN",
            row=0,
            col=0,
        )

    def check_1_2(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        on_line = eng.row == 2
        on_word = eng.row == 2 and 30 <= eng.col <= 35
        return on_word, [
            ("Move to line 3", on_line),
            ("Land cursor on RETURN", on_word),
        ]

    levels.append(
        Level(
            id="vim_1_2",
            track_id=1,
            track_name="VIM Foundations",
            number=2,
            title="Word Surfer (w b e)",
            mode="vim",
            description=(
                "Stepping one character at a time is slow. Jump by words instead:\n"
                "  w = start of next word   |  b = start of previous word\n"
                "  e = end of current/next word"
            ),
            objective_text="Move to line 3 and jump across words to land on RETURN.",
            hint="Press jj to drop to line 3, then press w repeatedly (or 8w, or $b).",
            optimal_solution="jj$b (4 keys) or jj8w (4 keys) or jjwwwwwwww (10 keys)",
            par_keystrokes=10,
            xp_reward=60,
            setup_fn=setup_1_2,
            check_fn=check_1_2,
        )
    )

    def eval_1_3(eng: VimEngine, m: dict) -> None:
        if eng.row == 0 and eng.col == 0:
            m["col0"] = True
        if eng.row == 0 and eng.col == 8:
            m["first_non_blank"] = True
        if eng.row == 1 and eng.col == len(eng.lines[1]) - 1:
            m["eol"] = True

    def setup_1_3() -> VimEngine:
        eng = VimEngine.from_text(
            "        indented_target = 42;\n"
            "    status = 'READY_GO';",
            row=0,
            col=15,
        )
        return _attach_milestones(eng, eval_1_3)

    def check_1_3(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        m = getattr(eng, "_milestones", {})
        c1 = bool(m.get("col0"))
        c2 = bool(m.get("first_non_blank"))
        c3 = bool(m.get("eol"))
        return (c1 and c2 and c3), [
            ("Jump to column 0 on line 1 (0)", c1),
            ("Jump to first non-blank char 'i' on line 1 (^)", c2),
            ("Jump to end of line 2 (j$)", c3),
        ]

    levels.append(
        Level(
            id="vim_1_3",
            track_id=1,
            track_name="VIM Foundations",
            number=3,
            title="Line Boundaries (0 ^ $)",
            mode="vim",
            description=(
                "Snap to line edges instantly:\n"
                "  0 = very start of line (col 0)\n"
                "  ^ = first non-whitespace character\n"
                "  $ = end of line"
            ),
            objective_text="Hit all three line-edge checkpoints: col 0, first non-blank, and EOL of line 2.",
            hint="Press 0, then ^, then j, then $.",
            optimal_solution="0^j$ (4 keys)",
            par_keystrokes=5,
            xp_reward=60,
            setup_fn=setup_1_3,
            check_fn=check_1_3,
        )
    )

    def eval_1_4(eng: VimEngine, m: dict) -> None:
        if eng.row == len(eng.lines) - 1:
            m["bottom"] = True
        if eng.row == 0:
            m["top"] = True

    def setup_1_4() -> VimEngine:
        eng = VimEngine.from_text(
            "line 1: # start of file\n"
            "line 2: import sys\n"
            "line 3: import os\n"
            "line 4: def boot():\n"
            "line 5:     TARGET_LINE = True\n"
            "line 6:     return TARGET_LINE\n"
            "line 7: # footer\n"
            "line 8: # end of file",
            row=2,
            col=0,
        )
        return _attach_milestones(eng, eval_1_4)

    def check_1_4(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        m = getattr(eng, "_milestones", {})
        bottom = bool(m.get("bottom"))
        top = bool(m.get("top"))
        line5 = eng.row == 4
        return (bottom and top and line5), [
            ("Jump to the last line (G)", bottom),
            ("Jump to the first line (gg)", top),
            ("Finish on line 5 (5G)", line5),
        ]

    levels.append(
        Level(
            id="vim_1_4",
            track_id=1,
            track_name="VIM Foundations",
            number=4,
            title="File Teleport (gg G <n>G)",
            mode="vim",
            description=(
                "Navigate large files in two keystrokes:\n"
                "  gg = jump to line 1\n"
                "  G  = jump to the last line\n"
                "  5G = jump directly to line 5"
            ),
            objective_text="Visit the bottom of the file, then the top, and finish on line 5.",
            hint="Press G, then gg, then 5G.",
            optimal_solution="Ggg5G (5 keys)",
            par_keystrokes=6,
            xp_reward=70,
            setup_fn=setup_1_4,
            check_fn=check_1_4,
        )
    )

    def setup_1_5() -> VimEngine:
        return VimEngine.from_text("port = 8080", row=0, col=5)

    def check_1_5(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        text_ok = eng.get_text() == "const port = 8080;"
        normal_ok = eng.mode == "NORMAL"
        return (text_ok and normal_ok), [
            ("Line reads 'const port = 8080;'", text_ok),
            ("Return to NORMAL mode (Esc)", normal_ok),
        ]

    levels.append(
        Level(
            id="vim_1_5",
            track_id=1,
            track_name="VIM Foundations",
            number=5,
            title="Entering Insert Mode (i a I A)",
            mode="vim",
            description=(
                "Multiple ways to enter Insert mode from anywhere on a line:\n"
                "  i / a = insert before / append after cursor\n"
                "  I / A = insert at line start / append at line end\n"
                "Always press Esc to return to NORMAL mode when done."
            ),
            objective_text="Turn 'port = 8080' into 'const port = 8080;' and return to NORMAL mode.",
            hint="Press I to jump to line start in Insert mode, type 'const ', press Esc, then A, type ';', press Esc.",
            optimal_solution="Iconst <Esc>A;<Esc> (11 keys)",
            par_keystrokes=12,
            xp_reward=75,
            setup_fn=setup_1_5,
            check_fn=check_1_5,
        )
    )

    def setup_1_6() -> VimEngine:
        return VimEngine.from_text("def ping():", row=0, col=0)

    def check_1_6(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        expected = "# Check server health\ndef ping():\n    return True"
        text_ok = eng.get_text() == expected
        normal_ok = eng.mode == "NORMAL"
        return (text_ok and normal_ok), [
            ("Add '# Check server health' above def ping():", len(eng.lines) >= 1 and eng.lines[0] == "# Check server health"),
            ("Add '    return True' below def ping():", len(eng.lines) >= 3 and eng.lines[2] == "    return True"),
            ("Return to NORMAL mode (Esc)", normal_ok),
        ]

    levels.append(
        Level(
            id="vim_1_6",
            track_id=1,
            track_name="VIM Foundations",
            number=6,
            title="Opening New Lines (o O)",
            mode="vim",
            description=(
                "Create new lines and immediately enter Insert mode:\n"
                "  o = open a new line BELOW the cursor\n"
                "  O = open a new line ABOVE the cursor"
            ),
            objective_text=(
                "Insert '# Check server health' above 'def ping():' and '    return True' below it, "
                "then press Esc."
            ),
            hint="Press O, type '# Check server health', press Esc, press j, press o, type '    return True', press Esc.",
            optimal_solution="O# Check server health<Esc>jo    return True<Esc>",
            par_keystrokes=43,
            xp_reward=80,
            setup_fn=setup_1_6,
            check_fn=check_1_6,
        )
    )

    def setup_1_7() -> VimEngine:
        return VimEngine.from_text(
            'host = "locallhost"\n'
            "DEBUG_MODE = True\n"
            "port = 3000",
            row=0,
            col=12,
        )

    def check_1_7(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        expected = 'host = "localhost"\nport = 3000'
        typo_fixed = eng.lines[0] == 'host = "localhost"'
        debug_removed = "DEBUG_MODE = True" not in eng.lines
        exact = eng.get_text() == expected
        return exact, [
            ("Fix 'locallhost' -> 'localhost' (x)", typo_fixed),
            ("Delete the DEBUG_MODE line (dd)", debug_removed),
            ("Buffer matches clean config", exact),
        ]

    levels.append(
        Level(
            id="vim_1_7",
            track_id=1,
            track_name="VIM Foundations",
            number=7,
            title="Quick Cleanup & Undo (x dd u)",
            mode="vim",
            description=(
                "Fast edits without entering Insert mode:\n"
                "  x  = delete character under cursor\n"
                "  dd = delete entire current line\n"
                "  u  = undo last change  |  Ctrl-r = redo"
            ),
            objective_text="Remove the extra 'l' in locallhost and delete the DEBUG_MODE line.",
            hint="Cursor is already on the extra 'l'. Press x, then j, then dd.",
            optimal_solution="xjdd (4 keys)",
            par_keystrokes=5,
            xp_reward=80,
            setup_fn=setup_1_7,
            check_fn=check_1_7,
        )
    )

    # ------------------------------------------------------------------
    # Track 2: VIM Precision & Power
    # ------------------------------------------------------------------
    def setup_2_1() -> VimEngine:
        return VimEngine.from_text(
            "config = {\n"
            '    "old_v1": True,\n'
            '    "old_v2": True,\n'
            '    "env": "production",\n'
            "}",
            row=0,
            col=0,
        )

    def check_2_1(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        expected = 'config = {\n    "env": "production",\n}'
        text_ok = eng.get_text() == expected
        cursor_ok = eng.row == 1 and 11 <= eng.col <= 22
        return (text_ok and cursor_ok), [
            ("Delete both 'old_v1' and 'old_v2' lines", text_ok),
            ("Land cursor on 'production'", cursor_ok),
        ]

    levels.append(
        Level(
            id="vim_2_1",
            track_id=2,
            track_name="VIM Precision & Power",
            number=1,
            title="Count Multipliers (2dd 3w)",
            mode="vim",
            description=(
                "Almost every VIM command accepts a numeric count prefix:\n"
                "  2dd = delete 2 lines  |  4j = move 4 lines down  |  3w = jump 3 words"
            ),
            objective_text="Delete the two deprecated lines with a count, then jump to 'production'.",
            hint="Press j, then 2dd to delete both old lines, then 4w (or f\") to land on 'production'.",
            optimal_solution="j2dd4w (6 keys)",
            par_keystrokes=8,
            xp_reward=90,
            setup_fn=setup_2_1,
            check_fn=check_2_1,
        )
    )

    def setup_2_2() -> VimEngine:
        return VimEngine.from_text(
            'send_packet(host="10.0.0.1", port=8080, retry=0)',
            row=0,
            col=0,
        )

    def check_2_2(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        expected = 'send_packet(host="10.0.0.1", port=8080, retry=3)'
        return (eng.get_text() == expected), [
            ("Change retry=0 to retry=3 using f/t and r", eng.get_text() == expected),
        ]

    levels.append(
        Level(
            id="vim_2_2",
            track_id=2,
            track_name="VIM Precision & Power",
            number=2,
            title="Sniper Find (f t r ;)",
            mode="vim",
            description=(
                "Jump horizontally to any character on the current line:\n"
                "  f<char> = jump ON <char> forward   |  F<char> = backward\n"
                "  t<char> = jump BEFORE <char>       |  ; / , = repeat / reverse\n"
                "  r<char> = replace single char under cursor without entering Insert mode"
            ),
            objective_text="Jump to the 0 in 'retry=0' and replace it with '3'.",
            hint="Press t) to land right on 0 (or f0), then r3 to replace it with 3.",
            optimal_solution="t)r3 (4 keys) or f0r3 (4 keys)",
            par_keystrokes=6,
            xp_reward=95,
            setup_fn=setup_2_2,
            check_fn=check_2_2,
        )
    )

    def setup_2_3() -> VimEngine:
        return VimEngine.from_text(
            'temp user = "alice" # old comment\n'
            'status = "pending"',
            row=0,
            col=0,
        )

    def check_2_3(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        l0_ok = len(eng.lines) >= 1 and eng.lines[0] == 'user = "alice"'
        l1_ok = len(eng.lines) >= 2 and eng.lines[1] == 'status = "active"'
        normal_ok = eng.mode == "NORMAL"
        return (l0_ok and l1_ok and normal_ok), [
            ("Line 1 reads 'user = \"alice\"'", l0_ok),
            ("Line 2 reads 'status = \"active\"'", l1_ok),
            ("Return to NORMAL mode", normal_ok),
        ]

    levels.append(
        Level(
            id="vim_2_3",
            track_id=2,
            track_name="VIM Precision & Power",
            number=3,
            title="Operators + Motions (dw d$ cw)",
            mode="vim",
            description=(
                "VIM's grammar is Operator + Motion:\n"
                "  dw = delete word   |  d$ = delete to end of line\n"
                "  cw = change word   |  c$ = change to end of line"
            ),
            objective_text=(
                "Remove 'temp ' and ' # old comment' from line 1, then change 'pending' to 'active' on line 2."
            ),
            hint="Use dw, then f\"l then d$ (or t\" then 2ld$), then j0fpcwactive<Esc>.",
            optimal_solution='dwf";ld$j0fpcwactive<Esc> (21 keys)',
            par_keystrokes=22,
            xp_reward=100,
            setup_fn=setup_2_3,
            check_fn=check_2_3,
        )
    )

    def setup_2_4() -> VimEngine:
        return VimEngine.from_text(
            'api_key = "expired_token_123"\n'
            "connect(bad_host, 9999)",
            row=0,
            col=0,
        )

    def check_2_4(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        l0_ok = len(eng.lines) >= 1 and eng.lines[0] == 'api_key = "valid_key"'
        l1_ok = len(eng.lines) >= 2 and eng.lines[1] == "connect()"
        normal_ok = eng.mode == "NORMAL"
        return (l0_ok and l1_ok and normal_ok), [
            ("Change string inside quotes to 'valid_key' (ci\")", l0_ok),
            ("Delete arguments inside parentheses (di()", l1_ok),
            ("Return to NORMAL mode", normal_ok),
        ]

    levels.append(
        Level(
            id="vim_2_4",
            track_id=2,
            track_name="VIM Precision & Power",
            number=4,
            title='Text Objects (ci" di()',
            mode="vim",
            description=(
                "Text objects operate on structured blocks regardless of exact cursor position inside:\n"
                '  ci" = change inside double quotes  |  da" = delete around quotes\n'
                "  di( = delete inside parentheses    |  ciw = change inner word"
            ),
            objective_text='Replace "expired_token_123" with "valid_key" and empty connect(...) to connect().',
            hint='Press ci" then type valid_key and Esc. Press j, then di(.',
            optimal_solution='ci"valid_key<Esc>jdi( (17 keys)',
            par_keystrokes=21,
            xp_reward=110,
            setup_fn=setup_2_4,
            check_fn=check_2_4,
        )
    )

    def setup_2_5() -> VimEngine:
        return VimEngine.from_text(
            'step_2 = "deploy"\n'
            'step_1 = "build"\n'
            'step_3 = "verify"',
            row=0,
            col=0,
        )

    def check_2_5(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        expected = 'step_1 = "build"\nstep_2 = "deploy"\nstep_3 = "verify"'
        return (eng.get_text() == expected), [
            ("Reorder step_1, step_2, step_3 in ascending order", eng.get_text() == expected),
        ]

    levels.append(
        Level(
            id="vim_2_5",
            track_id=2,
            track_name="VIM Precision & Power",
            number=5,
            title="Yank, Cut & Put (dd p V y)",
            mode="vim",
            description=(
                "Deleted or yanked lines go into the unnamed register:\n"
                "  dd = cut line   |  yy = yank (copy) line   |  V = visual line mode\n"
                "  p  = paste below/after   |  P = paste above/before"
            ),
            objective_text="Swap step_2 and step_1 so the lines appear in order: step_1, step_2, step_3.",
            hint="Press dd on line 1 to cut step_2, then p to paste it below step_1.",
            optimal_solution="ddp (3 keys)",
            par_keystrokes=5,
            xp_reward=90,
            setup_fn=setup_2_5,
            check_fn=check_2_5,
        )
    )

    def setup_2_6() -> VimEngine:
        return VimEngine.from_text(
            "let a = 1\n"
            "let b = 2\n"
            "let c = 3\n"
            "let d = 4",
            row=0,
            col=0,
        )

    def check_2_6(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        expected = "let a = 1;\nlet b = 2;\nlet c = 3;\nlet d = 4;"
        ok = eng.get_text() == expected and eng.mode == "NORMAL"
        return ok, [
            ("Append ';' to all 4 lines", eng.get_text() == expected),
            ("Return to NORMAL mode", eng.mode == "NORMAL"),
        ]

    levels.append(
        Level(
            id="vim_2_6",
            track_id=2,
            track_name="VIM Precision & Power",
            number=6,
            title="The Power of Dot (.)",
            mode="vim",
            description=(
                "The '.' command repeats your last edit in a single keystroke!\n"
                "Make one clean change (like A;<Esc>), move with j, and press '.' to repeat it."
            ),
            objective_text="Add a trailing semicolon ';' to all 4 lines using the dot command.",
            hint="Press A;<Esc> on line 1, then repeat j. three times.",
            optimal_solution="A;<Esc>j.j.j. (9 keys)",
            par_keystrokes=10,
            xp_reward=110,
            setup_fn=setup_2_6,
            check_fn=check_2_6,
        )
    )

    def setup_2_7() -> VimEngine:
        return VimEngine.from_text(
            "alpha\n"
            "beta\n"
            "gamma\n"
            "delta",
            row=0,
            col=0,
        )

    def check_2_7(eng: VimEngine) -> tuple[bool, list[tuple[str, bool]]]:
        expected = '"alpha"\n"beta"\n"gamma"\n"delta"'
        macro_ok = len(eng.macros) > 0
        text_ok = eng.get_text() == expected and eng.mode == "NORMAL"
        return (macro_ok and text_ok), [
            ("Record a macro using q<reg>...q", macro_ok),
            ("Wrap all 4 words in double quotes", text_ok),
        ]

    levels.append(
        Level(
            id="vim_2_7",
            track_id=2,
            track_name="VIM Precision & Power",
            number=7,
            title="Macro Automation (qa ... q @a)",
            mode="vim",
            description=(
                "Macros record any sequence of keystrokes for effortless batch editing:\n"
                "  qa = start recording into register 'a'\n"
                "  q  = stop recording\n"
                "  @a = play macro 'a'  |  3@a = play 3 times"
            ),
            objective_text="Record a macro that wraps a word in double quotes and moves down, then replay it on all 4 lines.",
            hint="Type qaI\"<Esc>A\"<Esc>jq then 3@a.",
            optimal_solution='qaI"<Esc>A"<Esc>jq3@a (13 keys)',
            par_keystrokes=18,
            xp_reward=130,
            setup_fn=setup_2_7,
            check_fn=check_2_7,
        )
    )

    return levels
