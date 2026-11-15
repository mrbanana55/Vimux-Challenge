# Vimux Challenge

An interactive, self-contained terminal game and tutorial designed to help you build real muscle memory for **VIM motions/editing** and **TMUX commands**.

---

## About This Project

Learning VIM and TMUX at the same time usually means juggling cheat sheets while worrying about breaking your real `.vimrc`, `.tmux.conf`, or active terminal sessions. **Vimux Challenge** solves that by providing a **safe, deterministic simulator** directly inside your terminal built with Python and [Textual](https://textual.textualize.io/).

Every keystroke—including `Esc`, `q`, `:q`, `Tab`, `Ctrl-b`, `Ctrl-a`, and `Ctrl-r`—is captured cleanly by the in-game VIM and TMUX engines, giving you:
- **Immediate visual feedback** with live objective checklists and a keystroke tape.
- **Zero configuration conflicts** with your real system `vim`/`nvim` or `tmux`.
- **Persistent progress** saved automatically in a local SQLite database so you can track completed levels, star ratings, XP, drill streaks, and weak commands over time.

---

## Quick Start (Clone & Play in One Command)

**Prerequisites:** Python **3.11+** and `git`.

1. **Clone the repository and enter the folder:**
   ```bash
   git clone <repo-url>
   cd VimGame
   ```

2. **Launch the game** (the first run automatically creates `.venv` and installs dependencies):

   - **macOS / Linux (Bash / Zsh):**
     ```bash
     ./play.sh
     ```
     *(or run `make`)*

   - **Windows (PowerShell):**
     ```powershell
     .\play.ps1
     ```

   - **Windows (CMD / Double-click):**
     ```bat
     play.bat
     ```

   - **Universal Python Launcher (macOS / Linux / Windows):**
     ```bash
     python3 play.py
     ```

That's it! No manual `venv` creation or `pip install` commands needed.

---

## Game Modes & Curriculum

### 1. Campaign Mode (4 Tracks, 28 Levels)
Progress step by step through 28 hands-on coding & terminal challenges, scored against a **Par keystroke count** (`1–3★`):
- **Track 1 — VIM Foundations (7 levels):** `h/j/k/l`, word jumps (`w/b/e`), line edges (`0/^/$`), file teleports (`gg/G/<n>G`), Insert modes (`i/a/I/A/o/O`), and quick edits (`x/dd/u`).
- **Track 2 — VIM Precision & Power (7 levels):** Counts (`2dd`, `4w`), character find (`f/t/;/,`), operators + motions (`dw/d$/cw`), text objects (`ci"`, `di(`), visual/yank/put (`V/y/p`), dot repeat (`.`), and macros (`qa...q`, `@a`).
- **Track 3 — TMUX Foundations (7 levels):** Prefix mastery (`Ctrl-b` or configurable `Ctrl-a`), vertical & horizontal splits (`%`, `"`), pane focus (`o`, arrows, `h/j/k/l`), zoom (`z`), closing panes (`x`), and window management (`c`, `n`, `p`, `0-9`, `,`).
- **Track 4 — TMUX Mastery & Combo Workflows (7 levels):** Pane swapping (`{`, `}`), resizing (`H/J/K/L`, `Ctrl-Arrow`, `:resize-pane`), sessions (`$`, `s`, `d`), copy-mode (`[`, `Space`, `Enter`, `]`), and **combined TMUX + VIM workflows** where you split panes and patch code across files.

### 2. Practice & Speed Drills
- **51 command flashcards** covering VIM motions, operators, text objects, and TMUX panes, windows, sessions, and copy-mode.
- **Adaptive selection:** Commands you miss or haven't practiced yet appear more often so your drills target weak spots.

### 3. Command Cheat Sheet & Settings
- **Searchable Cheat Sheet (`[4]`):** Filter VIM & TMUX commands in real time.
- **Settings (`[5]`):** Switch TMUX prefix between `Ctrl-b` and `Ctrl-a`, toggle default hints, inspect weakest commands, or reset progress.
- **Help & Controls (`[6]`):** Built-in guide explaining controls and Function keys.

---

## Controls & Function Keys (`F1`, `F2`, `F3`)

Because `Esc`, `q`, `:q`, `Ctrl-b`, and `Ctrl-r` are used directly inside the VIM and TMUX simulations, meta-actions use **Function keys**:

| Screen | Action | Key |
| :--- | :--- | :--- |
| **Main Menu** | Quick launch menu item | `1`–`6` (or `j`/`k` + `Enter`) |
| **Main Menu** | Quit | `q` |
| **Gameplay** | Toggle Hint *(caps max stars at 2★)* | `F1` (`fn + F1` on Mac) |
| **Gameplay** | Reset / Retry Level | `F2` (`fn + F2` on Mac) |
| **Gameplay** | Exit Level to Menu | `F3` (`fn + F3` on Mac) |
| **Drills** | Switch Filter (`All / VIM / TMUX / Weak`) | `F1` (`fn + F1` on Mac) |
| **Drills** | Reveal Answer | `F2` (`fn + F2` on Mac) |
| **Drills** | Exit Drills to Menu | `F3` (`fn + F3` on Mac) |

> **macOS / Laptop Tip:** If your keyboard's top row adjusts brightness/volume by default, hold the **`fn`** key while pressing `F1`, `F2`, or `F3`.

---

## CLI Options & Running Tests

Check your saved progress without opening the full TUI:

```bash
./play.sh --status
```

Check version:

```bash
./play.sh --version
```

Run the automated test suite (after `.venv` has `pytest` installed):

```bash
.venv/bin/pip install pytest
make test
```
