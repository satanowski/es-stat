# -*- coding: utf-8 -*-
"""
Dashboard UI management for EsStat.

Handles layout construction, panel updates, and UI state management.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable, Optional

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel

from esstat.data_handler import DataHandler
from esstat.renderables import countdown, recovery, relocation, settings, status
from esstat.renderables.header import Header

Renderable = Any


@dataclass(frozen=True)
class PanelSpec:
    """Specification for a dashboard panel."""
    key: str
    title: str
    fetch: Callable[[DataHandler], Awaitable[Any]]
    render: Callable[[Any], Renderable]
    wrap: bool = True
    border_style: str | None = None
    box_style: box.Box | None = None
    auto_height: bool = False
    min_height: int = 3


class Dashboard:
    """
    Main dashboard UI manager.
    
    Manages layout, panel updates, state (help/pause/edit modes),
    and cached data from Elasticsearch.
    """

    def __init__(self, app_name: str, cluster_name: str, refresh_interval: int = 5):
        self.app_name = app_name
        self.cluster_name = cluster_name
        self.refresh_interval = refresh_interval
        self.layout = Layout(name="root")
        self._console = Console()
        self._show_help = False
        self._paused = False  # Track if app is in paused mode
        self._edit_mode = False  # Track if app is in edit mode
        self._selected_row = 0  # Currently selected row in edit mode
        self._cached_data: dict[str, Any] = {}
        self._data_lock = asyncio.Lock()
        self._error_message: Optional[str] = None
        self._data_ready = False  # Track if we have initial data
        self._last_refresh_time: float = 0.0
        self._is_refreshing = False  # Track if we're currently fetching data
        self._panels: tuple[PanelSpec, ...] = (
            PanelSpec(
                "status",
                "Status",
                DataHandler.get_status,
                status.render_data,
                wrap=False,
                auto_height=True,
                min_height=12,
            ),
            PanelSpec(
                "settings",
                "Cluster settings",
                DataHandler.get_settings,
                settings.render_data,
                border_style="cyan",
                box_style=box.SQUARE,
                auto_height=False,
                min_height=5,
            ),
            PanelSpec(
                "recov",
                "Shards recovery in progress...",
                DataHandler.get_recovery,
                recovery.render_data,
                border_style="yellow",
                box_style=box.SQUARE,
            ),
            PanelSpec(
                "reloc",
                "Shards relocation in progress...",
                DataHandler.get_relocations,
                relocation.render_data,
                border_style="magenta",
                box_style=box.SQUARE,
            ),
        )
        self._build_layout()

    def _build_layout(self) -> None:
        """Build the initial layout structure."""
        lay = self.layout
        lay.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
        )
        lay["main"].split_row(
            Layout(name="side", minimum_size=44, ratio=1),
            Layout(name="body", ratio=3, minimum_size=96),
        )
        lay["side"].split(
            Layout(name="status", ratio=1, minimum_size=12),
            Layout(name="settings", ratio=1, minimum_size=5),
            Layout(name="countdown", size=3),
        )
        lay["body"].split(
            Layout(name="reloc", ratio=1, minimum_size=14),
            Layout(name="recov", ratio=1, minimum_size=14),
        )
        self._prime_layout()

    def _prime_layout(self) -> None:
        """Initialize panels with empty content."""
        self.layout["header"].update(Header(self.app_name, self.cluster_name))
        for spec in self._panels:
            panel_kwargs: dict[str, Any] = {}
            if spec.border_style:
                panel_kwargs["border_style"] = spec.border_style
            if spec.box_style:
                panel_kwargs["box"] = spec.box_style
            self.layout[spec.key].update(
                Panel(
                    "",
                    title=spec.title,
                    **panel_kwargs,
                )
            )
        # Initialize countdown panel
        self.layout["countdown"].update(
            Panel(countdown.render_countdown(self.refresh_interval), box=box.SQUARE, border_style="dim")
        )

    def _iter_panel_specs(self) -> Iterable[PanelSpec]:
        """Iterate over panel specifications."""
        return self._panels

    def toggle_help(self) -> None:
        """Toggle the help shortcuts visibility."""
        self._show_help = not self._show_help
        # Immediately update the status panel
        self._update_status_panel()

    def toggle_pause(self) -> None:
        """Toggle the paused state."""
        self._paused = not self._paused

    def is_paused(self) -> bool:
        """Check if the app is in paused mode."""
        return self._paused

    def toggle_edit_mode(self) -> None:
        """Toggle edit mode for cluster settings."""
        self._edit_mode = not self._edit_mode
        if self._edit_mode:
            # Reset selection to first row when entering edit mode
            self._selected_row = 0

    def is_edit_mode(self) -> bool:
        """Check if the app is in edit mode."""
        return self._edit_mode

    def move_selection_up(self) -> None:
        """Move selection up in edit mode (wrap around)."""
        if not self._edit_mode:
            return
        settings_data = self._cached_data.get("settings", {})
        if not settings_data:
            return
        num_rows = len(settings_data)
        if num_rows > 0:
            self._selected_row = (self._selected_row - 1) % num_rows

    def move_selection_down(self) -> None:
        """Move selection down in edit mode (wrap around)."""
        if not self._edit_mode:
            return
        settings_data = self._cached_data.get("settings", {})
        if not settings_data:
            return
        num_rows = len(settings_data)
        if num_rows > 0:
            self._selected_row = (self._selected_row + 1) % num_rows

    def get_selected_setting(self) -> tuple[str, str] | None:
        """Get the currently selected setting key and value."""
        if not self._edit_mode:
            return None
        settings_data = self._cached_data.get("settings", {})
        if not settings_data:
            return None
        items = list(settings_data.items())
        if 0 <= self._selected_row < len(items):
            return items[self._selected_row]
        return None

    def get_selected_row_index(self) -> int:
        """Get the currently selected row index."""
        return self._selected_row

    def _update_status_panel(self) -> None:
        """Update the status panel to show either help or cluster status."""
        if self._show_help:
            # Show shortcuts in the status panel
            help_panel = settings.render_help_panel()
            self.layout["status"].update(help_panel)
            # Measure and set height for help panel
            est_width = self._estimate_width("status")
            dyn_height = self._measure_height(help_panel, est_width)
            self.layout["status"].ratio = None
            self.layout["status"].size = max(12, dyn_height)
        else:
            # Reset to auto-height for status panel
            self.layout["status"].ratio = 1
            self.layout["status"].size = None

    def get_renderable(self) -> Any:
        """Get the current renderable."""
        if not self._data_ready:
            # Show loading state
            from rich.align import Align
            from rich.text import Text
            loading_text = Text("Waiting for data from Elasticsearch...", style="bold yellow")
            return Align.center(loading_text, vertical="middle")
        return self.layout

    def set_error(self, message: str) -> None:
        """Show error message in the footer."""
        self._error_message = message
        self._update_footer()

    def clear_error(self) -> None:
        """Clear error message and hide footer."""
        self._error_message = None
        self._update_footer()

    def _update_footer(self) -> None:
        """Update the footer to show/hide error message."""
        if self._error_message:
            from rich.text import Text
            error_text = Text(f" ⚠ {self._error_message}", style="bold white on red")
            error_panel = Panel(error_text, box=box.SQUARE, border_style="red", expand=True)

            # Rebuild layout with footer
            self.layout.split(
                Layout(name="header", size=3),
                Layout(name="main", ratio=1),
                Layout(name="footer", size=3),
            )
            # Restore main layout structure
            self._rebuild_main_layout()
            self.layout["footer"].update(error_panel)
        else:
            # Rebuild layout without footer
            self.layout.split(
                Layout(name="header", size=3),
                Layout(name="main", ratio=1),
            )
            # Restore main layout structure
            self._rebuild_main_layout()

    def _rebuild_main_layout(self) -> None:
        """Rebuild the main layout structure (side and body panels)."""
        self.layout["main"].split_row(
            Layout(name="side", minimum_size=44, ratio=1),
            Layout(name="body", ratio=3, minimum_size=96),
        )
        self.layout["side"].split(
            Layout(name="status", ratio=1, minimum_size=12),
            Layout(name="settings", ratio=1, minimum_size=5),
            Layout(name="countdown", size=3),
        )
        self.layout["body"].split(
            Layout(name="reloc", ratio=1, minimum_size=14),
            Layout(name="recov", ratio=1, minimum_size=14),
        )
        # Re-prime panels with empty content
        self._prime_layout()

    def _estimate_width(self, key: str) -> int:
        """Estimate width for a panel based on layout ratios."""
        total_width = self._console.size.width
        # For side panels (status, settings), calculate the actual allocated width
        # side has ratio=1, body has ratio=3, so side gets 1/4 of total width
        if key in {"status", "settings"}:
            side_width = total_width // 4  # side ratio / (side ratio + body ratio)
            # Subtract borders and padding: 2 for panel borders, 2 for layout margins
            return max(side_width - 4, 24)
        # For body panels
        body_width = (total_width * 3) // 4
        return max(body_width - 4, 40)

    def _measure_height(self, renderable: Renderable, width: int) -> int:
        """Measure the height of a renderable at given width."""
        width = max(width, 10)
        options = self._console.options.update(width=width)
        lines = self._console.render_lines(renderable, options, pad=False)
        return max(len(lines), 1)

    async def refresh(self, handler: DataHandler) -> None:
        """Fetch data in background and update cache."""
        self._is_refreshing = True
        try:
            async with self._data_lock:
                async with asyncio.TaskGroup() as tg:
                    tasks = {
                        spec.key: tg.create_task(spec.fetch(handler)) for spec in self._iter_panel_specs()
                    }
                for spec in self._iter_panel_specs():
                    self._cached_data[spec.key] = tasks[spec.key].result()

                # Check if we got valid data (at least status should have cluster_name)
                status_data = self._cached_data.get("status", {})
                if not status_data or not status_data.get("cluster_name"):
                    raise RuntimeError("No valid data received from Elasticsearch")

                # Mark data as ready after first successful fetch
                if not self._data_ready:
                    self._data_ready = True

                # Update last refresh time
                self._last_refresh_time = time.time()
        finally:
            self._is_refreshing = False

    def get_seconds_until_refresh(self) -> int:
        """Calculate seconds remaining until next refresh."""
        if self._last_refresh_time == 0.0:
            return self.refresh_interval
        elapsed = time.time() - self._last_refresh_time
        remaining = self.refresh_interval - int(elapsed)
        return max(0, remaining)

    def get_next_refresh_time(self) -> float:
        """Get the timestamp of the next scheduled refresh."""
        return self._last_refresh_time + self.refresh_interval

    def update_countdown(self) -> None:
        """Update the countdown panel."""
        if self._paused:
            # Show paused indicator when in paused mode
            renderable = countdown.render_paused()
        elif self._is_refreshing:
            # Show loading indicator when fetching data
            renderable = countdown.render_loading()
        else:
            seconds_remaining = self.get_seconds_until_refresh()
            renderable = countdown.render_countdown(seconds_remaining)

        self.layout["countdown"].update(
            Panel(renderable, box=box.SQUARE, border_style="dim")
        )

    def update_ui(self) -> None:
        """Update UI from cached data (non-blocking)."""
        # Don't update UI if data is not ready yet
        if not self._data_ready:
            return

        self.layout["header"].update(Header(self.app_name, self.cluster_name))

        for spec in self._iter_panel_specs():
            # Skip status panel if help is shown
            if spec.key == "status" and self._show_help:
                continue

            payload = self._cached_data.get(spec.key, {} if spec.key != "recov" and spec.key != "reloc" else [])

            # Special handling for settings panel in edit mode
            if spec.key == "settings" and self._edit_mode:
                rendered = settings.render_data(payload, self._selected_row)
            else:
                rendered = spec.render(payload)

            if spec.wrap:
                panel_kwargs: dict[str, Any] = {}
                if spec.border_style:
                    panel_kwargs["border_style"] = spec.border_style
                if spec.box_style:
                    panel_kwargs["box"] = spec.box_style
                # Change border style for settings panel in edit mode
                if spec.key == "settings" and self._edit_mode:
                    panel_kwargs["border_style"] = "bold yellow"
                    title = f"{spec.title} [EDIT MODE]"
                else:
                    title = spec.title
                final_renderable = Panel(rendered, title=title, **panel_kwargs)
            else:
                final_renderable = rendered
            self.layout[spec.key].update(final_renderable)
            if spec.auto_height:
                est_width = self._estimate_width(spec.key)
                dyn_height = self._measure_height(final_renderable, est_width)
                self.layout[spec.key].ratio = None
                self.layout[spec.key].size = max(spec.min_height, dyn_height)
            else:
                # Ensure non-auto-height panels use ratio, never size
                if self.layout[spec.key].ratio is None:
                    self.layout[spec.key].ratio = 1
                self.layout[spec.key].size = None
