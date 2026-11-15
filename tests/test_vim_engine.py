"""Unit tests for the VIM simulation engine."""

from vim_tmux_quest.engine.vim_engine import VimEngine


def test_basic_hjkl_and_bounds():
    eng = VimEngine.from_text("hello\nworld\n!")
    eng.handle_keys(["l", "l", "j", "l", "k", "h"])
    assert (eng.row, eng.col) == (0, 2)
    eng.handle_keys(["j", "j"])
    assert (eng.row, eng.col) == (2, 0)


def test_word_motions_w_b_e():
    eng = VimEngine.from_text("alpha beta_two gamma")
    eng.handle_key("w")
    assert eng.col == 6
    eng.handle_key("e")
    assert eng.col == 13
    eng.handle_key("w")
    assert eng.col == 15
    eng.handle_key("b")
    assert eng.col == 6


def test_line_and_file_motions():
    eng = VimEngine.from_text("    first\nsecond\nthird\nfourth\nfifth")
    eng.handle_keys(["0"])
    assert eng.col == 0
    eng.handle_keys(["^"])
    assert eng.col == 4
    eng.handle_keys(["$"])
    assert eng.col == 8
    eng.handle_keys(["G"])
    assert eng.row == 4
    eng.handle_keys(["g", "g"])
    assert eng.row == 0
    eng.handle_keys(["3", "G"])
    assert eng.row == 2


def test_find_char_and_repeat():
    eng = VimEngine.from_text("a(b, c, d)")
    eng.handle_keys(["f", ","])
    assert eng.col == 3
    eng.handle_keys([";"])
    assert eng.col == 6
    eng.handle_keys([","])
    assert eng.col == 3
    eng.handle_keys(["t", ")"])
    assert eng.col == 8


def test_search_and_bracket_match():
    eng = VimEngine.from_text("foo(bar, [baz])\nnext foo")
    eng.handle_keys(["/", "f", "o", "o", "Enter"])
    assert (eng.row, eng.col) == (1, 5)
    eng.handle_keys(["N"])
    assert (eng.row, eng.col) == (0, 0)
    eng.handle_keys(["f", "(", "%"])
    assert (eng.row, eng.col) == (0, 14)


def test_insert_append_open_and_edits():
    eng = VimEngine.from_text("mid")
    eng.handle_keys(["I", "a", " ", "Esc", "A", "!", "Esc"])
    assert eng.get_text() == "a mid!"
    assert eng.mode == "NORMAL"

    eng.handle_keys(["o", *list("below"), "Esc", "k", "O", *list("above"), "Esc"])
    assert eng.get_text() == "above\na mid!\nbelow"

    eng.handle_keys(["0", "x", "r", "X"])
    assert eng.lines[0] == "Xove"


def test_operators_text_objects_and_yank_put():
    eng = VimEngine.from_text('msg = "old value"\ncall(x, y)\none two three')
    eng.handle_keys(["c", "i", '"', "n", "e", "w", "Esc"])
    assert eng.lines[0] == 'msg = "new"'

    eng.handle_keys(["j", "d", "i", "("])
    assert eng.lines[1] == "call()"

    eng.handle_keys(["j", "0", "d", "w"])
    assert eng.lines[2] == "two three"

    eng.handle_keys(["d", "$"])
    assert eng.lines[2] == ""

    eng.handle_keys(["u"])
    assert eng.lines[2] == "two three"
    eng.handle_keys(["Ctrl-r"])
    assert eng.lines[2] == ""


def test_visual_mode_dot_repeat_and_macros():
    eng = VimEngine.from_text("one\ntwo\nthree")
    eng.handle_keys(["v", "e", "y", "j", "0", "p"])
    assert eng.lines[1] == "tonewo"

    eng = VimEngine.from_text("a\nb\nc")
    eng.handle_keys(["A", ";", "Esc", "j", ".", "j", "."])
    assert eng.get_text() == "a;\nb;\nc;"
    assert eng.keystroke_count == 7

    eng = VimEngine.from_text("x\ny\nz")
    eng.handle_keys(["q", "a", "I", "[", "Esc", "A", "]", "Esc", "j", "q", "2", "@", "a"])
    assert eng.get_text() == "[x]\n[y]\n[z]"
    assert eng.keystroke_count == 13


def test_ex_commands_w_and_q():
    eng = VimEngine.from_text("hello")
    eng.handle_keys([":", "w", "q", "Enter"])
    assert eng.saved is True
    assert eng.quitted is True
