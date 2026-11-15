"""Dataclasses for campaign tracks, levels, and drills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TrackInfo:
    id: int
    name: str
    description: str


@dataclass(frozen=True)
class Level:
    id: str
    track_id: int
    track_name: str
    number: int
    title: str
    mode: str  # "vim", "tmux", "combo"
    description: str
    objective_text: str
    hint: str
    optimal_solution: str
    par_keystrokes: int
    xp_reward: int
    setup_fn: Callable[[], Any]
    check_fn: Callable[[Any], tuple[bool, list[tuple[str, bool]]]]


@dataclass(frozen=True)
class DrillItem:
    id: str
    tool: str  # "vim" | "tmux"
    category: str
    prompt: str
    accepted_keys: list[list[str]]
    display_answer: str
    explanation: str
