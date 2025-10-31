# pylint: disable=missing-module-docstring,missing-function-docstring

from rich.align import Align
from rich.text import Text


def render_countdown(seconds_remaining: int) -> Text:
    """Render countdown text with color based on time remaining.
    
    Args:
        seconds_remaining: Number of seconds until next refresh
        
    Returns:
        Formatted Text with dynamic color:
        - > 3 seconds: green
        - 2-3 seconds: yellow
        - < 2 seconds: orange
    """
    # Determine color based on time remaining
    if seconds_remaining > 3:
        color = "green"
    elif seconds_remaining >= 2:
        color = "yellow"
    else:
        color = "orange1"
    
    # Create the text with bold seconds
    text = Text("Next refresh in ")
    text.append(str(seconds_remaining), style=f"bold {color}")
    text.append(" seconds...")
    
    return Align.center(text, vertical="middle")


def render_loading() -> Text:
    """Render loading indicator when fetching data.
    
    Returns:
        Formatted Text showing loading state
    """
    text = Text("Refreshing data", style="bold cyan")
    text.append("...", style="bold cyan")
    
    return Align.center(text, vertical="middle")


def render_paused() -> Text:
    """Render paused indicator when app is in paused mode.
    
    Returns:
        Formatted Text showing paused state
    """
    text = Text("⏸ ", style="bold yellow")
    text.append("PAUSED", style="bold yellow")
    text.append(" ⏸", style="bold yellow")
    
    return Align.center(text, vertical="middle")
