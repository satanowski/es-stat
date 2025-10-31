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
import time

import click
from rich.live import Live

from esstat.dashboard import Dashboard
from esstat.data_handler import DataHandler
from esstat.input_handler import create_key_listener, get_key_context

APP_NAME = "EsStat"


async def _handle_key_events(dashboard: Dashboard, key_listener, live: Live, shutdown_event: asyncio.Event):
    """Process keyboard events."""
    raw_chars = key_listener.drain()
    keys = key_listener.parse_keys(raw_chars)
    for key in keys:
        if key.lower() == "q":
            shutdown_event.set()
            break
        elif key.lower() == "h":
            dashboard.toggle_help()
            live.update(dashboard.get_renderable())
        elif key.lower() == "p":
            dashboard.toggle_pause()
            live.update(dashboard.get_renderable())
        elif key.lower() == "e":
            dashboard.toggle_edit_mode()
            live.update(dashboard.get_renderable())
        elif key == "UP" and dashboard.is_edit_mode():
            dashboard.move_selection_up()
            dashboard.update_ui()
            live.update(dashboard.get_renderable())
        elif key == "DOWN" and dashboard.is_edit_mode():
            dashboard.move_selection_down()
            dashboard.update_ui()
            live.update(dashboard.get_renderable())
        elif key == "\r" or key == "\n":
            # Enter key pressed
            if dashboard.is_edit_mode():
                selected = dashboard.get_selected_setting()
                if selected:
                    # TODO: Implement action on selected setting
                    # For now, just exit edit mode
                    dashboard.toggle_edit_mode()
                    live.update(dashboard.get_renderable())


async def _data_fetcher(dashboard: Dashboard, handler: DataHandler, shutdown_event: asyncio.Event):
    """Background task to fetch data every 5 seconds."""
    # Initial fetch before starting the loop
    try:
        await dashboard.refresh(handler)
        dashboard.clear_error()
    except Exception as e:
        error_msg = f"Error fetching initial data: {e}"
        dashboard.set_error(error_msg)

    while not shutdown_event.is_set():
        # Calculate next refresh time to maintain consistent intervals
        next_refresh = dashboard.get_next_refresh_time()
        sleep_time = max(0.1, next_refresh - time.time())

        try:
            await asyncio.sleep(sleep_time)
            # Only fetch data if not paused and not shutting down
            if not shutdown_event.is_set() and not dashboard.is_paused():
                await dashboard.refresh(handler)
                dashboard.clear_error()
        except Exception as e:
            error_msg = f"Error fetching data: {e}"
            dashboard.set_error(error_msg)


async def printscreen(host: str, port: int):
    """Render the screen and update it."""
    dashboard = Dashboard(APP_NAME, host)
    key_listener = None
    
    async with DataHandler(host, port) as dah:
        with get_key_context():
            key_listener = create_key_listener()

            # Flag to signal shutdown
            shutdown_event = asyncio.Event()

            try:
                # Start background data fetcher
                fetch_task = asyncio.create_task(_data_fetcher(dashboard, dah, shutdown_event))

                with Live(dashboard.layout, refresh_per_second=10, screen=True) as live:
                    while not shutdown_event.is_set():
                        # Update UI from cached data (non-blocking)
                        # Always update in edit mode, otherwise only when not paused
                        if dashboard.is_edit_mode() or not dashboard.is_paused():
                            dashboard.update_ui()
                        dashboard.update_countdown()
                        live.update(dashboard.get_renderable())

                        # Handle key presses
                        if key_listener:
                            await _handle_key_events(dashboard, key_listener, live, shutdown_event)

                        # Short sleep for UI responsiveness
                        await asyncio.sleep(0.1)

                # Wait for background task to finish
                await fetch_task

            finally:
                shutdown_event.set()
                if key_listener:
                    key_listener.stop()


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
