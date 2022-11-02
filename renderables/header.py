# pylint: disable=missing-module-docstring,missing-function-docstring

from datetime import datetime

from rich.panel import Panel
from rich.table import Table


class Header:  # pylint: disable=too-few-public-methods
    
    """Display app header with clock."""

    def __init__(self, app_name: str, cluster_name: str):
        self.app_name = app_name
        self.cluster_name = cluster_name

    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True)
        for just in ("left", "center", "right"):
            grid.add_column(justify=just, ratio=1)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        grid.add_row(f"[b]{self.app_name}[/b]", f"[b]{self.cluster_name}[/]", now)
        return Panel(grid)
