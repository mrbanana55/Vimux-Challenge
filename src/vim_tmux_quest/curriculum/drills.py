"""Flashcard & speed-drill command bank with spaced-weakness weighting."""

from __future__ import annotations

import random

from vim_tmux_quest.curriculum.models import DrillItem
from vim_tmux_quest.db.database import Database


def _prefix_variants(key: str) -> list[list[str]]:
    return [["Ctrl-b", key], ["Ctrl-a", key]]


DRILL_BANK: list[DrillItem] = [
    # VIM Motions
    DrillItem("vim_left", "vim", "Motions", "Move cursor one character LEFT", [["h"]], "h", "h moves left one character."),
    DrillItem("vim_down", "vim", "Motions", "Move cursor one line DOWN", [["j"]], "j", "j moves down one line."),
    DrillItem("vim_up", "vim", "Motions", "Move cursor one line UP", [["k"]], "k", "k moves up one line."),
    DrillItem("vim_right", "vim", "Motions", "Move cursor one character RIGHT", [["l"]], "l", "l moves right one character."),
    DrillItem("vim_word_next", "vim", "Motions", "Jump to the START of the next word", [["w"]], "w", "w jumps forward to the start of the next word."),
    DrillItem("vim_word_back", "vim", "Motions", "Jump to the START of the previous word", [["b"]], "b", "b jumps backward to the start of the previous word."),
    DrillItem("vim_word_end", "vim", "Motions", "Jump to the END of the current/next word", [["e"]], "e", "e lands on the last character of a word."),
    DrillItem("vim_line_0", "vim", "Motions", "Jump to column 0 (very start of line)", [["0"]], "0", "0 goes to column 0 regardless of indentation."),
    DrillItem("vim_line_caret", "vim", "Motions", "Jump to the first non-blank character on line", [["^"]], "^", "^ skips leading whitespace to the first non-blank char."),
    DrillItem("vim_line_eol", "vim", "Motions", "Jump to the END of the current line", [["$"]], "$", "$ moves to the last character of the line."),
    DrillItem("vim_file_top", "vim", "Motions", "Jump to the FIRST line of the file", [["g", "g"]], "gg", "gg teleports to line 1."),
    DrillItem("vim_file_bot", "vim", "Motions", "Jump to the LAST line of the file", [["G"]], "G", "G teleports to the final line of the file."),
    DrillItem("vim_match_bracket", "vim", "Motions", "Jump to matching bracket () [] {}", [["%"]], "%", "% bounces between matching opening and closing brackets."),
    DrillItem("vim_find_char", "vim", "Search", "Jump ON the next '(' character on this line", [["f", "("]], "f(", "f<char> finds the next occurrence forward on the line."),
    DrillItem("vim_till_char", "vim", "Search", "Jump right BEFORE the next ';' on this line", [["t", ";"]], "t;", "t<char> lands one character before the target."),
    DrillItem("vim_repeat_find", "vim", "Search", "Repeat the last f/t/F/T character search", [[";"]], ";", "; repeats the last inline find in the same direction."),
    DrillItem("vim_search_word", "vim", "Search", "Search forward for the word under cursor", [["*"]], "*", "* searches for the next occurrence of the word under the cursor."),
    # VIM Insert & Edits
    DrillItem("vim_insert_start", "vim", "Insert", "Insert at the first non-blank char of the line", [["I"]], "I", "I jumps to the first non-blank character and enters Insert mode."),
    DrillItem("vim_append_eol", "vim", "Insert", "Append text at the END of the line", [["A"]], "A", "A jumps to the end of the line and enters Insert mode."),
    DrillItem("vim_open_below", "vim", "Insert", "Open a new blank line BELOW and enter Insert mode", [["o"]], "o", "o inserts a line below and puts you in Insert mode."),
    DrillItem("vim_open_above", "vim", "Insert", "Open a new blank line ABOVE and enter Insert mode", [["O"]], "O", "O inserts a line above and puts you in Insert mode."),
    DrillItem("vim_del_char", "vim", "Editing", "Delete the single character under the cursor", [["x"]], "x", "x deletes the character at the cursor."),
    DrillItem("vim_undo", "vim", "Editing", "Undo the last change", [["u"]], "u", "u undoes the last edit."),
    DrillItem("vim_redo", "vim", "Editing", "Redo the last undone change", [["Ctrl-r"]], "Ctrl-r", "Ctrl-r redoes an undone change."),
    DrillItem("vim_dot", "vim", "Editing", "Repeat the last edit command", [["."]], ".", ". (dot) replays your most recent change."),
    # VIM Operators & Text Objects
    DrillItem("vim_dd", "vim", "Operators", "Delete (cut) the entire current line", [["d", "d"]], "dd", "Doubling an operator applies it to the whole line: dd."),
    DrillItem("vim_yy", "vim", "Operators", "Yank (copy) the entire current line", [["y", "y"]], "yy", "yy yanks the full current line into the register."),
    DrillItem("vim_paste_after", "vim", "Operators", "Paste (put) yanked/deleted text after/below", [["p"]], "p", "p pastes after cursor or below current line."),
    DrillItem("vim_dw", "vim", "Operators", "Delete from cursor to the start of next word", [["d", "w"]], "dw", "dw combines delete (d) + word motion (w)."),
    DrillItem("vim_d_eol", "vim", "Operators", "Delete from cursor to the end of the line", [["d", "$"], ["D"]], "d$ (or D)", "d$ or D deletes through the end of the current line."),
    DrillItem("vim_ciw", "vim", "Text Objects", "Change the entire word under the cursor", [["c", "i", "w"]], "ciw", "ciw changes 'inner word' from anywhere inside the word."),
    DrillItem("vim_di_quotes", "vim", "Text Objects", 'Delete everything inside double quotes "..."', [["d", "i", '"']], 'di"', 'di" deletes inside quotes without removing the quotes.'),
    DrillItem("vim_ci_parens", "vim", "Text Objects", "Change everything inside parentheses (...)", [["c", "i", "("], ["c", "i", ")"]], "ci(", "ci( clears inside (...) and enters Insert mode."),
    DrillItem("vim_da_braces", "vim", "Text Objects", "Delete around curly braces {...} including braces", [["d", "a", "{"], ["d", "a", "}"]], "da{", "da{ deletes the braces and everything inside them."),
    DrillItem("vim_visual_line", "vim", "Visual", "Enter Visual Line mode to select whole lines", [["V"]], "V", "V starts line-wise visual selection."),
    # TMUX Commands
    DrillItem("tmux_split_v", "tmux", "Panes", "TMUX: Split pane vertically (left | right)", _prefix_variants("%"), "Prefix + %", "% draws a vertical divider between left/right panes."),
    DrillItem("tmux_split_h", "tmux", "Panes", "TMUX: Split pane horizontally (top / bottom)", _prefix_variants('"'), 'Prefix + "', '" draws a horizontal divider between top/bottom panes.'),
    DrillItem("tmux_cycle_pane", "tmux", "Panes", "TMUX: Cycle focus to the next pane", _prefix_variants("o"), "Prefix + o", "Prefix + o cycles through panes in order."),
    DrillItem("tmux_zoom_pane", "tmux", "Panes", "TMUX: Toggle full-screen zoom on active pane", _prefix_variants("z"), "Prefix + z", "Prefix + z zooms/unzooms the active pane."),
    DrillItem("tmux_close_pane", "tmux", "Panes", "TMUX: Close the active pane", _prefix_variants("x"), "Prefix + x", "Prefix + x closes the current pane."),
    DrillItem("tmux_swap_prev", "tmux", "Panes", "TMUX: Swap active pane with previous pane", _prefix_variants("{"), "Prefix + {", "Prefix + { swaps the active pane backward."),
    DrillItem("tmux_break_pane", "tmux", "Panes", "TMUX: Break active pane out into a new window", _prefix_variants("!"), "Prefix + !", "Prefix + ! promotes a pane into its own window."),
    DrillItem("tmux_new_win", "tmux", "Windows", "TMUX: Create a new window", _prefix_variants("c"), "Prefix + c", "Prefix + c opens a new window in the current session."),
    DrillItem("tmux_next_win", "tmux", "Windows", "TMUX: Switch to the NEXT window", _prefix_variants("n"), "Prefix + n", "Prefix + n jumps to the next window."),
    DrillItem("tmux_prev_win", "tmux", "Windows", "TMUX: Switch to the PREVIOUS window", _prefix_variants("p"), "Prefix + p", "Prefix + p jumps to the previous window."),
    DrillItem("tmux_rename_win", "tmux", "Windows", "TMUX: Rename the current window", _prefix_variants(","), "Prefix + ,", "Prefix + , opens the rename-window prompt."),
    DrillItem("tmux_rename_sess", "tmux", "Sessions", "TMUX: Rename the current session", _prefix_variants("$"), "Prefix + $", "Prefix + $ opens the rename-session prompt."),
    DrillItem("tmux_list_sess", "tmux", "Sessions", "TMUX: Open interactive session switcher", _prefix_variants("s"), "Prefix + s", "Prefix + s opens the session picker tree."),
    DrillItem("tmux_detach", "tmux", "Sessions", "TMUX: Detach from the current session", _prefix_variants("d"), "Prefix + d", "Prefix + d detaches while leaving processes running."),
    DrillItem("tmux_copy_mode", "tmux", "Copy Mode", "TMUX: Enter copy-mode to scroll & yank text", _prefix_variants("["), "Prefix + [", "Prefix + [ enters VIM-style scroll/copy mode."),
    DrillItem("tmux_paste", "tmux", "Copy Mode", "TMUX: Paste from the TMUX paste buffer", _prefix_variants("]"), "Prefix + ]", "Prefix + ] pastes the most recently copied buffer."),
]


