"""Key normalization helpers for VIM and TMUX simulation engines."""

from __future__ import annotations

TEXTUAL_PUNCT_MAP: dict[str, str] = {
    "space": " ",
    "slash": "/",
    "question_mark": "?",
    "colon": ":",
    "semicolon": ";",
    "comma": ",",
    "full_stop": ".",
    "period": ".",
    "minus": "-",
    "hyphen_minus": "-",
    "underscore": "_",
    "plus": "+",
    "equals_sign": "=",
    "exclamation_mark": "!",
    "at": "@",
    "commercial_at": "@",
    "number_sign": "#",
    "hash": "#",
    "dollar_sign": "$",
    "percent_sign": "%",
    "circumflex_accent": "^",
    "caret": "^",
    "ampersand": "&",
    "asterisk": "*",
    "left_parenthesis": "(",
    "right_parenthesis": ")",
    "left_square_bracket": "[",
    "right_square_bracket": "]",
    "left_curly_bracket": "{",
    "right_curly_bracket": "}",
    "quotation_mark": '"',
    "double_quote": '"',
    "apostrophe": "'",
    "single_quote": "'",
    "tilde": "~",
    "grave_accent": "`",
    "less_than_sign": "<",
    "greater_than_sign": ">",
    "vertical_line": "|",
    "reverse_solidus": "\\",
    "backslash": "\\",
}

SPECIAL_KEY_MAP: dict[str, str] = {
    "escape": "Esc",
    "esc": "Esc",
    "backspace": "BS",
    "bs": "BS",
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "ctrl+up": "Ctrl-Up",
    "ctrl+down": "Ctrl-Down",
    "ctrl+left": "Ctrl-Left",
    "ctrl+right": "Ctrl-Right",
    "alt+up": "Alt-Up",
    "alt+down": "Alt-Down",
    "alt+left": "Alt-Left",
    "alt+right": "Alt-Right",
}


def normalize_key(key: str, character: str | None = None) -> str:
    """Normalize a Textual or test key string into a canonical token."""
    if character and len(character) == 1 and character.isprintable() and not key.startswith(("ctrl+", "alt+")):
        return character

    lower = key.lower()
    if lower in SPECIAL_KEY_MAP:
        return SPECIAL_KEY_MAP[lower]
    if lower in TEXTUAL_PUNCT_MAP:
        return TEXTUAL_PUNCT_MAP[lower]

    if lower.startswith("ctrl+") and len(lower) == 6:
        return f"Ctrl-{lower[-1]}"
    if lower.startswith("ctrl-") and len(lower) == 6:
        return f"Ctrl-{lower[-1]}"

    if len(key) == 1:
        return key
    return key


def format_key_for_display(key: str) -> str:
    """Format a canonical key token nicely for keystroke tapes."""
    if key == " ":
        return "Space"
    return key
