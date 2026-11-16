"""Interactive gameplay screen running VIM, TMUX, or Combo simulations."""

from __future__ import annotations

import time

from textual import events
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Static

from vim_tmux_quest.curriculum import get_all_levels, get_level_by_id
from vim_tmux_quest.curriculum.models import Level
from vim_tmux_quest.engine.key_utils import normalize_key
from vim_tmux_quest.engine.tmux_engine import TmuxEngine
from vim_tmux_quest.engine.vim_engine import VimEngine
from vim_tmux_quest.ui.widgets.hud import HudWidget
from vim_tmux_quest.ui.widgets.modals import LevelCompleteModal
from vim_tmux_quest.ui.widgets.tmux_view import TmuxView
from vim_tmux_quest.ui.widgets.vim_view import VimView


class GameScreen(Screen):
    """Plays a single VIM, TMUX, or Combo level with live checklist & scoring."""

    def __init__(self, level_id: str) -> None:
        super().__init__()
        lvl = get_level_by_id(level_id)
        if lvl is None:
            raise ValueError(f"Unknown level ID: {level_id}")
        self.level: Level = lvl
        self.engine: VimEngine | TmuxEngine = lvl.setup_fn()
        self.show_hint: bool = False
        self.hint_used: bool = False
        self._start_mono: float = time.monotonic()
        self._completed: bool = False
        self._vim_view: VimView | None = None
        self._tmux_view: TmuxView | None = None

    def compose(self):
        with Horizontal(id="game-topbar"):
            yield Static("", id="topbar-title")
            yield Static("", id="topbar-metrics")
        with Horizontal(id="game-body"):
            yield Container(id="workspace-container")
            yield HudWidget(id="hud-container")

    async def on_mount(self) -> None:
        await self._load_level(self.level)

    async def _load_level(self, level: Level) -> None:
        self.level = level
        self.engine = level.setup_fn()
        if isinstance(self.engine, TmuxEngine):
            prefix = self.app.db.get_setting("tmux_prefix", "ctrl+b") or "ctrl+b"  # type: ignore[attr-defined]
            self.engine.set_prefix_key(prefix)

        default_hints = (self.app.db.get_setting("show_hints", "0") == "1")  # type: ignore[attr-defined]
        self.show_hint = default_hints
        self.hint_used = default_hints
        self._start_mono = time.monotonic()
        self._completed = False

        workspace = self.query_one("#workspace-container", Container)
        await workspace.remove_children()
        self._vim_view = None
        self._tmux_view = None

        if isinstance(self.engine, VimEngine):
            self._vim_view = VimView(self.engine)
            await workspace.mount(self._vim_view)
            self._vim_view.focus()
        else:
            self._tmux_view = TmuxView(self.engine)
            await workspace.mount(self._tmux_view)
            self._tmux_view.focus()

        await self._refresh_ui()

    async def _refresh_ui(self) -> None:
        if self._vim_view is not None and isinstance(self.engine, VimEngine):
            self._vim_view.refresh_buffer()
            mode_badge = self.engine.mode
        elif self._tmux_view is not None and isinstance(self.engine, TmuxEngine):
            await self._tmux_view.sync_engine(self.engine)
            if self.engine.prefix_active:
                mode_badge = "PREFIX"
            elif self.engine.active_pane.in_copy_mode:
                mode_badge = "COPY MODE"
            elif self.engine.active_pane.vim_engine is not None:
                mode_badge = f"TMUX + VIM:{self.engine.active_pane.vim_engine.mode}"
            else:
                mode_badge = "TMUX"
        else:
            mode_badge = ""

        self.query_one("#topbar-title", Static).update(
            f"Track {self.level.track_id}: {self.level.track_name}  —  {self.level.number}. {self.level.title}"
        )
        self.query_one("#topbar-metrics", Static).update(
            f"[{mode_badge}]   Keys: {self.engine.keystroke_count} / Par: {self.level.par_keystrokes}"
        )

        _, checklist = self.level.check_fn(self.engine)
        hud = self.query_one("#hud-container", HudWidget)
        hud.update_state(self.level, checklist, self.engine.key_history, self.show_hint)

    async def on_key(self, event: events.Key) -> None:
        if event.key == "f1":
            event.stop()
            event.prevent_default()
            self.show_hint = not self.show_hint
            if self.show_hint:
                self.hint_used = True
            await self._refresh_ui()
            return

        if event.key == "f2":
            event.stop()
            event.prevent_default()
            await self._load_level(self.level)
            return

        if event.key == "f3":
            event.stop()
            event.prevent_default()
            self.app.pop_screen()
            return

        if self._completed:
            return

        event.stop()
        event.prevent_default()
        key = normalize_key(event.key, event.character)
        if not key:
            return
        self.engine.handle_key(event.key, event.character)
        await self._refresh_ui()

        done, _ = self.level.check_fn(self.engine)
        if done and not self._completed:
            await self._finish_level()

    async def _finish_level(self) -> None:
        self._completed = True
        keystrokes = self.engine.keystroke_count
        elapsed_ms = max(1, int((time.monotonic() - self._start_mono) * 1000))
        par = self.level.par_keystrokes
        if keystrokes <= par and not self.hint_used:
            stars = 3
        elif keystrokes <= max(par + 2, int(par * 1.5)):
            stars = 2
        else:
            stars = 1

        res = self.app.db.record_level_attempt(  # type: ignore[attr-defined]
            level_id=self.level.id,
            completed=True,
            keystrokes=keystrokes,
            time_ms=elapsed_ms,
            stars=stars,
            xp_earned=self.level.xp_reward,
        )

        all_levels = get_all_levels()
        idx = next((i for i, l in enumerate(all_levels) if l.id == self.level.id), -1)
        next_level = all_levels[idx + 1] if 0 <= idx + 1 < len(all_levels) else None

        def _on_modal_close(choice: str | None) -> None:
            if choice == "next" and next_level is not None:
                self.run_worker(self._load_level(next_level))
            elif choice == "retry":
                self.run_worker(self._load_level(self.level))
            else:
                self.app.pop_screen()

        self.app.push_screen(
            LevelCompleteModal(
                level=self.level,
                stars=stars,
                keystrokes=keystrokes,
                time_ms=elapsed_ms,
                xp_gained=int(res["xp_delta"]),
                has_next_level=next_level is not None,
            ),
            callback=_on_modal_close,
        )
