"""Defines utility nodes for the Edon graph system.

Utility nodes are special-purpose nodes that assist in graph management,
UI interactions, or other non-data-processing tasks.
"""

from __future__ import annotations

from edon.node import EntityNode
from edon.types import SocketDef, SocketDisplayState
from edon_ui.widgets.factories import SocketType


class SubgraphPromoterNode(EntityNode):
    """
    A utility node used within a graphs editing view to expose internal sockets
    to the parent SubGraphNode's interface.

    When a user drags an edge from an internal node's socket and drops it onto
    one of this node's special sockets, it signals an intent to create a
    corresponding proxy socket on the containing SubGraphNode.
    """

    node_type = "utility.subgraph.promoter"

    target_socket_definitions = [
        SocketDef(
            name="trg_promoter",
            socket_type=SocketType.ANY,
            display_state=SocketDisplayState.LINK_LABEL,
        ),
    ]

    source_socket_definitions = [
        SocketDef(
            name="src_promoter",
            socket_type=SocketType.ANY,
            display_state=SocketDisplayState.LINK_LABEL,
        ),
    ]
