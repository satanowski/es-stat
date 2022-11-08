# pylint: disable=missing-module-docstring,missing-function-docstring

from rich.table import Table

from .common import empty_box

COLUMNS = (
    "index",
    "shard",
    "stage",
    "source_node",
    "target_node",
    "files_percent",
    "bytes_percent",
    "translog_ops_percent",
)


def render_data(data):
    if not data:
        return empty_box("No ongoing shards recovery")

    table = Table(expand=True)
    for col in COLUMNS:
        table.add_column(col.capitalize().replace("_", " ").replace("percent", "%"))

    for record in data:
        table.add_row(*(record[col] for col in COLUMNS))

    return table