def get_drills_for_filter(tool_filter: str = "all", db: Database | None = None) -> list[DrillItem]:
    if tool_filter == "vim":
        return [d for d in DRILL_BANK if d.tool == "vim"]
    if tool_filter == "tmux":
        return [d for d in DRILL_BANK if d.tool == "tmux"]
    if tool_filter == "weak" and db is not None:
        weak_rows = db.get_weakest_commands(limit=15)
        weak_ids = {r["command_key"] for r in weak_rows if r["mistake_count"] > 0}
        filtered = [d for d in DRILL_BANK if d.id in weak_ids]
        if filtered:
            return filtered
    return list(DRILL_BANK)


def select_next_drill(
    db: Database,
    tool_filter: str = "all",
    exclude_id: str | None = None,
    rng: random.Random | None = None,
) -> DrillItem:
    """Select the next drill weighted toward unpracticed or high-mistake commands."""
    pool = get_drills_for_filter(tool_filter, db)
    if len(pool) > 1 and exclude_id is not None:
        pool = [d for d in pool if d.id != exclude_id]

    stats_by_key = {row["command_key"]: row for row in db.get_command_stats()}
    weights: list[float] = []
    for item in pool:
        row = stats_by_key.get(item.id)
        if row is None:
            weights.append(3.0)
        else:
            succ = int(row["success_count"])
            mist = int(row["mistake_count"])
            weight = 1.0 + (mist * 3.0) / max(1, succ + mist) + (1.5 / (1 + succ))
            weights.append(weight)

    chooser = rng or random
    return chooser.choices(pool, weights=weights, k=1)[0]
