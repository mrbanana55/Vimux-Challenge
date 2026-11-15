"""Persistence layer for VIM & TMUX Quest."""

from vim_tmux_quest.db.database import Database, get_default_db_path

__all__ = ["Database", "get_default_db_path"]
