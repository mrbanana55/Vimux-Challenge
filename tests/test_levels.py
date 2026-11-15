"""Smoke tests verifying every campaign level starts incomplete and is solvable within par."""

from vim_tmux_quest.curriculum import DRILL_BANK, get_all_levels, get_level_by_id
from vim_tmux_quest.curriculum.drills import select_next_drill
from vim_tmux_quest.db.database import Database

SOLUTIONS: dict[str, list[str]] = {
    # Track 1: VIM Foundations
    "vim_1_1": ["j", "j", "j", "l", "l", "l", "l", "l", "l"],
    "vim_1_2": ["j", "j", "$", "b"],
    "vim_1_3": ["0", "^", "j", "$"],
    "vim_1_4": ["G", "g", "g", "5", "G"],
    "vim_1_5": ["I", *list("const "), "Esc", "A", ";", "Esc"],
    "vim_1_6": ["O", *list("# Check server health"), "Esc", "j", "o", *list("    return True"), "Esc"],
    "vim_1_7": ["x", "j", "d", "d"],
    # Track 2: VIM Precision & Power
    "vim_2_1": ["j", "2", "d", "d", "4", "w"],
    "vim_2_2": ["t", ")", "r", "3"],
    "vim_2_3": ["d", "w", "f", '"', ";", "l", "d", "$", "j", "0", "f", "p", "c", "w", *list("active"), "Esc"],
    "vim_2_4": ["c", "i", '"', *list("valid_key"), "Esc", "j", "d", "i", "("],
    "vim_2_5": ["d", "d", "p"],
    "vim_2_6": ["A", ";", "Esc", "j", ".", "j", ".", "j", "."],
    "vim_2_7": ["q", "a", "I", '"', "Esc", "A", '"', "Esc", "j", "q", "3", "@", "a"],
    # Track 3: TMUX Foundations
    "tmux_3_1": ["Ctrl-b", "%"],
    "tmux_3_2": ["Ctrl-b", "%", "Ctrl-b", '"'],
    "tmux_3_3": ["Ctrl-b", "o", "Ctrl-b", "o"],
    "tmux_3_4": ["Ctrl-b", "o", "Ctrl-b", "z"],
    "tmux_3_5": ["Ctrl-b", "o", "Ctrl-b", "x"],
    "tmux_3_6": ["Ctrl-b", "c", "Ctrl-b", "c", "Ctrl-b", "0"],
    "tmux_3_7": ["Ctrl-b", "c", "Ctrl-b", ",", *list("logs"), "Enter"],
    # Track 4: TMUX Mastery & Combo
    "tmux_4_1": ["Ctrl-b", "{"],
    "tmux_4_2": ["Ctrl-b", "L", "Ctrl-b", "L"],
    "tmux_4_3": ["Ctrl-b", "$", *list("prod"), "Enter", "Ctrl-b", "s", "j", "Enter"],
    "tmux_4_4": ["Ctrl-b", "[", "j", "Enter", "Ctrl-b", "o", "Ctrl-b", "]"],
    "combo_4_5": ["Ctrl-b", "%", "Ctrl-b", "o", "j", "f", ":", "c", "i", '"', "o", "k", "Esc"],
    "combo_4_6": [
        "f", "5", "c", "i", "w", *list("8080"), "Esc", ":", "w", "Enter",
        "Ctrl-b", "o",
        "f", "5", "c", "i", "w", *list("8080"), "Esc", ":", "w", "Enter",
    ],
    "combo_4_7": [
        "Ctrl-b", ",", *list("hotfix"), "Enter",
        "Ctrl-b", "x",
        "j", "d", "d",
        "c", "i", '"', *list("https://prod.io"), "Esc",
        ":", "w", "Enter",
    ],
}


def test_all_28_levels_exist_and_solvable_within_par():
    levels = get_all_levels()
    assert len(levels) == 28
    assert set(SOLUTIONS.keys()) == {lvl.id for lvl in levels}

    for lvl in levels:
        engine = lvl.setup_fn()
        initially_done, checklist = lvl.check_fn(engine)
        assert initially_done is False, f"{lvl.id} started already completed!"
        assert len(checklist) >= 1

        engine.handle_keys(SOLUTIONS[lvl.id])
        done, checklist_after = lvl.check_fn(engine)
        assert done is True, f"{lvl.id} failed solution check: {checklist_after}"
        assert engine.keystroke_count <= lvl.par_keystrokes, (
            f"{lvl.id} took {engine.keystroke_count} > par {lvl.par_keystrokes}"
        )


def test_drill_bank_and_selector(tmp_path):
    assert len(DRILL_BANK) >= 35
    db = Database(db_path=tmp_path / "drill_sel.db")
    d1 = select_next_drill(db, tool_filter="vim")
    assert d1.tool == "vim"
    d2 = select_next_drill(db, tool_filter="tmux")
    assert d2.tool == "tmux"
    assert get_level_by_id("combo_4_7") is not None
