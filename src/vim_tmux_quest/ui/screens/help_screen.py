"""Help, controls, Fn-key guide, and about screen."""

from __future__ import annotations

from textual import events
from textual.containers import Center, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

HELP_TEXT = """[bold #39d353]ABOUT VIMUX CHALLENGE[/bold #39d353]
Vimux Challenge is a self-contained terminal simulator and interactive tutorial
for mastering VIM motions/editing and TMUX pane/window/session workflows.

  • Campaign Mode: 4 progressive tracks (28 levels total), from basic hjkl and
    splits up to text objects, macros, copy-mode, and combined VIM+TMUX tasks.
  • Star Ratings (1–3★): Earn 3 stars by finishing at or under Par keystrokes
    without opening the Hint box.
  • Practice & Speed Drills: 51 command flashcards with adaptive weighting toward
    your weakest or least-practiced commands.
  • Persistent Progress: Your completed levels, stars, XP, streaks, and settings
    are automatically saved in SQLite.

[bold #58a6ff]USING FUNCTION KEYS (F1, F2, F3)[/bold #58a6ff]
During levels and drills, keys like Esc, q, :q, Tab, Ctrl-b, Ctrl-a, Ctrl-r,
and arrow keys go directly to the VIM / TMUX simulator so nothing clashes with
real commands. Because of that, meta-actions use Function keys:

  • On macOS or compact laptop keyboards where the top row adjusts brightness
    or volume by default, hold the [bold #f0c674]fn[/bold #f0c674] key while pressing F1, F2, or F3
    (i.e. [bold #f0c674]fn + F1[/bold #f0c674], [bold #f0c674]fn + F2[/bold #f0c674], [bold #f0c674]fn + F3[/bold #f0c674]).

[bold #58a6ff]GAMEPLAY CONTROLS[/bold #58a6ff]
  Toggle Hint (caps max stars at 2★)   ->   F1  (fn + F1)
  Reset / Retry Current Level          ->   F2  (fn + F2)
  Exit Level Back to Menu              ->   F3  (fn + F3)

[bold #58a6ff]PRACTICE & SPEED DRILL CONTROLS[/bold #58a6ff]
  Switch Filter (All / VIM / TMUX / Weak) -> F1  (fn + F1)
  Reveal Command Answer                   -> F2  (fn + F2)
  Exit Drills Back to Main Menu           -> F3  (fn + F3)

[bold #58a6ff]MENU NAVIGATION[/bold #58a6ff]
  1–6            Quick-launch menu option from Main Menu
  j / k / Arrows Move highlight up or down
  Enter          Open selected option or level
  Esc / q        Go back to the previous screen
"""


class HelpScreen(Screen):
    """Displays controls, Fn-key instructions, and information about the game."""

    def compose(self):
        yield Static("HELP, CONTROLS & ABOUT — Vimux Challenge", classes="screen-header")
        with Center():
            with VerticalScroll(classes="help-card", id="help-scroll"):
                yield Static(HELP_TEXT, id="help-body")
        yield Static("j/k or Arrows: Scroll | Esc/q: Back to Main Menu", classes="footer-bar")

    def on_mount(self) -> None:
        self.query_one("#help-scroll", VerticalScroll).focus()

    def on_key(self, event: events.Key) -> None:
        scroll = self.query_one("#help-scroll", VerticalScroll)
        if event.key in ("escape", "q"):
            event.stop()
            self.app.pop_screen()
        elif event.key in ("j", "down"):
            scroll.scroll_down()
        elif event.key in ("k", "up"):
            scroll.scroll_up()
