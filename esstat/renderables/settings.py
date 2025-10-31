# pylint: disable=missing-module-docstring,missing-function-docstring

from typing import Union

from rich import box
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .common import empty_box

# Elasticsearch setting shortcuts (for highlighting in settings table)
SHORTCUTS = (
    "allocation",
    "balance",
    "cluster",
    "disk",
    "indices",
    ("incoming", "in"),
    "node",
    "outgoing",
    "routing",
    "watermark",
    ("recoveries", "rec"),
    ("relocations", "rel"),
    ("concurrent", "cc"),
    ("connections", "con"),
)

# Keyboard shortcuts
KEYBOARD_SHORTCUTS = (
    ("h", "Toggle this help"),
    ("p", "Pause / Resume updates"),
    ("e", "Toggle edit mode"),
    ("q", "Quit application"),
)


def _short(rep: str) -> str:
    for short in SHORTCUTS:
        if isinstance(short, str):
            rep = rep.replace(short, f"[white][b]{short[0]}[/][/]")
        if isinstance(short, tuple):
            rep = rep.replace(short[0], f"[white][b]{short[1]}[/][/]")
    return rep


def render_table(data: dict = {}, selected_row: int | None = None):  # pylint: disable=dangerous-default-value
    if not data:
        return empty_box("No settings retrieved")

    table = Table(expand=True)
    table.add_column("Setting", justify="left", no_wrap=True)
    table.add_column("Value")

    for idx, (key, val) in enumerate(data.items()):
        # Highlight the selected row in edit mode
        if selected_row is not None and idx == selected_row:
            key_text = Text.from_markup(_short(key))
            key_text.stylize("reverse bold yellow")
            val_text = Text(str(val))
            val_text.stylize("reverse bold yellow")
            table.add_row(key_text, val_text)
        else:
            table.add_row(Text.from_markup(_short(key)), str(val))
    return table


def _short_split(short: Union[str, tuple]) -> tuple:
    return (short[1], short[0]) if isinstance(short, tuple) else (short[0], short)


def _bold(txt: str) -> Text:
    return Text.from_markup(f"[white][b]{txt}[/][/]")


def render_shortcuts_legend():
    """Render the Elasticsearch settings shortcuts legend."""
    table = Table(expand=True, box=None)
    for _ in range(4):
        table.add_column("")
    # divide in chunks of 2 elements
    for shorts in [SHORTCUTS[i : i + 2] for i in range(0, len(SHORTCUTS), 2)]:
        short_left, short_right = shorts if len(shorts) == 2 else (shorts[0], " ")
        left, right = _short_split(short_left), _short_split(short_right)
        table.add_row(_bold(left[0]), left[1], _bold(right[0]), right[1])
    return table


def render_keyboard_shortcuts():
    """Render keyboard shortcuts for the help panel."""
    from rich.console import Group
    
    shortcuts_text = []
    shortcuts_text.append(Text("Keyboard Shortcuts", style="bold yellow", justify="center"))
    shortcuts_text.append(Text(""))
    
    for key, description in KEYBOARD_SHORTCUTS:
        line = Text()
        line.append(f"  {key}  ", style="bold white on blue")
        line.append(f"  {description}")
        shortcuts_text.append(line)
    
    shortcuts_text.append(Text(""))
    shortcuts_text.append(Text("Settings Filter Shortcuts", style="bold cyan", justify="center"))
    shortcuts_text.append(Text("(highlighted in settings table)", style="dim italic", justify="center"))
    shortcuts_text.append(Text(""))
    
    # Add ES shortcuts in a more compact format
    for short in SHORTCUTS:
        if isinstance(short, tuple):
            line = Text(f"  {short[1]}  ", style="bold white on green")
            line.append(f"  {short[0]}")
        else:
            line = Text(f"  {short[0]}  ", style="bold white on green")
            line.append(f"  {short}")
        shortcuts_text.append(line)
    
    return Group(*shortcuts_text)


def render_data(data, selected_row: int | None = None):
    return Padding(render_table(data, selected_row), pad=(1, 0, 1, 0))


def render_help_panel():
    """Render the help panel to replace cluster status panel."""
    return Panel(
        Padding(render_keyboard_shortcuts(), pad=(1, 2, 1, 2)),
        title="Help (press 'h' to close)",
        box=box.SQUARE,
        expand=True,
        border_style="yellow",
    )


def render_help_modal():
    """Render the help modal with shortcuts legend."""
    return Panel(
        Padding(render_shortcuts_legend(), pad=(1, 0, 1, 0)),
        title="Shortcuts (press 'h' to close)",
        box=box.HEAVY,
        expand=True,
        border_style="yellow",
    )
