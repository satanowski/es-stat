# pylint: disable=missing-module-docstring,missing-function-docstring

import re

from rich.table import Table
from rich.text import Text

from .common import empty_box

COLUMNS = ("index", "shard", "prirep", "state", "store", "docs", "ip", "source_node", "target_node")

FILTER_OUT = ("UNASSIGNED",)


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


def _colorize_ip(ip_address: str) -> Text:
    """Colorize IP address octets with different colors.
    
    Splits IP addresses like '192.168.1.100' into octets and applies colors:
    - 1st octet: magenta
    - 2nd octet: blue
    - 3rd octet: cyan
    - 4th octet: yellow
    - dots: dim white
    """
    text = Text()
    parts = ip_address.split('.')
    
    if len(parts) == 4:  # IPv4 address
        colors = ["magenta", "blue", "cyan", "yellow"]
        for i, part in enumerate(parts):
            text.append(part, style=colors[i])
            if i < 3:
                text.append(".", style="dim white")
    else:
        # Fallback for non-standard IP formats
        text.append(ip_address)
    
    return text


def _clean_node_name(node_field: str) -> str:
    """Remove node ID hash from node field.
    
    The node field from _cat/shards can contain:
    '10.73.161.124 9U9EdMvXTfmkeXnKGZW5aA log-datanode15.logger-prod.pl-kra-6.dc4.local-data1'
    
    This function removes the node ID (the hash between IP and FQDN), keeping:
    '10.73.161.124 log-datanode15.logger-prod.pl-kra-6.dc4.local-data1'
    """
    # Pattern to match and remove the node ID hash (typically 22 alphanumeric characters)
    # It appears after an IP address and before a FQDN
    # Match: IP_ADDRESS HASH FQDN and replace with: IP_ADDRESS FQDN
    pattern = r'(\d+\.\d+\.\d+\.\d+)\s+[a-zA-Z0-9_-]{20,24}\s+([a-zA-Z0-9\.-]+)'
    cleaned = re.sub(pattern, r'\1 \2', node_field)
    
    return cleaned


def _colorize_source_node(source_field: str) -> Text:
    """Colorize source node FQDN.
    
    Simply colorizes the source FQDN using the standard FQDN color scheme.
    """
    return _colorize_fqdn_internal(source_field)


def _colorize_target_node(target_field: str, source_field: str = "") -> Text:
    """Colorize target node with IP and FQDN.
    
    Target field format: "IP FQDN" or "IP HASH FQDN"
    Simplifies target FQDN by removing common domain parts if source is provided.
    """
    # Clean the target field first
    target_field = _clean_node_name(target_field)
    
    text = Text()
    
    # Separate IP and FQDN components
    target_components = target_field.split()
    target_ip = None
    target_fqdn = None
    
    for component in target_components:
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', component):
            target_ip = component
        else:
            target_fqdn = component
    
    # Display in order: FQDN then IP
    if target_fqdn:
        shortened_target = target_fqdn
        
        # Simplify target FQDN by removing common domain parts if source provided
        if source_field:
            source_parts = source_field.split('.')
            target_parts = target_fqdn.split('.')
            
            if len(source_parts) >= 2 and len(target_parts) >= 2:
                # Extract hostname (first part) from target
                target_hostname = target_parts[0]
                
                # Get last parts to check for -dataX pattern
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
                        hostname_match = re.match(r'^(.+?)(-data\d+)$', target_hostname)
                        if hostname_match:
                            shortened_target = hostname_match.group(1) + data_suffix
                        else:
                            shortened_target = target_hostname + data_suffix
                else:
                    # No -dataX pattern, just compare middle parts
                    source_middle = source_parts[1:]
                    target_middle = target_parts[1:]
                    if source_middle == target_middle:
                        shortened_target = target_hostname
        
        text.append(_colorize_fqdn_internal(shortened_target))
    
    if target_ip:
        if target_fqdn:
            text.append(" ", style="dim white")
        text.append(_colorize_ip(target_ip))
    
    return text


def _colorize_fqdn_internal(fqdn: str) -> Text:
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
        return empty_box("No active shards relocation")

    table = Table(expand=True, border_style="dim")
    for col in COLUMNS:
        table.add_column(col.capitalize().replace("_", " "))

    for rec in filter(lambda r: r.get("state") not in FILTER_OUT, data):
        # Colorize the index name, IP address, and source/target nodes
        row_data = []
        
        for col in COLUMNS:
            if col == "index":
                row_data.append(_colorize_index(rec["index"]))
            elif col == "ip":
                row_data.append(_colorize_ip(rec["ip"]))
            elif col == "source_node":
                # Source field is pre-split by data_handler
                row_data.append(_colorize_source_node(rec.get("source", "")))
            elif col == "target_node":
                # Target field is pre-split by data_handler
                # Pass source to enable FQDN simplification
                row_data.append(_colorize_target_node(rec.get("target", ""), rec.get("source", "")))
            else:
                row_data.append(rec[col])
        table.add_row(*row_data)

    return table
