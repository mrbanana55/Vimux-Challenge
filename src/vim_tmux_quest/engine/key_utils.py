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

MODIFIER_ONLY_KEYS: frozenset[str] = frozenset(
    {
        "shift",
        "left_shift",
        "right_shift",
        "ctrl",
        "control",
        "left_control",
        "right_control",
        "alt",
        "option",
        "left_alt",
        "right_alt",
        "super",
        "cmd",
        "command",
        "left_super",
        "right_super",
        "hyper",
        "left_hyper",
        "right_hyper",
        "meta",
        "left_meta",
        "right_meta",
        "iso_level3_shift",
        "iso_level5_shift",
        "caps_lock",
        "scroll_lock",
        "num_lock",
        "ignore",
        "<ignore>",
    }
)


def is_modifier_key(key: str) -> bool:
    """Return True if key represents a standalone modifier, lock, or ignored key."""
    if not key:
        return True
    lower = key.lower()
    if lower in MODIFIER_ONLY_KEYS:
        return True
    if key != "+" and "+" in lower:
        tail = lower.rsplit("+", 1)[-1]
        if tail in MODIFIER_ONLY_KEYS:
            return True
    return False


def normalize_key(key: str, character: str | None = None) -> str:
    """Normalize a Textual or test key string into a canonical token."""
    if is_modifier_key(key):
        return ""

    lower = key.lower()
    if (
        character
        and len(character) == 1
        and character.isprintable()
        and not lower.startswith(("ctrl+", "ctrl-", "alt+", "alt-"))
    ):
        if lower.startswith(("shift+", "shift-")) and character.isalpha():
            return character.upper()
        return character

    if lower.startswith(("shift+", "shift-")):
        base = key[6:]
        base_lower = base.lower()
        if len(base) == 1 and base.isalpha():
            return base.upper()
        if base_lower.startswith("upper_") and len(base_lower) == 7 and base_lower[-1].isalpha():
            return base_lower[-1].upper()
        if base_lower in TEXTUAL_PUNCT_MAP:
            return TEXTUAL_PUNCT_MAP[base_lower]
        if base_lower in SPECIAL_KEY_MAP:
            return SPECIAL_KEY_MAP[base_lower]
        if len(base) == 1:
            return base

    if lower.startswith("upper_") and len(lower) == 7 and lower[-1].isalpha():
        return lower[-1].upper()

    if lower in SPECIAL_KEY_MAP:
        return SPECIAL_KEY_MAP[lower]
    if lower in TEXTUAL_PUNCT_MAP:
        return TEXTUAL_PUNCT_MAP[lower]

    if lower.startswith(("ctrl+shift+", "ctrl-shift-")) and len(lower) == 12 and lower[-1].isalpha():
        return f"Ctrl-{lower[-1]}"
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
