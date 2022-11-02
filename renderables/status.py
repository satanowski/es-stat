# pylint: disable=missing-module-docstring,missing-function-docstring

from typing import Union

from rich import box
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from .common import empty_box


def status_row(key: str, val: Union[str, int], state: Union[bool, None] = None):
    if isinstance(state, bool):
        color = "green" if state else "red"
    else:
        color = "yellow"
    if isinstance(val, bool):
        val = "✖" if val else "✓"
    if isinstance(val, float):
        val = round(val,2)
    return Text.from_markup(f"[bold]{str(val).ljust(6)}[/bold][{color}]{key}[/]")


def render_data(c_state: dict):
    if not c_state:
        return empty_box("No status retrieved")

    tree = Tree(Text.from_markup(f"[bold]{c_state['cluster_name']}[/]"))
    shards = tree.add("Shards")
    shards.add(
        status_row(
            "Active primary",
            c_state["active_primary_shards"],
            c_state["active_primary_shards"] > 0,
        )
    )
    shards.add(
        status_row("Active", c_state["active_shards"], c_state["active_shards"] > 0)
    )

    shards.add(
        status_row(
            "Active as percent",
            c_state["active_shards_percent_as_number"],
            c_state["active_shards_percent_as_number"] == 100,
        )
    )
    shards.add(
        status_row(
            "Initializing",
            c_state["initializing_shards"],
            c_state["initializing_shards"] == 0 or None,
        )
    )
    shards.add(
        status_row(
            "Delayed unassigned",
            c_state["delayed_unassigned_shards"],
            c_state["delayed_unassigned_shards"] == 0 or None,
        )
    )
    shards.add(
        status_row(
            "Unassigned",
            c_state["unassigned_shards"],
            c_state["unassigned_shards"] == 0,
        )
    )
    shards.add(
        status_row(
            "Relocating",
            c_state["relocating_shards"],
            c_state["relocating_shards"] == 0,
        )
    )

    datanodes = tree.add("Datanodes")
    datanodes.add(
        status_row("Nodes", c_state["number_of_nodes"], c_state["number_of_nodes"] > 0)
    )
    datanodes.add(
        status_row(
            "Data nodes",
            c_state["number_of_data_nodes"],
            c_state["number_of_data_nodes"] > 0,
        )
    )

    tasks = tree.add("Tasks")
    tasks.add(
        status_row(
            "Pending tasks",
            c_state["number_of_pending_tasks"],
            c_state["number_of_pending_tasks"] == 0 or None,
        )
    )
    tasks.add(
        status_row(
            "Task max waiting in queue",
            c_state["task_max_waiting_in_queue_millis"],
            c_state["task_max_waiting_in_queue_millis"] == 0 or None,
        )
    )

    general = tree.add("General")
    general.add(
        status_row(
            "In flight fetch",
            c_state["number_of_in_flight_fetch"],
            c_state["number_of_in_flight_fetch"] == 0 or None,
        )
    )
    general.add(status_row("Timed out", c_state["timed_out"], not c_state["timed_out"]))

    cluster_status = Padding(
        Text.from_markup(
            f"\n[bold]{c_state['status'].upper()}[/bold]\n",
            justify="center",
            style=f"white on {c_state['status']}",
        ),
        pad=(0, 0, 1, 0),
    )

    return Panel(
        Padding(Group(cluster_status, tree), 1),
        title="Cluster state",
        box=box.SQUARE,
        expand=True,
    )
