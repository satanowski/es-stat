# pylint: disable=missing-module-docstring,missing-function-docstring

import re

from rich.table import Table
from rich.text import Text

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


def _colorize_percentage(percent_str: str) -> Text:
    """Colorize percentage value based on completion.
    
    Args:
        percent_str: Percentage string (e.g., "100.0%", "75.5%")
        
    Returns:
        Colorized Text object:
        - 100%: green
        - 75-99%: yellow
        - Below 75%: orange
    """
    text = Text()
    
    # Extract numeric value from percentage string
    try:
        # Remove '%' and convert to float
        value = float(percent_str.rstrip('%'))
        
        if value >= 100.0:
            color = "green"
        elif value >= 75.0:
            color = "yellow"
        else:
            color = "orange1"
        
        text.append(percent_str, style=color)
    except (ValueError, AttributeError):
        # If parsing fails, return as-is
        text.append(str(percent_str))
    
    return text


def _colorize_index(index_name: str) -> Text:
    """Colorize index name parts with different colors.
    
    Splits index names like 'logger_704-2025.10.24' into parts and applies colors:
    - base name (e.g., 'logger'): cyan
    - separators ('_', '-'): dim white
    - numbers: yellow
    - dates: green
    """
    # Pattern to match index components: name, separator, number/date parts
    pattern = r'([a-zA-Z]+)|([_\-])|(\d+(?:\.\d+)*)'
    
    text = Text()
    for match in re.finditer(pattern, index_name):
        part = match.group(0)
        if match.group(1):  # alphabetic part
            text.append(part, style="cyan")
        elif match.group(2):  # separator
            text.append(part, style="dim white")
        elif match.group(3):  # numeric part (including dates like 2025.10.24)
            # Check if it looks like a date pattern
            if '.' in part and len(part) >= 8:
                text.append(part, style="green")
            else:
                text.append(part, style="yellow")
    
    # Fallback: if nothing matched, return plain text
    if len(text) == 0:
        text.append(index_name)
    
    return text


def _shorten_target_fqdn(source_fqdn: str, target_fqdn: str) -> str:
    """Remove common domain suffix from target FQDN.
    
    Keeps only the hostname (first part) and -dataX suffix from target
    if the domain parts match between source and target.
    
    Args:
        source_fqdn: The source node FQDN
        target_fqdn: The target node FQDN
        
    Returns:
        Shortened target FQDN (e.g., "log-datanode13-data1")
    """
    source_parts = source_fqdn.split('.')
    target_parts = target_fqdn.split('.')
    
    if len(source_parts) < 2 or len(target_parts) < 2:
        return target_fqdn
    
    # Extract hostname (first part) from target
    target_hostname = target_parts[0]
    
    # Check if hostname ends with -dataX pattern
    hostname_match = re.match(r'^(.+?)(-data\d+)$', target_hostname)
    
    # Get middle parts (everything except first part)
    source_middle = source_parts[1:]
    target_middle = target_parts[1:]
    
    # Check if last part of source has -dataX, if so compare without it
    source_last = source_parts[-1]
    target_last = target_parts[-1]
    
    source_last_match = re.match(r'^(.+?)(-data\d+)$', source_last)
    target_last_match = re.match(r'^(.+?)(-data\d+)$', target_last)
    
    if source_last_match and target_last_match:
        # Compare middle parts with last part's base (without -dataX)
        source_middle_compare = source_parts[1:-1] + [source_last_match.group(1)]
        target_middle_compare = target_parts[1:-1] + [target_last_match.group(1)]
        
        if source_middle_compare == target_middle_compare:
            # Return just hostname-dataX (replace - with ▪ in -dataX)
            data_suffix = target_last_match.group(2).replace('-', '▪', 1)
            if hostname_match:
                return hostname_match.group(1) + data_suffix
            else:
                return target_hostname + data_suffix
    else:
        # No -dataX pattern, just compare middle parts
        if source_middle == target_middle:
            return target_hostname
    
    return target_fqdn


def _colorize_fqdn(fqdn: str) -> Text:
    """Colorize FQDN parts with different colors.
    
    Splits FQDNs like 'data-node-01.prod.example.com' into parts and applies colors:
    - hostname parts: alternating between cyan, blue, magenta
    - domain parts: green
    - dots: dim white
    - numbers: yellow
    - Replaces -data with ▪data for better visibility
    """
    # Replace -data pattern with ▪data for all instances
    fqdn = re.sub(r'-data(\d+)', r'▪data\1', fqdn)
    
    text = Text()
    parts = fqdn.split('.')
    
    # Use different colors for hostname vs domain
    # Typically first 1-2 parts are hostname, rest is domain
    hostname_colors = ["cyan", "blue", "magenta"]
    
    for i, part in enumerate(parts):
        # Check if part contains numbers or special chars
        if re.search(r'\d', part):
            # Split part into text, numbers, and special chars like ▪
            subparts = re.split(r'(\d+|▪)', part)
            for subpart in subparts:
                if subpart:
                    if subpart.isdigit():
                        text.append(subpart, style="yellow")
                    elif subpart == '▪':
                        text.append(subpart, style="dim white")
                    else:
                        # Use hostname colors for first parts, green for domain
                        color = hostname_colors[i % len(hostname_colors)] if i < 2 else "green"
                        text.append(subpart, style=color)
        else:
            # No numbers, just colorize the whole part
            color = hostname_colors[i % len(hostname_colors)] if i < 2 else "green"
            text.append(part, style=color)
        
        # Add dot separator
        if i < len(parts) - 1:
            text.append(".", style="dim white")
    
    return text


def render_data(data):
    if not data:
        return empty_box("No ongoing shards recovery")

    table = Table(expand=True, border_style="dim")
    for col in COLUMNS:
        table.add_column(col.capitalize().replace("_", " ").replace("percent", "%"))

    for record in data:
        # Colorize the index name and node FQDNs
        # Shorten target node by removing common domain suffix
        source_node = record.get("source_node", "")
        target_node = record.get("target_node", "")
        
        # Shorten target if both source and target exist
        if source_node and target_node:
            shortened_target = _shorten_target_fqdn(source_node, target_node)
        else:
            shortened_target = target_node
        
        row_data = []
        for col in COLUMNS:
            if col == "index":
                row_data.append(_colorize_index(record[col]))
            elif col == "source_node":
                row_data.append(_colorize_fqdn(record[col]))
            elif col == "target_node":
                row_data.append(_colorize_fqdn(shortened_target))
            elif col in ("files_percent", "bytes_percent", "translog_ops_percent"):
                row_data.append(_colorize_percentage(record[col]))
            else:
                row_data.append(record[col])
        table.add_row(*row_data)

    return table
