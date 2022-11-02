# -*- coding: utf-8 -*-
"""
Simple ES cluster monitoring tool.

Todo:
    * handle nodes with auth.
    * handle exec arguments
    * use setup.py to install
"""


import sys
from argparse import ArgumentParser
from time import sleep

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

from data_handler import DataHandler
from renderables import recovery, relocation, settings, status
from renderables.header import Header

APP_NAME = "EsStat"
PROC_NUM = 4

console = Console()


def make_layout(cluster_name="") -> Layout:
    """Define the screen layout."""

    lay = Layout(name="root")
    lay.split(Layout(name="header", size=3), Layout(name="main", ratio=1))
    lay["main"].split_row(
        Layout(name="side", minimum_size=50), Layout(name="body", ratio=4, minimum_size=100)
    )
    lay["side"].split(Layout(name="status", size=29), Layout(name="settings"))
    lay["body"].split(Layout(name="reloc"), Layout(name="recov"))

    lay["header"].update(Header(APP_NAME, cluster_name))
    lay["recov"].update(Panel("", title="Shards recovery in progress..."))
    lay["settings"].update(Panel("", title="Settings"))
    lay["status"].update(Panel("", title="Status"))
    lay["reloc"].update(Panel("", title="Shards relocation in progress..."))

    return lay


def update_screen(lay, dah: DataHandler):
    """Update screen elements with new data."""
    lay["status"].update(Panel(status.render_data(dah.get_status()), title="Status"))
    lay["settings"].update(
        Panel(settings.render_data(dah.get_settings()), title="Settings")
    )
    lay["recov"].update(
        Panel(
            recovery.render_data(dah.get_recovery()),
            title="Shards recovery in progress...",
        )
    )
    lay["reloc"].update(
        Panel(
            relocation.render_data(dah.get_relocations()),
            title="Shards relocation in progress...",
        )
    )
    return lay


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("address")
    args = parser.parse_args()

    # to do --- handling port and logging
    if not args.address:
        sys.exit(1)

    try:
        layout = make_layout(args.address)
        dh = DataHandler(args.address)

        with Live(layout, refresh_per_second=4) as live:
            while True:
                live.update(update_screen(layout, dh))
                sleep(5)
    except KeyboardInterrupt:
        sys.exit(0)