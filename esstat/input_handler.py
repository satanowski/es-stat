# -*- coding: utf-8 -*-
"""
Terminal input handling for EsStat.

Provides keyboard input capture in raw terminal mode with support for
arrow keys and special character sequences.
"""

import asyncio
import contextlib
import sys
import termios
import tty
from typing import Optional


@contextlib.contextmanager
def raw_mode(stream):
    """Context manager to set terminal to raw/cbreak mode."""
    fd = stream.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class KeyListener:
    """
    Asynchronous keyboard input listener.
    
    Captures individual keystrokes and escape sequences (arrow keys)
    in non-blocking fashion using asyncio event loop.
    """

    def __init__(self, stream):
        self.stream = stream
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._loop = asyncio.get_running_loop()
        self._fd = stream.fileno()
        self._active = False
        self._escape_buffer: list[str] = []  # Buffer for escape sequences

    def start(self) -> bool:
        """Start listening for keyboard input. Returns True on success."""
        add_reader = getattr(self._loop, "add_reader", None)
        if not callable(add_reader):
            return False
        try:
            add_reader(self._fd, self._on_input_ready)
        except NotImplementedError:
            return False
        self._active = True
        return True

    def stop(self) -> None:
        """Stop listening for keyboard input."""
        if self._active:
            remove_reader = getattr(self._loop, "remove_reader", None)
            if callable(remove_reader):
                remove_reader(self._fd)
        self._active = False

    def drain(self) -> list[str]:
        """Drain all pending characters from the queue."""
        drained: list[str] = []
        while True:
            try:
                drained.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return drained

    def parse_keys(self, chars: list[str]) -> list[str]:
        """
        Parse character list into key events, handling escape sequences.
        
        Arrow keys are represented as: UP, DOWN, LEFT, RIGHT
        Other keys are returned as-is.
        """
        keys = []
        i = 0

        # Add buffered escape sequence characters from previous parse
        if self._escape_buffer:
            chars = self._escape_buffer + chars
            self._escape_buffer = []

        while i < len(chars):
            if chars[i] == "\x1b":
                # Start of potential escape sequence
                if i + 1 < len(chars) and chars[i + 1] == "[":
                    if i + 2 < len(chars):
                        # We have all three characters
                        if chars[i + 2] == "A":
                            keys.append("UP")
                            i += 3
                            continue
                        elif chars[i + 2] == "B":
                            keys.append("DOWN")
                            i += 3
                            continue
                        elif chars[i + 2] == "C":
                            keys.append("RIGHT")
                            i += 3
                            continue
                        elif chars[i + 2] == "D":
                            keys.append("LEFT")
                            i += 3
                            continue
                        else:
                            # Unknown escape sequence, treat as regular keys
                            keys.append(chars[i])
                            i += 1
                    else:
                        # Incomplete sequence - buffer it for next time
                        self._escape_buffer = chars[i:]
                        break
                elif i + 1 >= len(chars):
                    # Incomplete sequence - buffer it for next time
                    self._escape_buffer = chars[i:]
                    break
                else:
                    # Not an arrow key escape sequence
                    keys.append(chars[i])
                    i += 1
            else:
                # Regular key
                keys.append(chars[i])
                i += 1
        return keys

    def _on_input_ready(self) -> None:
        """Internal callback when input is ready to read."""
        char = self.stream.read(1)
        if char:
            self._queue.put_nowait(char)


def get_key_context():
    """
    Get appropriate context manager for keyboard input.
    
    Returns raw_mode context if stdin is a TTY, otherwise nullcontext.
    """
    if sys.stdin.isatty():
        return raw_mode(sys.stdin)
    return contextlib.nullcontext()


def create_key_listener() -> Optional[KeyListener]:
    """
    Create and start a KeyListener if stdin is a TTY.
    
    Returns None if stdin is not a TTY or listener fails to start.
    """
    if not sys.stdin.isatty():
        return None
    
    listener = KeyListener(sys.stdin)
    if listener.start():
        return listener
    return None
