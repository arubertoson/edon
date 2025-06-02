"""Parameter system for sub-graph nodes.

This module provides the data structures for exposing internal node sockets
as configurable parameters on sub-graph nodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edon.types import SocketAddress


@dataclass
class ParameterMapping:
    """Maps a sub-graph parameter name to a socket that should receive the parameter value.
    
    This is a simple mapping that relies on SocketAddress to uniquely identify
    the target socket. All type information and defaults are derived from the
    actual socket at runtime.
    """
    parameter_name: str
    target_socket_addr: SocketAddress


@dataclass
class SubGraphParameter:
    """A parameter exposed by the sub-graph.
    
    The parameter's type and default value are derived from the target socket,
    not stored here. This keeps the parameter system simple and avoids duplication.
    """
    name: str
    current_value: Any = None
    description: str = ""
