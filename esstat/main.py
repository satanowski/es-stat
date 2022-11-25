# -*- coding: utf-8 -*-
# pylint: disable=
"""
Simple ES cluster monitoring tool.

Todo:
    * handle nodes with auth.
    * handle exec arguments
    * use setup.py to install
"""


import asyncio
import sys
from time import sleep

import click
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

from esstat.data_handler import DataHandler
from esstat.renderables import recovery, relocation, settings, status
from esstat.renderables.header import Header

APP_NAME = "EsStat"
PROC_NUM = 4

console = Console()


def make_layout(cluster_name="") -> Layout:
    """Define the screen layout."""

    lay = Layout(name="root")
    lay.split(Layout(name="header", size=3), Layout(name="main", ratio=1))
    lay["main"].split_row(
        Layout(name="side", minimum_size=50),
        Layout(name="body", ratio=4, minimum_size=100),
    )
    lay["side"].split(Layout(name="status", size=29), Layout(name="settings"))
    lay["body"].split(Layout(name="reloc"), Layout(name="recov"))

    lay["header"].update(Header(APP_NAME, cluster_name))
    lay["recov"].update(Panel("", title="Shards recovery in progress..."))
    lay["settings"].update(Panel("", title="Settings"))
    lay["status"].update(Panel("", title="Status"))
    lay["reloc"].update(Panel("", title="Shards relocation in progress..."))

    return lay


async def update_screen(lay, dah: DataHandler):
    """Update screen elements with new data."""
    lay["status"].update(Panel(status.render_data(await dah.get_status()), title="Status"))
    lay["settings"].update(
        Panel(settings.render_data(await dah.get_settings()), title="Settings")
    )
    lay["recov"].update(
        Panel(
            recovery.render_data(await dah.get_recovery()),
            title="Shards recovery in progress...",
        )
    )
    lay["reloc"].update(
        Panel(
            relocation.render_data(await dah.get_relocations()),
            title="Shards relocation in progress...",
        )
    )
    return lay


async def printscreen(host: str, port: int):
    """Render the screen and update it."""
    layout = make_layout(host)
    dah = DataHandler(host, port)

    with Live(layout, refresh_per_second=4) as live:
        while True:
            live.update(await update_screen(layout, dah))
            sleep(5)


@click.command(name=APP_NAME.lower(), help="Monitor ElasticSearch cluster state")
@click.option("--port", default=9200, help="Elasticsearch node port")
@click.argument("host")
def main(host, port):
    """The main app entrypoint."""
    try:
        asyncio.run(printscreen(host, port))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
