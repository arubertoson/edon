"""Defines structured error reasons for graph operations within the Edon core.

This module centralizes enumerations used to convey specific reasons for failures
or exceptional conditions encountered during operations on the edon entity system.

The enums are categorized by the type of operation or object they pertain to:
- `SocketConnectionErrorReason`: For issues arising during attempts to connect sockets.
- `GraphObjectErrorReason`: For problems related to the existence or validity of
                             nodes and sockets themselves.
- `SocketDisconnectionErrorReason`: For issues during attempts to disconnect sockets.
"""

from enum import Enum, auto


class SocketLinkErrorReason(Enum):
    """Enumerates reasons why a socket connection attempt might fail."""

    # Compatibility Issues
    CANNOT_LINK_TO_SELF = auto()
    DIRECTIONS_NOT_OPPOSITE = auto()
    SAME_PARENT_NODE = auto()
    TYPE_MISMATCH = auto()
    ALREADY_LINKED = auto()

    # Arity/Limit Issues
    INPUT_SOCKET_FULL = (
        auto()
    )  # e.g., Input socket already has a connection and doesn't allow more
    OUTPUT_SOCKET_LIMIT_REACHED = auto()  # If an output socket had a fan-out limit (less common)

    # General/Other
    TARGET_SOCKET_INVALID = auto()  # Placeholder if other_socket itself is None or invalid
    UNKNOWN = auto()  # Generic fallback
    CYCLE_DETECTED = auto()


class GraphObjectErrorReason(Enum):
    """Enumerates reasons for errors related to graph object (node/socket) access or validity."""

    NODE_NOT_FOUND = auto()
    SOCKET_NOT_FOUND = auto()
    SOCKET_DIRECTION_INVALID = (
        auto()
    )  # e.g. trying to use an input as an output in connect_sockets


class SocketUnlinkErrorReason(Enum):
    """Enumerates reasons why a socket disconnection attempt might fail."""

    SOCKETS_NOT_LINKED = auto()
    UNKNOWN = auto()  # Generic fallback
