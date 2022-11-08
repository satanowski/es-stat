# pylint: disable=missing-module-docstring,missing-function-docstring

from rich.table import Table

from .common import empty_box

COLUMNS = ("index", "shard", "prirep", "state", "store", "docs", "ip", "node")

FILTER_OUT = ("UNASSIGNED",)


def render_data(data):
    if not data:
        return empty_box("No active shards relocation")

    table = Table(expand=True)
    for col in COLUMNS:
        table.add_column(col.capitalize().replace("_", " "))

    for rec in filter(lambda r: r.get("state") not in FILTER_OUT, data):
        table.add_row(*(rec[col] for col in COLUMNS))

    return table
