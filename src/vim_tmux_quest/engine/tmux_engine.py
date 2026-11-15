"""Deterministic TMUX simulation engine with split-tree layout and VIM pane routing."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Callable

from vim_tmux_quest.engine.key_utils import normalize_key
from vim_tmux_quest.engine.vim_engine import VimEngine


@dataclass
class TmuxPane:
    """Single TMUX pane, optionally hosting an embedded VimEngine."""

    pane_id: int
    title: str = "zsh"
    content_lines: list[str] = field(default_factory=lambda: ["$ "])
    width_pct: int = 100
    height_pct: int = 100
    vim_engine: VimEngine | None = None

    in_copy_mode: bool = False
    copy_row: int = 0
    copy_col: int = 0
    copy_anchor: tuple[int, int] | None = None

    def get_lines(self) -> list[str]:
        if self.vim_engine is not None:
            return self.vim_engine.lines
        return self.content_lines


@dataclass
class SplitNode:
    """Binary/N-ary split tree node for pane layouts."""

    pane: TmuxPane | None = None
    direction: str | None = None  # "vertical" (left|right, %) or "horizontal" (top/bottom, ")
    children: list[SplitNode] = field(default_factory=list)
    ratios: list[int] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return self.pane is not None

    def iter_leaves(self) -> list[TmuxPane]:
        if self.pane is not None:
            return [self.pane]
        leaves: list[TmuxPane] = []
        for child in self.children:
            leaves.extend(child.iter_leaves())
        return leaves

    def find_leaf_and_parent(
        self, pane_id: int, parent: SplitNode | None = None
    ) -> tuple[SplitNode | None, SplitNode | None, int]:
        if self.pane is not None:
            if self.pane.pane_id == pane_id:
                return self, parent, -1
            return None, None, -1
        for idx, child in enumerate(self.children):
            if child.pane is not None and child.pane.pane_id == pane_id:
                return child, self, idx
            found, p, child_idx = child.find_leaf_and_parent(pane_id, self)
            if found is not None:
                return found, p, child_idx
        return None, None, -1

    def find_path(self, pane_id: int) -> list[tuple[SplitNode, int]] | None:
        """Return list of (ancestor_node, child_index) leading to pane_id."""
        if self.pane is not None:
            return [] if self.pane.pane_id == pane_id else None
        for idx, child in enumerate(self.children):
            sub = child.find_path(pane_id)
            if sub is not None:
                return [(self, idx), *sub]
        return None


@dataclass
class TmuxWindow:
    """Single TMUX window containing a split tree of panes."""

    window_id: int
    index: int
    name: str
    root: SplitNode
    active_pane_id: int
    zoomed_pane_id: int | None = None

    def panes(self) -> list[TmuxPane]:
        return self.root.iter_leaves()

    def active_pane(self) -> TmuxPane:
        for p in self.panes():
            if p.pane_id == self.active_pane_id:
                return p
        panes = self.panes()
        self.active_pane_id = panes[0].pane_id
        return panes[0]

    def compute_pane_rects(self) -> dict[int, tuple[float, float, float, float]]:
        """Compute (x, y, width, height) in 0..100 percentages and sync pane sizes."""
        rects: dict[int, tuple[float, float, float, float]] = {}

        def _walk(node: SplitNode, x: float, y: float, w: float, h: float) -> None:
            if node.pane is not None:
                rects[node.pane.pane_id] = (x, y, w, h)
                node.pane.width_pct = round(w)
                node.pane.height_pct = round(h)
                return
            total = sum(node.ratios) or len(node.children)
            offset = 0.0
            for child, ratio in zip(node.children, node.ratios):
                frac = ratio / total
                if node.direction == "vertical":
                    cw = w * frac
                    _walk(child, x + offset, y, cw, h)
                    offset += cw
                else:
                    ch = h * frac
                    _walk(child, x, y + offset, w, ch)
                    offset += ch

        _walk(self.root, 0.0, 0.0, 100.0, 100.0)
        return rects


@dataclass
class TmuxSession:
    """TMUX session holding one or more windows."""

    name: str
    windows: list[TmuxWindow] = field(default_factory=list)
    active_window_index: int = 0

    @property
    def active_window(self) -> TmuxWindow:
        self.active_window_index = max(0, min(self.active_window_index, len(self.windows) - 1))
        return self.windows[self.active_window_index]


@dataclass
class TmuxEngine:
    """Self-contained TMUX state machine supporting sessions, windows, panes, copy-mode, and VIM panes."""

    sessions: list[TmuxSession] = field(default_factory=list)
    active_session_index: int = 0
    prefix_key: str = "Ctrl-b"
    prefix_active: bool = False

    prompt_mode: str | None = None
    prompt_buffer: str = ""
    picker_index: int = 0

    detached: bool = False
    paste_buffer: str = ""
    keystroke_count: int = 0
    key_history: list[str] = field(default_factory=list)
    command_history: list[str] = field(default_factory=list)
    status_message: str = ""

    _next_pane_id: int = 1
    _next_window_id: int = 1
    _copy_pending_g: bool = False
    on_change_callback: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        self.prefix_key = normalize_key(self.prefix_key)
        if not self.sessions:
            pane = self._alloc_pane(title="zsh", content_lines=["user@dev:~/project$ "])
            win = self._alloc_window(index=0, name="zsh", root=SplitNode(pane=pane), active_pane_id=pane.pane_id)
            self.sessions = [TmuxSession(name="main", windows=[win], active_window_index=0)]
        else:
            max_p = 0
            max_w = 0
            for s in self.sessions:
                for w in s.windows:
                    max_w = max(max_w, w.window_id + 1)
                    w.compute_pane_rects()
                    for p in w.panes():
                        max_p = max(max_p, p.pane_id + 1)
            self._next_pane_id = max(self._next_pane_id, max_p)
            self._next_window_id = max(self._next_window_id, max_w)

    def _alloc_pane(
        self,
        title: str = "zsh",
        content_lines: list[str] | None = None,
        vim_engine: VimEngine | None = None,
    ) -> TmuxPane:
        pid = self._next_pane_id
        self._next_pane_id += 1
        lines = list(content_lines) if content_lines is not None else [f"[pane {pid}] $ "]
        return TmuxPane(pane_id=pid, title=title, content_lines=lines, vim_engine=vim_engine)

    def _alloc_window(
        self, index: int, name: str, root: SplitNode, active_pane_id: int
    ) -> TmuxWindow:
        wid = self._next_window_id
        self._next_window_id += 1
        win = TmuxWindow(
            window_id=wid,
            index=index,
            name=name,
            root=root,
            active_pane_id=active_pane_id,
        )
        win.compute_pane_rects()
        return win

    @property
    def active_session(self) -> TmuxSession:
        self.active_session_index = max(0, min(self.active_session_index, len(self.sessions) - 1))
        return self.sessions[self.active_session_index]

    @property
    def active_window(self) -> TmuxWindow:
        return self.active_session.active_window

    @property
    def active_pane(self) -> TmuxPane:
        return self.active_window.active_pane()

    def set_prefix_key(self, prefix: str) -> None:
        self.prefix_key = normalize_key(prefix)

    # ------------------------------------------------------------------
    # Key Dispatch
    # ------------------------------------------------------------------
    def handle_key(self, raw_key: str, character: str | None = None) -> None:
        key = normalize_key(raw_key, character)
        self.keystroke_count += 1
        self.key_history.append(key)
        if len(self.key_history) > 50:
            self.key_history = self.key_history[-50:]

        if self.prompt_mode is not None:
            self._handle_prompt(key)
        elif self.prefix_active:
            self.prefix_active = False
            self._handle_prefix_command(key)
        elif key == self.prefix_key:
            self.prefix_active = True
            self.status_message = f"PREFIX ({self.prefix_key})"
        elif self.active_pane.in_copy_mode:
            self._handle_copy_mode(key)
        elif self.active_pane.vim_engine is not None:
            # Forward directly without double-counting inside TmuxEngine,
            # while keeping vim_engine's own keystroke_count updated via _dispatch_key.
            self.active_pane.vim_engine._dispatch_key(key, internal=False)
        else:
            # Plain shell pane typing preview
            pane = self.active_pane
            if key == "Enter":
                pane.content_lines.append("$ ")
            elif key == "BS":
                if pane.content_lines and len(pane.content_lines[-1]) > 2:
                    pane.content_lines[-1] = pane.content_lines[-1][:-1]
            elif len(key) == 1 and key.isprintable():
                if not pane.content_lines:
                    pane.content_lines.append("$ ")
                pane.content_lines[-1] += key

        if self.on_change_callback is not None:
            self.on_change_callback()

    def handle_keys(self, keys: list[str]) -> None:
        for k in keys:
            self.handle_key(k)

    # ------------------------------------------------------------------
    # Prefix Commands
    # ------------------------------------------------------------------
    def _handle_prefix_command(self, key: str) -> None:
        self.command_history.append(key)
        if key == "%":
            self.split_pane("vertical")
        elif key == '"':
            self.split_pane("horizontal")
        elif key == "o":
            self.cycle_pane()
        elif key in ("Up", "Down", "Left", "Right", "h", "j", "k", "l"):
            dir_map = {
                "Up": "up", "k": "up",
                "Down": "down", "j": "down",
                "Left": "left", "h": "left",
                "Right": "right", "l": "right",
            }
            self.focus_direction(dir_map[key])
        elif key == "x":
            self.close_active_pane()
        elif key == "z":
            self.toggle_zoom()
        elif key == "{":
            self.swap_pane(-1)
        elif key == "}":
            self.swap_pane(1)
        elif key == "!":
            self.break_pane()
        elif key in ("Ctrl-Up", "Alt-Up", "K"):
            self.resize_active_pane("up", 10)
        elif key in ("Ctrl-Down", "Alt-Down", "J"):
            self.resize_active_pane("down", 10)
        elif key in ("Ctrl-Left", "Alt-Left", "H"):
            self.resize_active_pane("left", 10)
        elif key in ("Ctrl-Right", "Alt-Right", "L"):
            self.resize_active_pane("right", 10)
        elif key == "c":
            self.create_window()
        elif key == "n":
            self.next_window()
        elif key == "p":
            self.previous_window()
        elif len(key) == 1 and key.isdigit():
            self.select_window_index(int(key))
        elif key == ",":
            self.prompt_mode = "rename-window"
            self.prompt_buffer = ""
        elif key == "&":
            self.kill_active_window()
        elif key == "d":
            self.detached = True
            self.status_message = f"Detached from session '{self.active_session.name}'"
        elif key == "$":
            self.prompt_mode = "rename-session"
            self.prompt_buffer = ""
        elif key == "s":
            self.prompt_mode = "session-picker"
            self.picker_index = self.active_session_index
        elif key == "[":
            self.enter_copy_mode()
        elif key == "]":
            self.paste_into_active_pane()
        elif key == ":":
            self.prompt_mode = "command"
            self.prompt_buffer = ""
        elif key == "Esc":
            self.status_message = ""
        else:
            self.status_message = f"Unknown TMUX binding: {self.prefix_key} {key}"

    # ------------------------------------------------------------------
    # Pane Operations
    # ------------------------------------------------------------------
    def split_pane(self, direction: str) -> TmuxPane:
        """Split the active pane. direction: 'vertical' (%) or 'horizontal' (\")."""
        win = self.active_window
        win.zoomed_pane_id = None
        leaf, parent, idx = win.root.find_leaf_and_parent(win.active_pane_id)
        assert leaf is not None
        new_pane = self._alloc_pane(
            title="zsh",
            content_lines=[f"[pane {self._next_pane_id}] $ "],
        )
        new_leaf = SplitNode(pane=new_pane)

        if parent is not None and parent.direction == direction:
            parent.children.insert(idx + 1, new_leaf)
            # Split the active child's existing ratio in half
            old_ratio = parent.ratios[idx]
            half1 = max(10, old_ratio // 2)
            half2 = max(10, old_ratio - half1)
            parent.ratios[idx] = half1
            parent.ratios.insert(idx + 1, half2)
        else:
            old_pane = leaf.pane
            leaf.pane = None
            leaf.direction = direction
            leaf.children = [SplitNode(pane=old_pane), new_leaf]
            leaf.ratios = [50, 50]

        win.active_pane_id = new_pane.pane_id
        win.compute_pane_rects()
        self.status_message = f"Split {direction} -> pane {new_pane.pane_id}"
        return new_pane

    def cycle_pane(self) -> None:
        win = self.active_window
        panes = win.panes()
        if len(panes) <= 1:
            return
        ids = [p.pane_id for p in panes]
        idx = ids.index(win.active_pane_id)
        win.active_pane_id = ids[(idx + 1) % len(ids)]
        win.zoomed_pane_id = None

    def focus_direction(self, direction: str) -> None:
        win = self.active_window
        rects = win.compute_pane_rects()
        if len(rects) <= 1:
            return
        ax, ay, aw, ah = rects[win.active_pane_id]
        acx, acy = ax + aw / 2, ay + ah / 2
        best_id: int | None = None
        best_score = float("inf")

        for pid, (x, y, w, h) in rects.items():
            if pid == win.active_pane_id:
                continue
            cx, cy = x + w / 2, y + h / 2
            if direction == "left" and x + w <= ax + 0.5:
                overlap = min(ay + ah, y + h) - max(ay, y)
                if overlap > 0:
                    score = (ax - (x + w)) * 10 + abs(cy - acy)
                    if score < best_score:
                        best_score = score
                        best_id = pid
            elif direction == "right" and x >= ax + aw - 0.5:
                overlap = min(ay + ah, y + h) - max(ay, y)
                if overlap > 0:
                    score = (x - (ax + aw)) * 10 + abs(cy - acy)
                    if score < best_score:
                        best_score = score
                        best_id = pid
            elif direction == "up" and y + h <= ay + 0.5:
                overlap = min(ax + aw, x + w) - max(ax, x)
                if overlap > 0:
                    score = (ay - (y + h)) * 10 + abs(cx - acx)
                    if score < best_score:
                        best_score = score
                        best_id = pid
            elif direction == "down" and y >= ay + ah - 0.5:
                overlap = min(ax + aw, x + w) - max(ax, x)
                if overlap > 0:
                    score = (y - (ay + ah)) * 10 + abs(cx - acx)
                    if score < best_score:
                        best_score = score
                        best_id = pid

        if best_id is not None:
            win.active_pane_id = best_id
            win.zoomed_pane_id = None

    def close_active_pane(self) -> None:
        win = self.active_window
        panes = win.panes()
        if len(panes) <= 1:
            if len(self.active_session.windows) > 1:
                self.kill_active_window()
            else:
                self.status_message = "Cannot close the only remaining pane"
            return

        active_id = win.active_pane_id
        ids = [p.pane_id for p in panes]
        old_pos = ids.index(active_id)
        fallback_id = ids[old_pos - 1] if old_pos > 0 else ids[1]

        _, parent, idx = win.root.find_leaf_and_parent(active_id)
        if parent is not None:
            parent.children.pop(idx)
            parent.ratios.pop(idx)
            if len(parent.children) == 1:
                sole = parent.children[0]
                parent.pane = sole.pane
                parent.direction = sole.direction
                parent.children = sole.children
                parent.ratios = sole.ratios
        win.active_pane_id = fallback_id
        win.zoomed_pane_id = None
        win.compute_pane_rects()
        self.status_message = f"Closed pane {active_id}"

    def toggle_zoom(self) -> None:
        win = self.active_window
        if win.zoomed_pane_id == win.active_pane_id:
            win.zoomed_pane_id = None
            self.status_message = "Unzoomed pane"
        else:
            win.zoomed_pane_id = win.active_pane_id
            self.status_message = f"Zoomed pane {win.active_pane_id}"

    def _replace_leaf_pane(self, node: SplitNode, target_id: int, replacement: TmuxPane) -> bool:
        if node.pane is not None:
            if node.pane.pane_id == target_id:
                node.pane = replacement
                return True
            return False
        return any(self._replace_leaf_pane(c, target_id, replacement) for c in node.children)

    def swap_pane(self, offset: int) -> None:
        win = self.active_window
        panes = win.panes()
        if len(panes) <= 1:
            return
        ids = [p.pane_id for p in panes]
        idx = ids.index(win.active_pane_id)
        other_idx = (idx + offset) % len(panes)
        p1 = panes[idx]
        p2 = panes[other_idx]

        # Temporarily assign unique sentinel to swap safely
        sentinel = TmuxPane(pane_id=-1)
        self._replace_leaf_pane(win.root, p1.pane_id, sentinel)
        self._replace_leaf_pane(win.root, p2.pane_id, p1)
        self._replace_leaf_pane(win.root, -1, p2)
        win.compute_pane_rects()
        self.status_message = f"Swapped pane {p1.pane_id} with {p2.pane_id}"

    def break_pane(self) -> None:
        win = self.active_window
        panes = win.panes()
        if len(panes) <= 1:
            self.status_message = "Cannot break single pane"
            return
        pane = win.active_pane()
        # Remove from current window without destroying the TmuxPane instance
        ids = [p.pane_id for p in panes]
        old_pos = ids.index(pane.pane_id)
        fallback_id = ids[old_pos - 1] if old_pos > 0 else ids[1]
        _, parent, idx = win.root.find_leaf_and_parent(pane.pane_id)
        if parent is not None:
            parent.children.pop(idx)
            parent.ratios.pop(idx)
            if len(parent.children) == 1:
                sole = parent.children[0]
                parent.pane = sole.pane
                parent.direction = sole.direction
                parent.children = sole.children
                parent.ratios = sole.ratios
        win.active_pane_id = fallback_id
        win.zoomed_pane_id = None
        win.compute_pane_rects()

        sess = self.active_session
        next_idx = max(w.index for w in sess.windows) + 1
        new_win = self._alloc_window(
            index=next_idx,
            name=pane.title,
            root=SplitNode(pane=pane),
            active_pane_id=pane.pane_id,
        )
        sess.windows.append(new_win)
        sess.active_window_index = len(sess.windows) - 1
        self.status_message = f"Broke pane {pane.pane_id} to window {next_idx}"

    def resize_active_pane(self, direction: str, amount: int = 10) -> None:
        win = self.active_window
        path = win.root.find_path(win.active_pane_id)
        if not path:
            return
        axis = "vertical" if direction in ("left", "right") else "horizontal"
        # Walk up from closest split ancestor matching axis
        for node, child_idx in reversed(path):
            if node.direction != axis or len(node.children) < 2:
                continue
            total = sum(node.ratios)
            if total <= 0:
                continue
            # Normalize to 100
            norm = [round(r * 100 / total) for r in node.ratios]
            norm[-1] += 100 - sum(norm)

            grow_with = direction in ("right", "down")
            neighbor_idx = child_idx + 1 if child_idx + 1 < len(norm) else child_idx - 1
            if child_idx + 1 < len(norm):
                delta = amount if grow_with else -amount
            else:
                delta = -amount if grow_with else amount

            new_cur = norm[child_idx] + delta
            new_nbr = norm[neighbor_idx] - delta
            if new_cur < 10:
                diff = 10 - new_cur
                new_cur = 10
                new_nbr -= diff
            if new_nbr < 10:
                diff = 10 - new_nbr
                new_nbr = 10
                new_cur -= diff
            norm[child_idx] = new_cur
            norm[neighbor_idx] = new_nbr
            node.ratios = norm
            win.compute_pane_rects()
            self.status_message = f"Resized pane {win.active_pane_id}"
            return

    # ------------------------------------------------------------------
    # Window Operations
    # ------------------------------------------------------------------
    def create_window(self, name: str = "zsh") -> TmuxWindow:
        sess = self.active_session
        next_idx = (max(w.index for w in sess.windows) + 1) if sess.windows else 0
        pane = self._alloc_pane(title=name)
        win = self._alloc_window(
            index=next_idx,
            name=name,
            root=SplitNode(pane=pane),
            active_pane_id=pane.pane_id,
        )
        sess.windows.append(win)
        sess.active_window_index = len(sess.windows) - 1
        self.status_message = f"Created window {next_idx}:{name}"
        return win

    def next_window(self) -> None:
        sess = self.active_session
        if sess.windows:
            sess.active_window_index = (sess.active_window_index + 1) % len(sess.windows)

    def previous_window(self) -> None:
        sess = self.active_session
        if sess.windows:
            sess.active_window_index = (sess.active_window_index - 1) % len(sess.windows)

    def select_window_index(self, index: int) -> None:
        sess = self.active_session
        for pos, win in enumerate(sess.windows):
            if win.index == index:
                sess.active_window_index = pos
                return

    def kill_active_window(self) -> None:
        sess = self.active_session
        if len(sess.windows) <= 1:
            self.status_message = "Cannot kill the last window"
            return
        sess.windows.pop(sess.active_window_index)
        sess.active_window_index = max(0, min(sess.active_window_index, len(sess.windows) - 1))

    # ------------------------------------------------------------------
    # Copy Mode & Paste
    # ------------------------------------------------------------------
    def enter_copy_mode(self) -> None:
        pane = self.active_pane
        pane.in_copy_mode = True
        pane.copy_row = 0
        pane.copy_col = 0
        pane.copy_anchor = None
        self._copy_pending_g = False
        self.status_message = "[copy mode]"

    def _handle_copy_mode(self, key: str) -> None:
        pane = self.active_pane
        lines = pane.get_lines() or [""]

        if key in ("q", "Esc"):
            pane.in_copy_mode = False
            pane.copy_anchor = None
            self._copy_pending_g = False
            self.status_message = ""
            return

        if key == "g":
            if self._copy_pending_g:
                self._copy_pending_g = False
                pane.copy_row = 0
                pane.copy_col = 0
            else:
                self._copy_pending_g = True
            return
        self._copy_pending_g = False

        if key in (" ", "v"):
            if pane.copy_anchor is None:
                pane.copy_anchor = (pane.copy_row, pane.copy_col)
                self.status_message = "[copy mode: selecting]"
            else:
                pane.copy_anchor = None
            return

        if key in ("Enter", "y"):
            if pane.copy_anchor is not None:
                start, end = sorted([pane.copy_anchor, (pane.copy_row, pane.copy_col)])
                sr, sc = start
                er, ec = end
                if sr == er:
                    yanked = lines[sr][sc : ec + 1]
                else:
                    parts = [lines[sr][sc:]]
                    for mid in range(sr + 1, er):
                        parts.append(lines[mid])
                    parts.append(lines[er][: ec + 1])
                    yanked = "\n".join(parts)
            else:
                yanked = lines[pane.copy_row]
            self.paste_buffer = yanked
            pane.in_copy_mode = False
            pane.copy_anchor = None
            self.status_message = f"Copied {len(yanked)} chars"
            return

        max_r = len(lines) - 1
        if key in ("j", "Down"):
            pane.copy_row = min(max_r, pane.copy_row + 1)
        elif key in ("k", "Up"):
            pane.copy_row = max(0, pane.copy_row - 1)
        elif key in ("h", "Left"):
            pane.copy_col = max(0, pane.copy_col - 1)
        elif key in ("l", "Right"):
            line_len = len(lines[pane.copy_row])
            pane.copy_col = min(max(0, line_len - 1), pane.copy_col + 1)
        elif key == "0":
            pane.copy_col = 0
        elif key == "^":
            line = lines[pane.copy_row]
            pane.copy_col = next((i for i, ch in enumerate(line) if not ch.isspace()), 0)
        elif key == "$":
            pane.copy_col = max(0, len(lines[pane.copy_row]) - 1)
        elif key == "G":
            pane.copy_row = max_r
            pane.copy_col = 0
        elif key == "w":
            line = lines[pane.copy_row]
            c = pane.copy_col
            while c < len(line) and not line[c].isspace():
                c += 1
            while c < len(line) and line[c].isspace():
                c += 1
            if c < len(line):
                pane.copy_col = c
            elif pane.copy_row < max_r:
                pane.copy_row += 1
                pane.copy_col = 0
        elif key == "b":
            line = lines[pane.copy_row]
            c = max(0, pane.copy_col - 1)
            while c > 0 and line[c].isspace():
                c -= 1
            while c > 0 and not line[c - 1].isspace():
                c -= 1
            pane.copy_col = c

        cur_len = len(lines[pane.copy_row])
        pane.copy_col = max(0, min(pane.copy_col, max(0, cur_len - 1)))

    def paste_into_active_pane(self) -> None:
        if not self.paste_buffer:
            self.status_message = "Paste buffer is empty"
            return
        pane = self.active_pane
        if pane.vim_engine is not None:
            for ch in self.paste_buffer:
                if ch == "\n":
                    pane.vim_engine._dispatch_key("Enter", internal=True)
                else:
                    pane.vim_engine._dispatch_key(ch, internal=True)
        else:
            for line in self.paste_buffer.splitlines():
                pane.content_lines.append(line)
        self.status_message = "Pasted buffer"

    # ------------------------------------------------------------------
    # Prompts & Ex-style TMUX Commands
    # ------------------------------------------------------------------
    def _handle_prompt(self, key: str) -> None:
        if self.prompt_mode == "session-picker":
            if key in ("Esc", "q"):
                self.prompt_mode = None
                return
            if key in ("j", "Down"):
                self.picker_index = (self.picker_index + 1) % len(self.sessions)
                return
            if key in ("k", "Up"):
                self.picker_index = (self.picker_index - 1) % len(self.sessions)
                return
            if key == "Enter":
                self.active_session_index = self.picker_index
                self.prompt_mode = None
                self.status_message = f"Switched to session '{self.active_session.name}'"
                return
            if len(key) == 1 and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(self.sessions):
                    self.active_session_index = idx
                    self.prompt_mode = None
                    self.status_message = f"Switched to session '{self.active_session.name}'"
            return

        if key == "Esc":
            self.prompt_mode = None
            self.prompt_buffer = ""
            return
        if key == "BS":
            self.prompt_buffer = self.prompt_buffer[:-1]
            return
        if key == "Enter":
            mode = self.prompt_mode
            text = self.prompt_buffer.strip()
            self.prompt_mode = None
            self.prompt_buffer = ""
            if mode == "rename-window" and text:
                self.active_window.name = text
                self.status_message = f"Renamed window to '{text}'"
            elif mode == "rename-session" and text:
                self.active_session.name = text
                self.status_message = f"Renamed session to '{text}'"
            elif mode == "command" and text:
                self._execute_tmux_command(text)
            return
        if len(key) == 1 and key.isprintable():
            self.prompt_buffer += key

    def _execute_tmux_command(self, cmd_line: str) -> None:
        try:
            tokens = shlex.split(cmd_line)
        except ValueError:
            tokens = cmd_line.split()
        if not tokens:
            return
        cmd = tokens[0]
        args = tokens[1:]

        if cmd in ("new-session", "new"):
            name = f"session-{len(self.sessions)}"
            if "-s" in args:
                i = args.index("-s")
                if i + 1 < len(args):
                    name = args[i + 1]
            pane = self._alloc_pane(title="zsh")
            win = self._alloc_window(index=0, name="zsh", root=SplitNode(pane=pane), active_pane_id=pane.pane_id)
            self.sessions.append(TmuxSession(name=name, windows=[win], active_window_index=0))
            self.active_session_index = len(self.sessions) - 1
            self.status_message = f"Created session '{name}'"
        elif cmd in ("split-window", "splitw"):
            direction = "horizontal" if "-v" in args else "vertical"
            self.split_pane(direction)
        elif cmd in ("kill-pane", "killp"):
            self.close_active_pane()
        elif cmd in ("kill-window", "killw"):
            self.kill_active_window()
        elif cmd in ("rename-window", "renamew") and args:
            self.active_window.name = args[0]
            self.status_message = f"Renamed window to '{args[0]}'"
        elif cmd in ("rename-session", "rename") and args:
            self.active_session.name = args[0]
            self.status_message = f"Renamed session to '{args[0]}'"
        elif cmd in ("resize-pane", "resizep"):
            amount = 10
            for a in args:
                if a.isdigit():
                    amount = int(a)
            if "-U" in args:
                self.resize_active_pane("up", amount)
            elif "-D" in args:
                self.resize_active_pane("down", amount)
            elif "-L" in args:
                self.resize_active_pane("left", amount)
            elif "-R" in args:
                self.resize_active_pane("right", amount)
        else:
            self.status_message = f"Unknown TMUX command: :{cmd_line}"
