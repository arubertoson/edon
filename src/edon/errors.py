from enum import Enum, auto


class SocketConnectionErrorReason(Enum):
    # Compatibility Issues
    CANNOT_CONNECT_TO_SELF = auto()
    DIRECTIONS_NOT_OPPOSITE = auto()
    SAME_PARENT_NODE = auto()
    TYPE_MISMATCH = auto()

    # Arity/Limit Issues
    INPUT_SOCKET_FULL = auto()  # e.g., Input socket already has a connection and doesn't allow more
    OUTPUT_SOCKET_LIMIT_REACHED = auto()  # If an output socket had a fan-out limit (less common)

    # General/Other
    TARGET_SOCKET_INVALID = auto()  # Placeholder if other_socket itself is None or invalid
    UNKNOWN = auto()  # Generic fallback


class GraphObjectErrorReason(Enum):
    NODE_NOT_FOUND = auto()
    SOCKET_NOT_FOUND = auto()
    SOCKET_DIRECTION_INVALID = auto()  # e.g. trying to use an input as an output in connect_sockets


class SocketDisconnectionErrorReason(Enum):
    SOCKETS_NOT_CONNECTED = auto()
    UNKNOWN = auto() # Generic fallback
