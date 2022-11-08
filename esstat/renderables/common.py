# pylint: disable=missing-module-docstring,missing-function-docstring

from rich.padding import Padding
from rich.text import Text


def empty_box(content: str):
    return Padding(Text(content, justify="center"), pad=(3, 0, 0, 0))
