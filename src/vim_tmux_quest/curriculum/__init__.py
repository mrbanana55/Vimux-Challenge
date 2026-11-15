"""Curriculum levels and drill bank for VIM & TMUX Quest."""

from vim_tmux_quest.curriculum.combo_levels import get_combo_levels
from vim_tmux_quest.curriculum.drills import DRILL_BANK, DrillItem, select_next_drill
from vim_tmux_quest.curriculum.models import Level, TrackInfo
from vim_tmux_quest.curriculum.tmux_levels import get_tmux_levels
from vim_tmux_quest.curriculum.vim_levels import get_vim_levels

TRACKS: list[TrackInfo] = [
    TrackInfo(1, "VIM Foundations", "Core navigation, modes, and basic text edits."),
    TrackInfo(2, "VIM Precision & Power", "Counts, find motions, operators, text objects, and macros."),
    TrackInfo(3, "TMUX Foundations", "Prefix key, splits, pane navigation, zoom, and windows."),
    TrackInfo(4, "TMUX Mastery & Combo", "Resizing, sessions, copy-mode, and real VIM+TMUX workflows."),
]


def get_all_levels() -> list[Level]:
    """Return all 28 campaign levels ordered by track and level number."""
    return [*get_vim_levels(), *get_tmux_levels(), *get_combo_levels()]


def get_level_by_id(level_id: str) -> Level | None:
    """Look up a campaign level by its unique ID."""
    for lvl in get_all_levels():
        if lvl.id == level_id:
            return lvl
    return None


__all__ = [
    "Level",
    "TrackInfo",
    "DrillItem",
    "TRACKS",
    "DRILL_BANK",
    "get_all_levels",
    "get_level_by_id",
    "select_next_drill",
]
