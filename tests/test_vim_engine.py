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


def test_5g_and_uppercase_motions_ignore_modifiers_and_variants():
    text = "\n".join(f"line {i}" for i in range(1, 9))

    for seq in (
        ["5", "left_shift", "G"],
        ["5", "caps_lock", "G"],
        ["5", "shift+g"],
        ["5", "upper_g"],
    ):
        eng = VimEngine.from_text(text, row=2, col=0)
        eng.handle_keys(seq)
        assert eng.row == 4
        assert eng.keystroke_count == 2
        assert eng.pending_count == ""


def test_uppercase_commands_and_operators_with_modifiers():
    eng = VimEngine.from_text("l1\nl2\nl3\nl4\nl5", row=0, col=0)
    eng.handle_keys(["left_shift", "G"])
    assert eng.row == 4

    eng = VimEngine.from_text("l1\nl2\nl3\nl4\nl5", row=1, col=0)
    eng.handle_keys(["d", "left_shift", "G"])
    assert eng.get_text() == "l1"

    eng = VimEngine.from_text("l1\nl2\nl3\nl4\nl5", row=0, col=0)
    eng.handle_keys(["2", "d", "right_shift", "G"])
    assert eng.get_text() == "l3\nl4\nl5"

    eng = VimEngine.from_text("  one\ntwo\nthree\nfour\nfive\nsix", row=0, col=0)
    eng.handle_keys(["left_shift", "V", "5", "caps_lock", "G", "d"])
    assert eng.get_text() == "six"

    eng = VimEngine.from_text("  one\ntwo\nthree\nfour\nfive\nsix", row=0, col=0)
    eng.handle_keys(["V", "5", "g", "g", "d"])
    assert eng.get_text() == "six"

    eng = VimEngine.from_text("  mid", row=0, col=3)
    eng.handle_keys(["left_shift", "I", "a", " ", "Esc"])
    eng.handle_keys(["right_shift", "A", "!", "Esc"])
    eng.handle_keys(["caps_lock", "O", *list("top"), "Esc"])
    assert eng.get_text() == "top\n  a mid!"

    eng = VimEngine.from_text("abcdef", row=0, col=3)
    eng.handle_keys(["left_shift", "D"])
    assert eng.get_text() == "abc"
    eng.handle_keys(["0", "l", "right_shift", "C", *list("XYZ"), "Esc"])
    assert eng.get_text() == "aXYZ"

    eng.handle_keys(["left_shift", "Z", "left_shift", "Z"])
    assert eng.saved is True
    assert eng.quitted is True
