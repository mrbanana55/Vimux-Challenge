"""Deterministic VIM simulation engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from vim_tmux_quest.engine.key_utils import normalize_key

BRACKET_PAIRS = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{"}
OPEN_BRACKETS = {"(", "[", "{"}
CLOSE_BRACKETS = {")", "]", "}"}
TEXT_OBJ_PAIRS = {
    '"': ('"', '"'),
    "'": ("'", "'"),
    "(": ("(", ")"),
    ")": ("(", ")"),
    "{": ("{", "}"),
    "}": ("{", "}"),
    "[": ("[", "]"),
    "]": ("[", "]"),
}


def _char_class(ch: str) -> int:
    if ch.isspace():
        return 0
    if ch.isalnum() or ch == "_":
        return 1
    return 2


@dataclass
class VimEngine:
    """Self-contained VIM editor state machine."""

    lines: list[str] = field(default_factory=lambda: [""])
    row: int = 0
    col: int = 0
    mode: str = "NORMAL"  # NORMAL, INSERT, VISUAL, VISUAL_LINE, COMMAND
    visual_start: tuple[int, int] | None = None

    pending_count: str = ""
    pending_op: str = ""
    command_prefix: str = ":"
    command_buffer: str = ""

    last_find: tuple[str, str] | None = None
    search_pattern: str = ""
    search_direction: int = 1

    registers: dict[str, tuple[str, bool]] = field(default_factory=dict)
    undo_stack: list[tuple[list[str], int, int]] = field(default_factory=list)
    redo_stack: list[tuple[list[str], int, int]] = field(default_factory=list)

    recording_register: str | None = None
    macro_buffer: list[str] = field(default_factory=list)
    macros: dict[str, list[str]] = field(default_factory=dict)
    last_macro_register: str | None = None
    in_macro: bool = False

    last_change_keys: list[str] = field(default_factory=list)
    current_change_keys: list[str] = field(default_factory=list)
    tracking_change: bool = False
    in_repeat: bool = False

    keystroke_count: int = 0
    key_history: list[str] = field(default_factory=list)
    status_message: str = ""
    saved: bool = False
    quitted: bool = False
    preferred_col: int = 0
    on_change_callback: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        if not self.lines:
            self.lines = [""]
        self._clamp_cursor()
        self.preferred_col = self.col

    @classmethod
    def from_text(cls, text: str, row: int = 0, col: int = 0) -> VimEngine:
        lines = text.splitlines() if text else [""]
        if text.endswith("\n"):
            lines.append("")
        return cls(lines=lines, row=row, col=col)

    def get_text(self) -> str:
        return "\n".join(self.lines)

    # ------------------------------------------------------------------
    # Cursor & Undo Helpers
    # ------------------------------------------------------------------
    def _max_col(self, row: int | None = None) -> int:
        r = self.row if row is None else row
        line = self.lines[r]
        if self.mode == "INSERT":
            return len(line)
        return max(0, len(line) - 1)

    def _clamp_cursor(self) -> None:
        if not self.lines:
            self.lines = [""]
        self.row = max(0, min(self.row, len(self.lines) - 1))
        self.col = max(0, min(self.col, self._max_col()))

    def _save_undo(self) -> None:
        if self.in_repeat or self.in_macro:
            return
        self.undo_stack.append((list(self.lines), self.row, self.col))
        self.redo_stack.clear()

    def _undo(self) -> None:
        if not self.undo_stack:
            self.status_message = "Already at oldest change"
            return
        self.redo_stack.append((list(self.lines), self.row, self.col))
        lines, row, col = self.undo_stack.pop()
        self.lines = list(lines)
        self.row = row
        self.col = col
        self._clamp_cursor()
        self.preferred_col = self.col
        self.status_message = "Undo"

    def _redo(self) -> None:
        if not self.redo_stack:
            self.status_message = "Already at newest change"
            return
        self.undo_stack.append((list(self.lines), self.row, self.col))
        lines, row, col = self.redo_stack.pop()
        self.lines = list(lines)
        self.row = row
        self.col = col
        self._clamp_cursor()
        self.preferred_col = self.col
        self.status_message = "Redo"

    def _reset_pending(self) -> None:
        self.pending_count = ""
        self.pending_op = ""

    def _finish_change(self) -> None:
        if self.tracking_change and not self.in_repeat and self.current_change_keys:
            self.last_change_keys = list(self.current_change_keys)
        self.tracking_change = False
        self.current_change_keys = []

    def _abort_change(self) -> None:
        self.tracking_change = False
        self.current_change_keys = []

    # ------------------------------------------------------------------
    # Public Key Dispatch
    # ------------------------------------------------------------------
    def handle_key(self, raw_key: str, character: str | None = None) -> None:
        key = normalize_key(raw_key, character)
        self._dispatch_key(key, internal=False)

    def handle_keys(self, keys: list[str]) -> None:
        for key in keys:
            self.handle_key(key)

    def _dispatch_key(self, key: str, internal: bool = False) -> None:
        if not internal:
            self.keystroke_count += 1
            self.key_history.append(key)
            if len(self.key_history) > 50:
                self.key_history = self.key_history[-50:]

        # Macro recording intercept (only in normal/insert/visual/command except stopping 'q')
        if (
            not internal
            and self.recording_register is not None
            and not (self.mode == "NORMAL" and self.pending_op == "" and key == "q")
        ):
            self.macro_buffer.append(key)

        if self.tracking_change and not internal:
            self.current_change_keys.append(key)

        if self.mode == "INSERT":
            self._handle_insert(key)
        elif self.mode == "COMMAND":
            self._handle_command(key)
        elif self.mode in ("VISUAL", "VISUAL_LINE"):
            self._handle_visual(key)
        else:
            self._handle_normal(key)

        if self.on_change_callback is not None:
            self.on_change_callback()

    # ------------------------------------------------------------------
    # INSERT & COMMAND Modes
    # ------------------------------------------------------------------
    def _handle_insert(self, key: str) -> None:
        if key == "Esc":
            self.mode = "NORMAL"
            if self.col > 0:
                self.col -= 1
            self._clamp_cursor()
            self.preferred_col = self.col
            self._finish_change()
            return

        if key == "BS":
            if self.col > 0:
                line = self.lines[self.row]
                self.lines[self.row] = line[: self.col - 1] + line[self.col :]
                self.col -= 1
            elif self.row > 0:
                prev_len = len(self.lines[self.row - 1])
                self.lines[self.row - 1] += self.lines.pop(self.row)
                self.row -= 1
                self.col = prev_len
            self.preferred_col = self.col
            return

        if key == "Enter":
            line = self.lines[self.row]
            before = line[: self.col]
            after = line[self.col :]
            self.lines[self.row] = before
            self.lines.insert(self.row + 1, after)
            self.row += 1
            self.col = 0
            self.preferred_col = 0
            return

        if key == "Tab":
            key = "    "

        if key == "Left":
            self.col = max(0, self.col - 1)
        elif key == "Right":
            self.col = min(len(self.lines[self.row]), self.col + 1)
        elif key == "Up":
            if self.row > 0:
                self.row -= 1
                self.col = min(self.col, len(self.lines[self.row]))
        elif key == "Down":
            if self.row < len(self.lines) - 1:
                self.row += 1
                self.col = min(self.col, len(self.lines[self.row]))
        elif len(key) >= 1 and (len(key) == 1 or key == "    ") and key.isprintable():
            line = self.lines[self.row]
            self.lines[self.row] = line[: self.col] + key + line[self.col :]
            self.col += len(key)
            self.preferred_col = self.col

    def _handle_command(self, key: str) -> None:
        if key == "Esc":
            self.mode = "NORMAL"
            self.command_buffer = ""
            self.status_message = ""
            return
        if key == "BS":
            if self.command_buffer:
                self.command_buffer = self.command_buffer[:-1]
            else:
                self.mode = "NORMAL"
            return
        if key == "Enter":
            cmd = self.command_buffer
            prefix = self.command_prefix
            self.command_buffer = ""
            self.mode = "NORMAL"
            if prefix == ":":
                self._execute_ex_command(cmd)
            else:
                self.search_pattern = cmd
                self.search_direction = 1 if prefix == "/" else -1
                if cmd:
                    pos = self._find_search_match(self.search_direction)
                    if pos is not None:
                        self.row, self.col = pos
                        self.preferred_col = self.col
                    else:
                        self.status_message = f"Pattern not found: {cmd}"
            return
        if len(key) == 1 and key.isprintable():
            self.command_buffer += key

    def _execute_ex_command(self, cmd: str) -> None:
        stripped = cmd.strip()
        if not stripped:
            return
        if stripped in ("w", "write"):
            self.saved = True
            self.status_message = "Written"
        elif stripped in ("q", "q!", "quit"):
            self.quitted = True
            self.status_message = "Quit"
        elif stripped in ("wq", "x", "wq!"):
            self.saved = True
            self.quitted = True
            self.status_message = "Written & Quit"
        elif stripped.isdigit():
            target = max(1, min(int(stripped), len(self.lines))) - 1
            self.row = target
            self.col = self._first_non_blank(self.row)
            self.preferred_col = self.col
        else:
            self.status_message = f"Unknown command: :{stripped}"

    # ------------------------------------------------------------------
    # Motion Calculations
    # ------------------------------------------------------------------
    def _first_non_blank(self, row: int) -> int:
        line = self.lines[row]
        for idx, ch in enumerate(line):
            if not ch.isspace():
                return idx
        return 0

    def _move_word_forward(self, row: int, col: int, big_word: bool = False) -> tuple[int, int]:
        line = self.lines[row]
        n_lines = len(self.lines)

        def cls(ch: str) -> int:
            if ch.isspace():
                return 0
            return 1 if big_word else _char_class(ch)

        if col < len(line):
            start_cls = cls(line[col])
            if start_cls != 0:
                while col < len(line) and cls(line[col]) == start_cls:
                    col += 1
            while col < len(line) and cls(line[col]) == 0:
                col += 1
            if col < len(line):
                return row, col

        # Wrap to next non-empty or next line
        r = row + 1
        while r < n_lines:
            l = self.lines[r]
            if not l:
                return r, 0
            c = 0
            while c < len(l) and l[c].isspace():
                c += 1
            if c < len(l):
                return r, c
            r += 1
        return row, max(0, len(line) - 1)

    def _move_word_end(self, row: int, col: int, big_word: bool = False) -> tuple[int, int]:
        n_lines = len(self.lines)

        def cls(ch: str) -> int:
            if ch.isspace():
                return 0
            return 1 if big_word else _char_class(ch)

        r, c = row, col + 1
        while r < n_lines:
            line = self.lines[r]
            while c < len(line) and cls(line[c]) == 0:
                c += 1
            if c < len(line):
                target_cls = cls(line[c])
                while c + 1 < len(line) and cls(line[c + 1]) == target_cls:
                    c += 1
                return r, c
            r += 1
            c = 0
        return row, max(0, len(self.lines[row]) - 1)

    def _move_word_backward(self, row: int, col: int, big_word: bool = False) -> tuple[int, int]:
        def cls(ch: str) -> int:
            if ch.isspace():
                return 0
            return 1 if big_word else _char_class(ch)

        r, c = row, col - 1
        while r >= 0:
            line = self.lines[r]
            if c < 0:
                r -= 1
                if r >= 0:
                    c = len(self.lines[r]) - 1
                    if c < 0:
                        return r, 0
                continue
            while c >= 0 and cls(line[c]) == 0:
                c -= 1
            if c >= 0:
                target_cls = cls(line[c])
                while c - 1 >= 0 and cls(line[c - 1]) == target_cls:
                    c -= 1
                return r, c
            r -= 1
            if r >= 0:
                c = len(self.lines[r]) - 1
                if c < 0:
                    return r, 0
        return 0, 0

    def _find_char_on_line(self, row: int, col: int, mode: str, ch: str, count: int) -> int | None:
        line = self.lines[row]
        idx = col
        for _ in range(count):
            if mode in ("f", "t"):
                found = line.find(ch, idx + 1)
                if found == -1:
                    return None
                idx = found
            else:
                found = line.rfind(ch, 0, idx)
                if found == -1:
                    return None
                idx = found
        if mode == "t":
            return max(col, idx - 1)
        if mode == "T":
            return min(col, idx + 1)
        return idx

    def _find_matching_bracket(self, row: int, col: int) -> tuple[int, int] | None:
        line = self.lines[row]
        if not line:
            return None
        # Find bracket at or after cursor on current line
        c = col
        if c >= len(line) or line[c] not in BRACKET_PAIRS:
            found = None
            for i in range(col, len(line)):
                if line[i] in BRACKET_PAIRS:
                    found = i
                    break
            if found is None:
                return None
            c = found

        ch = line[c]
        partner = BRACKET_PAIRS[ch]
        depth = 0
        if ch in OPEN_BRACKETS:
            for r in range(row, len(self.lines)):
                cur = self.lines[r]
                start_c = c if r == row else 0
                for j in range(start_c, len(cur)):
                    if cur[j] == ch:
                        depth += 1
                    elif cur[j] == partner:
                        depth -= 1
                        if depth == 0:
                            return r, j
        else:
            for r in range(row, -1, -1):
                cur = self.lines[r]
                end_c = c if r == row else len(cur) - 1
                for j in range(end_c, -1, -1):
                    if cur[j] == ch:
                        depth += 1
                    elif cur[j] == partner:
                        depth -= 1
                        if depth == 0:
                            return r, j
        return None

    def _move_paragraph(self, row: int, direction: int, count: int) -> int:
        r = row
        n = len(self.lines)
        for _ in range(count):
            if direction > 0:
                while r < n - 1 and not self.lines[r].strip():
                    r += 1
                while r < n - 1 and self.lines[r].strip():
                    r += 1
            else:
                while r > 0 and not self.lines[r].strip():
                    r -= 1
                while r > 0 and self.lines[r].strip():
                    r -= 1
        return max(0, min(r, n - 1))

    def _find_search_match(self, direction: int) -> tuple[int, int] | None:
        if not self.search_pattern:
            return None
        pat = self.search_pattern
        n = len(self.lines)
        if direction >= 0:
            # Forward from (row, col + 1), wrapping around
            for offset in range(n + 1):
                r = (self.row + offset) % n
                start = self.col + 1 if offset == 0 else 0
                idx = self.lines[r].find(pat, start)
                if idx != -1:
                    return r, idx
        else:
            for offset in range(n + 1):
                r = (self.row - offset) % n
                end = self.col if offset == 0 else len(self.lines[r])
                idx = self.lines[r].rfind(pat, 0, end)
                if idx != -1:
                    return r, idx
        return None

    def _word_under_cursor(self) -> str:
        line = self.lines[self.row]
        if not line or self.col >= len(line):
            return ""
        if _char_class(line[self.col]) != 1:
            return ""
        start = self.col
        while start > 0 and _char_class(line[start - 1]) == 1:
            start -= 1
        end = self.col
        while end + 1 < len(line) and _char_class(line[end + 1]) == 1:
            end += 1
        return line[start : end + 1]

    def _compute_motion(
        self, motion: str, count: int, arg: str = "", for_operator: str = ""
    ) -> tuple[tuple[int, int], str, bool] | None:
        """Return (new_pos, kind, valid) where kind is 'exclusive' | 'inclusive' | 'linewise'."""
        r, c = self.row, self.col
        n_lines = len(self.lines)

        if motion in ("h", "Left"):
            return (r, max(0, c - count)), "exclusive", True
        if motion in ("l", "Right"):
            max_c = len(self.lines[r]) if for_operator else self._max_col(r)
            return (r, min(max_c, c + count)), "exclusive", True
        if motion in ("j", "Down"):
            nr = min(n_lines - 1, r + count)
            if for_operator:
                return (nr, c), "linewise", True
            nc = min(self.preferred_col, self._max_col(nr))
            return (nr, nc), "linewise", True
        if motion in ("k", "Up"):
            nr = max(0, r - count)
            if for_operator:
                return (nr, c), "linewise", True
            nc = min(self.preferred_col, self._max_col(nr))
            return (nr, nc), "linewise", True
        if motion == "0":
            return (r, 0), "exclusive", True
        if motion == "^":
            return (r, self._first_non_blank(r)), "exclusive", True
        if motion == "$":
            line = self.lines[r]
            target_c = len(line) if for_operator else max(0, len(line) - 1)
            return (r, target_c), "exclusive" if for_operator else "inclusive", True
        if motion == "G":
            nr = (n_lines - 1) if not self.pending_count else max(0, min(count - 1, n_lines - 1))
            nc = min(self._first_non_blank(nr), self._max_col(nr))
            return (nr, nc), "linewise", True
        if motion == "gg":
            nr = 0 if not self.pending_count else max(0, min(count - 1, n_lines - 1))
            nc = min(self._first_non_blank(nr), self._max_col(nr))
            return (nr, nc), "linewise", True
        if motion == "%":
            pos = self._find_matching_bracket(r, c)
            if pos is None:
                return None
            return pos, "inclusive", True
        if motion == "{":
            nr = self._move_paragraph(r, -1, count)
            return (nr, 0), "linewise", True
        if motion == "}":
            nr = self._move_paragraph(r, 1, count)
            return (nr, 0), "linewise", True
        if motion in ("w", "W"):
            big = motion == "W"
            if for_operator == "c":
                # Vim quirk: cw behaves like ce when cursor is on non-space
                line = self.lines[r]
                if c < len(line) and not line[c].isspace():
                    nr, nc = r, c
                    for _ in range(count):
                        nr, nc = self._move_word_end(nr, nc, big_word=big)
                    return (nr, nc), "inclusive", True
            nr, nc = r, c
            for _ in range(count):
                prev_r = nr
                nr, nc = self._move_word_forward(nr, nc, big_word=big)
                if for_operator in ("d", "y", "c") and nr > prev_r:
                    # Cap at end of current line when operating on last word of line
                    return (prev_r, len(self.lines[prev_r])), "exclusive", True
            return (nr, nc), "exclusive", True
        if motion in ("e", "E"):
            big = motion == "E"
            nr, nc = r, c
            for _ in range(count):
                nr, nc = self._move_word_end(nr, nc, big_word=big)
            return (nr, nc), "inclusive", True
        if motion in ("b", "B"):
            big = motion == "B"
            nr, nc = r, c
            for _ in range(count):
                nr, nc = self._move_word_backward(nr, nc, big_word=big)
            return (nr, nc), "exclusive", True
        if motion in ("f", "F", "t", "T"):
            if not arg:
                return None
            self.last_find = (motion, arg)
            nc = self._find_char_on_line(r, c, motion, arg, count)
            if nc is None:
                return None
            kind = "inclusive" if motion in ("f", "t") else "exclusive"
            return (r, nc), kind, True
        if motion in (";", ","):
            if self.last_find is None:
                return None
            f_mode, f_ch = self.last_find
            if motion == ",":
                flip = {"f": "F", "F": "f", "t": "T", "T": "t"}
                f_mode = flip[f_mode]
            nc = self._find_char_on_line(r, c, f_mode, f_ch, count)
            if nc is None:
                return None
            kind = "inclusive" if f_mode in ("f", "t") else "exclusive"
            return (r, nc), kind, True
        if motion in ("n", "N"):
            d = self.search_direction if motion == "n" else -self.search_direction
            pos = self._find_search_match(d)
            if pos is None:
                return None
            return pos, "exclusive", True
        return None

    # ------------------------------------------------------------------
    # Text Objects
    # ------------------------------------------------------------------
    def _find_text_object_range(self, inner: bool, obj: str) -> tuple[tuple[int, int], tuple[int, int], bool] | None:
        """Return ((start_row, start_col), (end_row, end_col_excl), is_linewise)."""
        r, c = self.row, self.col
        line = self.lines[r]

        if obj == "w":
            if not line:
                return None
            c = min(c, len(line) - 1)
            cls = _char_class(line[c])
            start = c
            while start > 0 and _char_class(line[start - 1]) == cls:
                start -= 1
            end = c + 1
            while end < len(line) and _char_class(line[end]) == cls:
                end += 1
            if not inner:
                if end < len(line) and line[end].isspace():
                    while end < len(line) and line[end].isspace():
                        end += 1
                elif start > 0 and line[start - 1].isspace():
                    while start > 0 and line[start - 1].isspace():
                        start -= 1
            return (r, start), (r, end), False

        if obj == "p":
            if not line.strip():
                return None
            sr = r
            while sr > 0 and self.lines[sr - 1].strip():
                sr -= 1
            er = r
            while er < len(self.lines) - 1 and self.lines[er + 1].strip():
                er += 1
            if not inner:
                while er < len(self.lines) - 1 and not self.lines[er + 1].strip():
                    er += 1
            return (sr, 0), (er, len(self.lines[er])), True

        if obj in ('"', "'"):
            quotes = [i for i, ch in enumerate(line) if ch == obj]
            if len(quotes) < 2:
                return None
            pair: tuple[int, int] | None = None
            for i in range(0, len(quotes) - 1, 2):
                s_q, e_q = quotes[i], quotes[i + 1]
                if s_q <= c <= e_q:
                    pair = (s_q, e_q)
                    break
            if pair is None:
                for i in range(0, len(quotes) - 1, 2):
                    s_q, e_q = quotes[i], quotes[i + 1]
                    if s_q >= c:
                        pair = (s_q, e_q)
                        break
            if pair is None:
                return None
            s_q, e_q = pair
            if inner:
                return (r, s_q + 1), (r, e_q), False
            return (r, s_q), (r, e_q + 1), False

        if obj in TEXT_OBJ_PAIRS:
            open_ch, close_ch = TEXT_OBJ_PAIRS[obj]
            # Search for enclosing pair across lines
            open_pos: tuple[int, int] | None = None
            depth = 0
            # Scan backwards from cursor
            for sr in range(r, -1, -1):
                cur = self.lines[sr]
                sc = c if sr == r else len(cur) - 1
                for j in range(sc, -1, -1):
                    if cur[j] == close_ch and not (sr == r and j == c and cur[j] == open_ch):
                        if not (sr == r and j == c):
                            depth += 1
                    elif cur[j] == open_ch:
                        if depth == 0:
                            open_pos = (sr, j)
                            break
                        depth -= 1
                if open_pos is not None:
                    break

            # If not inside, search forward on current line
            if open_pos is None:
                idx = line.find(open_ch, c)
                if idx == -1:
                    return None
                open_pos = (r, idx)

            # Find matching close bracket from open_pos
            depth = 0
            close_pos: tuple[int, int] | None = None
            for er in range(open_pos[0], len(self.lines)):
                cur = self.lines[er]
                sc = open_pos[1] if er == open_pos[0] else 0
                for j in range(sc, len(cur)):
                    if cur[j] == open_ch:
                        depth += 1
                    elif cur[j] == close_ch:
                        depth -= 1
                        if depth == 0:
                            close_pos = (er, j)
                            break
                if close_pos is not None:
                    break
            if close_pos is None:
                return None

            if inner:
                return (open_pos[0], open_pos[1] + 1), (close_pos[0], close_pos[1]), False
            return open_pos, (close_pos[0], close_pos[1] + 1), False

        return None

    # ------------------------------------------------------------------
    # Range Operations (Delete / Change / Yank)
    # ------------------------------------------------------------------
    def _delete_char_range(
        self, start: tuple[int, int], end_excl: tuple[int, int], store_reg: bool = True
    ) -> None:
        sr, sc = start
        er, ec = end_excl
        if (er, ec) < (sr, sc):
            sr, sc, er, ec = er, ec, sr, sc

        if sr == er:
            line = self.lines[sr]
            removed = line[sc:ec]
            self.lines[sr] = line[:sc] + line[ec:]
        else:
            chunks = [self.lines[sr][sc:]]
            for mid in range(sr + 1, er):
                chunks.append(self.lines[mid])
            chunks.append(self.lines[er][:ec])
            removed = "\n".join(chunks)
            self.lines[sr] = self.lines[sr][:sc] + self.lines[er][ec:]
            del self.lines[sr + 1 : er + 1]

        if store_reg:
            self.registers['"'] = (removed, False)
        self.row, self.col = sr, sc

    def _yank_char_range(self, start: tuple[int, int], end_excl: tuple[int, int]) -> None:
        sr, sc = start
        er, ec = end_excl
        if (er, ec) < (sr, sc):
            sr, sc, er, ec = er, ec, sr, sc
        if sr == er:
            text = self.lines[sr][sc:ec]
        else:
            chunks = [self.lines[sr][sc:]]
            for mid in range(sr + 1, er):
                chunks.append(self.lines[mid])
            chunks.append(self.lines[er][:ec])
            text = "\n".join(chunks)
        self.registers['"'] = (text, False)

    def _delete_line_range(self, sr: int, er: int, store_reg: bool = True) -> None:
        if er < sr:
            sr, er = er, sr
        sr = max(0, sr)
        er = min(len(self.lines) - 1, er)
        removed = "\n".join(self.lines[sr : er + 1])
        if store_reg:
            self.registers['"'] = (removed, True)
        del self.lines[sr : er + 1]
        if not self.lines:
            self.lines = [""]
        self.row = min(sr, len(self.lines) - 1)
        self.col = self._first_non_blank(self.row)

    def _yank_line_range(self, sr: int, er: int) -> None:
        if er < sr:
            sr, er = er, sr
        sr = max(0, sr)
        er = min(len(self.lines) - 1, er)
        self.registers['"'] = ("\n".join(self.lines[sr : er + 1]), True)

    def _apply_operator_range(
        self,
        op: str,
        start: tuple[int, int],
        end_excl: tuple[int, int],
        linewise: bool,
    ) -> None:
        if op == "y":
            if linewise:
                self._yank_line_range(start[0], end_excl[0])
            else:
                self._yank_char_range(start, end_excl)
            self.row, self.col = min(start, end_excl) if not linewise else (min(start[0], end_excl[0]), start[1])
            self._clamp_cursor()
            self._abort_change()
            return

        self._save_undo()
        if op == "d":
            if linewise:
                self._delete_line_range(start[0], end_excl[0])
            else:
                self._delete_char_range(start, end_excl)
            self._clamp_cursor()
            self.preferred_col = self.col
            self._finish_change()
        elif op == "c":
            if linewise:
                sr = min(start[0], end_excl[0])
                er = max(start[0], end_excl[0])
                self.registers['"'] = ("\n".join(self.lines[sr : er + 1]), True)
                self.lines[sr : er + 1] = [""]
                self.row, self.col = sr, 0
            else:
                self._delete_char_range(start, end_excl)
            self.mode = "INSERT"
            self._clamp_cursor()

    def _paste(self, after: bool, count: int) -> None:
        if '"' not in self.registers:
            return
        text, is_linewise = self.registers['"']
        self._save_undo()
        if is_linewise:
            new_lines = text.split("\n") * count
            insert_at = self.row + 1 if after else self.row
            self.lines[insert_at:insert_at] = new_lines
            self.row = insert_at
            self.col = self._first_non_blank(self.row)
        else:
            payload = text * count
            line = self.lines[self.row]
            pos = min(len(line), self.col + 1) if (after and line) else self.col
            if "\n" in payload:
                parts = payload.split("\n")
                head = line[:pos] + parts[0]
                tail = parts[-1] + line[pos:]
                mid = parts[1:-1]
                self.lines[self.row : self.row + 1] = [head, *mid, tail]
                self.row += len(parts) - 1
                self.col = max(0, len(parts[-1]) - 1)
            else:
                self.lines[self.row] = line[:pos] + payload + line[pos:]
                self.col = max(0, pos + len(payload) - 1)
        self._clamp_cursor()
        self.preferred_col = self.col
        self._finish_change()

    # ------------------------------------------------------------------
    # NORMAL Mode Handler
    # ------------------------------------------------------------------
    def _handle_normal(self, key: str) -> None:
        if key == "Esc":
            self._reset_pending()
            self._abort_change()
            self.status_message = ""
            return

        # Pending two-char arguments
        if self.pending_op in ("f", "F", "t", "T"):
            op = self.pending_op
            count = int(self.pending_count) if self.pending_count else 1
            self._reset_pending()
            if len(key) == 1:
                res = self._compute_motion(op, count, arg=key)
                if res:
                    (nr, nc), _, _ = res
                    self.row, self.col = nr, nc
                    self.preferred_col = self.col
            self._abort_change()
            return

        if len(self.pending_op) == 2 and self.pending_op[0] in ("d", "c", "y") and self.pending_op[1] in ("f", "F", "t", "T"):
            op, fmode = self.pending_op[0], self.pending_op[1]
            count = int(self.pending_count) if self.pending_count else 1
            self._reset_pending()
            if len(key) == 1:
                res = self._compute_motion(fmode, count, arg=key, for_operator=op)
                if res:
                    (nr, nc), kind, _ = res
                    start = (self.row, self.col)
                    end = (nr, nc)
                    if end < start:
                        start, end = end, start
                        if kind == "exclusive":
                            pass
                    if kind == "inclusive":
                        end = (end[0], end[1] + 1)
                    self._apply_operator_range(op, start, end, False)
                    return
            self._abort_change()
            return

        if self.pending_op == "r":
            count = int(self.pending_count) if self.pending_count else 1
            self._reset_pending()
            if len(key) == 1 and key.isprintable():
                line = self.lines[self.row]
                if self.col + count <= len(line):
                    self._save_undo()
                    self.lines[self.row] = (
                        line[: self.col] + (key * count) + line[self.col + count :]
                    )
                    self.col += count - 1
                    self._clamp_cursor()
                    self.preferred_col = self.col
                    self._finish_change()
                    return
            self._abort_change()
            return

        if self.pending_op == "q":
            self._reset_pending()
            if len(key) == 1 and "a" <= key <= "z":
                self.recording_register = key
                self.macro_buffer = []
                self.status_message = f"recording @{key}"
            self._abort_change()
            return

        if self.pending_op == "@":
            count = int(self.pending_count) if self.pending_count else 1
            self._reset_pending()
            reg = self.last_macro_register if key == "@" else key
            if reg and len(reg) == 1 and reg in self.macros:
                self.last_macro_register = reg
                self._play_macro(reg, count)
            self._abort_change()
            return

        if self.pending_op == "Z":
            self._reset_pending()
            if key == "Z":
                self.saved = True
                self.quitted = True
            self._abort_change()
            return

        if self.pending_op in ("di", "da", "ci", "ca", "yi", "ya"):
            op = self.pending_op[0]
            inner = self.pending_op[1] == "i"
            self._reset_pending()
            obj_range = self._find_text_object_range(inner, key)
            if obj_range is not None:
                start, end_excl, linewise = obj_range
                self._apply_operator_range(op, start, end_excl, linewise)
                return
            self._abort_change()
            return

        if self.pending_op == "g":
            count = int(self.pending_count) if self.pending_count else 1
            has_count = bool(self.pending_count)
            self._reset_pending()
            if key == "g":
                nr = 0 if not has_count else max(0, min(count - 1, len(self.lines) - 1))
                self.row = nr
                self.col = self._first_non_blank(nr)
                self.preferred_col = self.col
            self._abort_change()
            return

        if self.pending_op in ("dg", "cg", "yg"):
            op = self.pending_op[0]
            count = int(self.pending_count) if self.pending_count else 1
            has_count = bool(self.pending_count)
            self._reset_pending()
            if key == "g":
                nr = 0 if not has_count else max(0, min(count - 1, len(self.lines) - 1))
                self._apply_operator_range(op, (self.row, 0), (nr, 0), linewise=True)
                return
            self._abort_change()
            return

        # Digit accumulation for counts ('0' is motion if pending_count is empty)
        if key.isdigit() and (key != "0" or self.pending_count):
            if not self.tracking_change and not self.pending_op and not self.in_repeat and not self.in_macro:
                self.tracking_change = True
                self.current_change_keys = [key]
            self.pending_count += key
            return

        count = int(self.pending_count) if self.pending_count else 1

        # Operator pending: d, c, y
        if self.pending_op in ("d", "c", "y"):
            op = self.pending_op
            if key == op:
                # dd, cc, yy
                self._reset_pending()
                er = min(len(self.lines) - 1, self.row + count - 1)
                self._apply_operator_range(op, (self.row, 0), (er, 0), linewise=True)
                return
            if key in ("i", "a"):
                self.pending_op = op + key
                return
            if key in ("f", "F", "t", "T"):
                self.pending_op = op + key
                return
            if key == "g":
                self.pending_op = op + "g"
                return
            res = self._compute_motion(key, count, for_operator=op)
            self._reset_pending()
            if res is not None:
                (nr, nc), kind, _ = res
                if kind == "linewise":
                    self._apply_operator_range(op, (self.row, 0), (nr, 0), linewise=True)
                else:
                    start = (self.row, self.col)
                    end = (nr, nc)
                    if end < start:
                        start, end = end, start
                    elif kind == "inclusive":
                        end = (end[0], end[1] + 1)
                    self._apply_operator_range(op, start, end, linewise=False)
                return
            self._abort_change()
            return

        # Stop macro recording
        if key == "q" and self.recording_register is not None:
            reg = self.recording_register
            self.macros[reg] = list(self.macro_buffer)
            self.recording_register = None
            self.macro_buffer = []
            self.status_message = f"Recorded @{reg}"
            self._reset_pending()
            self._abort_change()
            return

        # Start operators / multi-key commands
        if key in ("d", "c", "y", "f", "F", "t", "T", "r", "g", "q", "@", "Z"):
            if key in ("d", "c", "r") and not self.tracking_change and not self.in_repeat and not self.in_macro:
                self.tracking_change = True
                self.current_change_keys = [key]
            elif key in ("y", "f", "F", "t", "T", "g", "q", "@", "Z"):
                self._abort_change()
            self.pending_op = key
            return

        # Motions
        motion_keys = {
            "h", "j", "k", "l", "Left", "Down", "Up", "Right",
            "0", "^", "$", "G", "%", "{", "}",
            "w", "W", "e", "E", "b", "B",
            ";", ",", "n", "N",
        }
        if key in motion_keys:
            res = self._compute_motion(key, count)
            self._reset_pending()
            self._abort_change()
            if res is not None:
                (nr, nc), _, _ = res
                self.row, self.col = nr, nc
                self._clamp_cursor()
                if key not in ("j", "k", "Up", "Down"):
                    self.preferred_col = self.col
                elif key == "$":
                    self.preferred_col = 10**6
            return

        # Single-key commands
        self._reset_pending()
        if key == "*":
            self._abort_change()
            word = self._word_under_cursor()
            if word:
                self.search_pattern = word
                self.search_direction = 1
                pos = self._find_search_match(1)
                if pos:
                    self.row, self.col = pos
                    self.preferred_col = self.col
            return

        if key in (":", "/", "?"):
            self._abort_change()
            self.mode = "COMMAND"
            self.command_prefix = key
            self.command_buffer = ""
            return

        if key == "v":
            self._abort_change()
            self.mode = "VISUAL"
            self.visual_start = (self.row, self.col)
            return

        if key == "V":
            self._abort_change()
            self.mode = "VISUAL_LINE"
            self.visual_start = (self.row, self.col)
            return

        if key == "u":
            self._abort_change()
            for _ in range(count):
                self._undo()
            return

        if key == "Ctrl-r":
            self._abort_change()
            for _ in range(count):
                self._redo()
            return

        if key == ".":
            self._abort_change()
            self._repeat_last_change(count)
            return

        # Mutating single-key commands (ensure change tracking started)
        if not self.tracking_change and not self.in_repeat and not self.in_macro:
            self.tracking_change = True
            self.current_change_keys = [key]

        if key in ("i", "I", "a", "A", "o", "O"):
            self._save_undo()
            self.mode = "INSERT"
            line = self.lines[self.row]
            if key == "i":
                pass
            elif key == "I":
                self.col = self._first_non_blank(self.row)
            elif key == "a":
                if line:
                    self.col = min(len(line), self.col + 1)
            elif key == "A":
                self.col = len(line)
            elif key == "o":
                self.lines.insert(self.row + 1, "")
                self.row += 1
                self.col = 0
            elif key == "O":
                self.lines.insert(self.row, "")
                self.col = 0
            self.preferred_col = self.col
            return

        if key == "x":
            line = self.lines[self.row]
            if line:
                self._save_undo()
                end = min(len(line), self.col + count)
                self.registers['"'] = (line[self.col : end], False)
                self.lines[self.row] = line[: self.col] + line[end:]
                self._clamp_cursor()
                self.preferred_col = self.col
            self._finish_change()
            return

        if key == "X":
            line = self.lines[self.row]
            if self.col > 0 and line:
                self._save_undo()
                start = max(0, self.col - count)
                self.registers['"'] = (line[start : self.col], False)
                self.lines[self.row] = line[:start] + line[self.col :]
                self.col = start
                self._clamp_cursor()
                self.preferred_col = self.col
            self._finish_change()
            return

        if key == "s":
            self._save_undo()
            line = self.lines[self.row]
            end = min(len(line), self.col + count)
            self.registers['"'] = (line[self.col : end], False)
            self.lines[self.row] = line[: self.col] + line[end:]
            self.mode = "INSERT"
            return

        if key == "S":
            self._save_undo()
            er = min(len(self.lines) - 1, self.row + count - 1)
            self.registers['"'] = ("\n".join(self.lines[self.row : er + 1]), True)
            self.lines[self.row : er + 1] = [""]
            self.col = 0
            self.mode = "INSERT"
            return

        if key == "D":
            self._save_undo()
            line = self.lines[self.row]
            self.registers['"'] = (line[self.col :], False)
            self.lines[self.row] = line[: self.col]
            self._clamp_cursor()
            self.preferred_col = self.col
            self._finish_change()
            return

        if key == "C":
            self._save_undo()
            line = self.lines[self.row]
            self.registers['"'] = (line[self.col :], False)
            self.lines[self.row] = line[: self.col]
            self.col = len(self.lines[self.row])
            self.mode = "INSERT"
            return

        if key == "Y":
            er = min(len(self.lines) - 1, self.row + count - 1)
            self._yank_line_range(self.row, er)
            self._abort_change()
            return

        if key == "J":
            if self.row < len(self.lines) - 1:
                self._save_undo()
                for _ in range(count):
                    if self.row >= len(self.lines) - 1:
                        break
                    cur = self.lines[self.row].rstrip()
                    nxt = self.lines.pop(self.row + 1).lstrip()
                    join_col = len(cur)
                    self.lines[self.row] = f"{cur} {nxt}" if (cur and nxt) else f"{cur}{nxt}"
                    self.col = join_col
                self._clamp_cursor()
                self.preferred_col = self.col
            self._finish_change()
            return

        if key == "~":
            line = self.lines[self.row]
            if line:
                self._save_undo()
                end = min(len(line), self.col + count)
                flipped = "".join(
                    ch.lower() if ch.isupper() else ch.upper()
                    for ch in line[self.col : end]
                )
                self.lines[self.row] = line[: self.col] + flipped + line[end:]
                self.col = min(self._max_col(), end)
                self.preferred_col = self.col
            self._finish_change()
            return

        if key == "p":
            self._paste(after=True, count=count)
            return

        if key == "P":
            self._paste(after=False, count=count)
            return

        self._abort_change()

    def _repeat_last_change(self, count: int) -> None:
        if not self.last_change_keys:
            return
        self._save_undo()
        self.in_repeat = True
        try:
            for _ in range(count):
                for k in self.last_change_keys:
                    self._dispatch_key(k, internal=True)
        finally:
            self.in_repeat = False
            self._reset_pending()

    def _play_macro(self, reg: str, count: int) -> None:
        keys = self.macros.get(reg)
        if not keys:
            return
        self._save_undo()
        self.in_macro = True
        try:
            for _ in range(count):
                for k in keys:
                    self._dispatch_key(k, internal=True)
        finally:
            self.in_macro = False
            self._reset_pending()

    # ------------------------------------------------------------------
    # VISUAL Mode Handler
    # ------------------------------------------------------------------
    def _visual_bounds(self) -> tuple[tuple[int, int], tuple[int, int]]:
        anchor = self.visual_start or (self.row, self.col)
        cur = (self.row, self.col)
        return (anchor, cur) if anchor <= cur else (cur, anchor)

    def _handle_visual(self, key: str) -> None:
        if key == "Esc":
            self.mode = "NORMAL"
            self.visual_start = None
            self._reset_pending()
            return

        if key == "v" and self.mode == "VISUAL":
            self.mode = "NORMAL"
            self.visual_start = None
            return
        if key == "V" and self.mode == "VISUAL_LINE":
            self.mode = "NORMAL"
            self.visual_start = None
            return
        if key in ("v", "V"):
            self.mode = "VISUAL" if key == "v" else "VISUAL_LINE"
            return

        if self.pending_op in ("vi", "va"):
            inner = self.pending_op == "vi"
            self.pending_op = ""
            obj_range = self._find_text_object_range(inner, key)
            if obj_range is not None:
                start, end_excl, linewise = obj_range
                if linewise:
                    self.mode = "VISUAL_LINE"
                self.visual_start = start
                end_col = max(0, end_excl[1] - 1)
                self.row, self.col = end_excl[0], end_col
                self._clamp_cursor()
            return

        if key in ("i", "a"):
            self.pending_op = "v" + key
            return

        if key in ("f", "F", "t", "T"):
            self.pending_op = key
            return
        if self.pending_op in ("f", "F", "t", "T"):
            fmode = self.pending_op
            self.pending_op = ""
            res = self._compute_motion(fmode, 1, arg=key)
            if res:
                (nr, nc), _, _ = res
                self.row, self.col = nr, nc
            return

        if key == "g":
            self.pending_op = "g"
            return
        if self.pending_op == "g":
            self.pending_op = ""
            if key == "g":
                self.row = 0
                self.col = self._first_non_blank(0)
            return

        if key.isdigit() and (key != "0" or self.pending_count):
            self.pending_count += key
            return

        count = int(self.pending_count) if self.pending_count else 1
        motion_keys = {
            "h", "j", "k", "l", "Left", "Down", "Up", "Right",
            "0", "^", "$", "G", "%", "{", "}",
            "w", "W", "e", "E", "b", "B", ";", ",", "n", "N",
        }
        if key in motion_keys:
            self.pending_count = ""
            res = self._compute_motion(key, count)
            if res:
                (nr, nc), _, _ = res
                self.row, self.col = nr, nc
                self._clamp_cursor()
            return

        self.pending_count = ""
        start, end = self._visual_bounds()
        is_linewise = self.mode == "VISUAL_LINE"

        if key in ("d", "x"):
            self._save_undo()
            if is_linewise:
                self._delete_line_range(start[0], end[0])
            else:
                end_excl = (end[0], min(len(self.lines[end[0]]), end[1] + 1))
                self._delete_char_range(start, end_excl)
            self.mode = "NORMAL"
            self.visual_start = None
            self._clamp_cursor()
            return

        if key == "c":
            self._save_undo()
            if is_linewise:
                self.registers['"'] = ("\n".join(self.lines[start[0] : end[0] + 1]), True)
                self.lines[start[0] : end[0] + 1] = [""]
                self.row, self.col = start[0], 0
            else:
                end_excl = (end[0], min(len(self.lines[end[0]]), end[1] + 1))
                self._delete_char_range(start, end_excl)
            self.visual_start = None
            self.mode = "INSERT"
            return

        if key == "y":
            if is_linewise:
                self._yank_line_range(start[0], end[0])
                self.row, self.col = start[0], 0
            else:
                end_excl = (end[0], min(len(self.lines[end[0]]), end[1] + 1))
                self._yank_char_range(start, end_excl)
                self.row, self.col = start
            self.mode = "NORMAL"
            self.visual_start = None
            self._clamp_cursor()
            return

        if key == "~":
            self._save_undo()
            if is_linewise:
                for r in range(start[0], end[0] + 1):
                    self.lines[r] = self.lines[r].swapcase()
            else:
                for r in range(start[0], end[0] + 1):
                    line = self.lines[r]
                    sc = start[1] if r == start[0] else 0
                    ec = (end[1] + 1) if r == end[0] else len(line)
                    self.lines[r] = line[:sc] + line[sc:ec].swapcase() + line[ec:]
            self.row, self.col = start
            self.mode = "NORMAL"
            self.visual_start = None
            self._clamp_cursor()
