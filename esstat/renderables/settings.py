# pylint: disable=missing-module-docstring,missing-function-docstring

from typing import Union

from rich import box
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .common import empty_box

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


def _short(rep: str) -> str:
    for short in SHORTCUTS:
        if isinstance(short, str):
            rep = rep.replace(short, f"[white][b]{short[0]}[/][/]")
        if isinstance(short, tuple):
            rep = rep.replace(short[0], f"[white][b]{short[1]}[/][/]")
    return rep


def render_table(data: dict = {}):  # pylint: disable=dangerous-default-value
    if not data:
        return empty_box("No settings retrieved")

    table = Table(expand=True)
    table.add_column("Setting", justify="left", no_wrap=True)
    table.add_column("Value")

    for key, val in data.items():
        table.add_row(Text.from_markup(_short(key)), str(val))
    return table


def _short_split(short: Union[str, tuple]) -> tuple:
    return (short[1], short[0]) if isinstance(short, tuple) else (short[0], short)


def _bold(txt: str) -> Text:
    return Text.from_markup(f"[white][b]{txt}[/][/]")


def render_shortcuts_legend():
    table = Table(expand=True, box=None)
    for _ in range(4):
        table.add_column("")
    # divide in chunks of 2 elements
    for shorts in [SHORTCUTS[i : i + 2] for i in range(0, len(SHORTCUTS), 2)]:
        short_left, short_right = shorts if len(shorts) == 2 else (shorts[0], " ")
        left, right = _short_split(short_left), _short_split(short_right)
        table.add_row(_bold(left[0]), left[1], _bold(right[0]), right[1])
    return table


def render_data(data):
    return Group(
        Padding(render_table(data), pad=(1, 0, 1, 0)),
        Panel(
            Padding(render_shortcuts_legend(), pad=(1, 0, 1, 0)),
            title="Shortcuts",
            box=box.SQUARE,
            expand=True,
        ),
    )
