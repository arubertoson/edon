"""
Centralized registry for UI item mappings with assertion-based validation.

Maintains synchronized mappings between logical graph entities and their UI
representations. Enforces data integrity through aggressive validation that
crashes the application immediately upon detecting any inconsistency.
"""

from collections import defaultdict
from collections.abc import ValuesView  # Added
from typing import TYPE_CHECKING

from loguru import logger

from edon.graph import EdgeKey, EntityGraph, SocketAddress

if TYPE_CHECKING:
    from edon_ui.items.edge import EdgeItem
    from edon_ui.items.node import NodeItem
    from edon_ui.items.socket import SocketItem


class GraphUIDataRegistry:
    """
    Centralized registry for UI item mappings with assertion-based validation.

    Maintains synchronized mappings between logical graph entities and their UI
    representations. Enforces data integrity through aggressive validation that
    crashes the application immediately upon detecting any inconsistency.
    """

    def __init__(self) -> None:
        self._node_items: dict[str, "NodeItem"] = {}
        self._edge_items: dict["EdgeKey", "EdgeItem"] = {}
        self._socket_items: dict["SocketAddress", "SocketItem"] = {}
        self._socket_to_edge_keys: dict["SocketAddress", set["EdgeKey"]] = defaultdict(set)

        # Track registration sequence for debugging corrupted states
        self._registration_order: list[str] = []

    @property
    def nodes(self) -> ValuesView["NodeItem"]:
        return self._node_items.values()

    @property
    def edges(self) -> ValuesView["EdgeItem"]:
        return self._edge_items.values()

    @property
    def sockets(self) -> ValuesView["SocketItem"]:
        return self._socket_items.values()

    def _assert_invariants(self) -> None:
        """Validates all internal consistency rules and crashes if any are violated."""

        # Socket associations must reference registered sockets
        for socket_addr in self._socket_to_edge_keys:
            assert socket_addr in self._socket_items, (
                f"CORRUPTION: Socket {socket_addr} has edge associations but no registered SocketItem"
            )

        # Edge associations must reference registered edges
        for socket_addr, edge_keys in self._socket_to_edge_keys.items():
            for edge_key in edge_keys:
                assert edge_key in self._edge_items, (
                    f"CORRUPTION: Socket {socket_addr} references non-existent edge {edge_key}"
                )

        # Edges must be bidirectionally associated with their endpoint sockets
        for edge_key, _ in self._edge_items.items():
            source_addr = edge_key.source
            target_addr = edge_key.target

            assert edge_key in self._socket_to_edge_keys[source_addr], (
                f"CORRUPTION: Edge {edge_key} not associated with its source socket {source_addr}"
            )
            assert edge_key in self._socket_to_edge_keys[target_addr], (
                f"CORRUPTION: Edge {edge_key} not associated with its target socket {target_addr}"
            )

        # Socket parent nodes must be registered
        for socket_addr, _ in self._socket_items.items():
            assert socket_addr.node_id in self._node_items, (
                f"CORRUPTION: Socket {socket_addr} belongs to unregistered node {socket_addr.node_id}"
            )

    def register_node_with_sockets(self, node_item: "NodeItem") -> None:
        """Atomically registers a node and all its socket items."""
        node_id = node_item.entity_id

        # Prevent double registration which indicates logic errors
        assert node_id not in self._node_items, (
            f"CORRUPTION: Attempting to register already-registered node {node_id}"
        )

        # Collect socket items and validate they're not already registered
        all_socket_items = node_item.source_sockets + node_item.target_sockets
        socket_addresses = [item.socket_address for item in all_socket_items if item is not None]

        for socket_addr in socket_addresses:
            assert socket_addr not in self._socket_items, (
                f"CORRUPTION: Socket {socket_addr} already registered during node registration"
            )

        # All-or-nothing registration to prevent partial corruption
        try:
            self._node_items[node_id] = node_item
            for socket_item in all_socket_items:
                if socket_item is not None:
                    self._socket_items[socket_item.socket_address] = socket_item

            self._registration_order.append(f"NODE:{node_id}")
            logger.debug(f"Registered node {node_id} with {len(socket_addresses)} sockets")

            # Validate consistency after every state mutation
            self._assert_invariants()

        except Exception as e:
            # Any failure during registration indicates corrupted state
            logger.critical(f"FATAL: Node registration failed for {node_id}, state corrupted: {e}")
            self._dump_debug_state()
            raise RuntimeError(f"Registry corruption during node registration: {e}") from e

    def register_edge_item(self, edge_key: "EdgeKey", edge_item: "EdgeItem") -> None:
        """Registers an edge item with full endpoint validation."""

        # Duplicate edge registration indicates controller logic errors
        assert edge_key not in self._edge_items, f"CORRUPTION: Edge {edge_key} already registered"

        # Endpoint sockets must exist before edge creation
        assert edge_key.source in self._socket_items, (
            f"CORRUPTION: Cannot register edge {edge_key} - source socket {edge_key.source} not registered"
        )
        assert edge_key.target in self._socket_items, (
            f"CORRUPTION: Cannot register edge {edge_key} - target socket {edge_key.target} not registered"
        )

        try:
            # Atomic registration of edge and bidirectional socket associations
            self._edge_items[edge_key] = edge_item
            self._socket_to_edge_keys[edge_key.source].add(edge_key)
            self._socket_to_edge_keys[edge_key.target].add(edge_key)

            self._registration_order.append(f"EDGE:{edge_key}")
            logger.debug(f"Registered edge {edge_key}")

            # Ensure consistency after state modification
            self._assert_invariants()

        except Exception as e:
            logger.critical(
                f"FATAL: Edge registration failed for {edge_key}, state corrupted: {e}"
            )
            self._dump_debug_state()
            raise RuntimeError(f"Registry corruption during edge registration: {e}") from e

    def unregister_node(
        self, node_id: str
    ) -> tuple["NodeItem", list["SocketItem"], list["EdgeItem"]]:
        """Removes a node and cascades to all dependent sockets and edges."""

        # Node must exist for unregistration
        assert node_id in self._node_items, (
            f"CORRUPTION: Cannot unregister non-existent node {node_id}"
        )

        node_item = self._node_items[node_id]

        # Identify all dependent items that must be removed
        node_socket_addrs = [addr for addr in self._socket_items.keys() if addr.node_id == node_id]

        # Find edges connected to any socket of this node
        edges_to_remove: set["EdgeKey"] = set()
        for socket_addr in node_socket_addrs:
            edges_to_remove.update(self._socket_to_edge_keys[socket_addr])

        try:
            # Remove in dependency order: edges → sockets → node
            removed_edges_items = []
            for edge_key_to_remove in list(
                edges_to_remove
            ):  # Iterate over a copy as unregister_edge modifies the sets
                removed_edges_items.append(self.unregister_edge(edge_key_to_remove))

            removed_sockets = []
            for socket_addr in node_socket_addrs:
                removed_sockets.append(self._unregister_socket_internal(socket_addr))

            # Remove the node itself
            del self._node_items[node_id]
            self._registration_order.append(f"UNREGISTER_NODE:{node_id}")

            logger.debug(
                f"Cascade unregistered node {node_id} ({len(removed_edges)} edges, {len(removed_sockets)} sockets)"
            )

            # Validate consistency after cascade operation
            self._assert_invariants()

            return node_item, removed_sockets, removed_edges_items

        except Exception as e:
            logger.critical(f"FATAL: Cascade unregistration failed for node {node_id}: {e}")
            self._dump_debug_state()
            raise RuntimeError(f"Registry corruption during cascade unregistration: {e}") from e

    def unregister_edge(self, edge_key: "EdgeKey") -> "EdgeItem":
        """
        Removes a specific edge UI item and its associations from the registry.

        This method asserts that the edge exists before attempting removal. It cleans up
        the edge's references from its connected sockets and ensures registry invariants
        are maintained.
        """
        assert edge_key in self._edge_items, (
            f"CORRUPTION: Attempting to unregister non-existent edge {edge_key}"
        )

        edge_item = self._edge_items.pop(edge_key)

        # Clean up bidirectional socket associations
        source_addr = edge_key.source
        if source_addr in self._socket_to_edge_keys:
            self._socket_to_edge_keys[source_addr].discard(edge_key)
            if not self._socket_to_edge_keys[source_addr]:  # Remove empty set
                del self._socket_to_edge_keys[source_addr]

        target_addr = edge_key.target
        if target_addr in self._socket_to_edge_keys:
            self._socket_to_edge_keys[target_addr].discard(edge_key)
            if not self._socket_to_edge_keys[target_addr]:  # Remove empty set
                del self._socket_to_edge_keys[target_addr]

        self._registration_order.append(f"UNREGISTER_EDGE:{edge_key}")
        logger.debug(f"Unregistered edge {edge_key}")

        self._assert_invariants()
        return edge_item

    def _unregister_socket_internal(self, socket_addr: "SocketAddress") -> "SocketItem":
        """Removes a socket and validates no edges are still associated."""
        assert socket_addr in self._socket_items, (
            f"CORRUPTION: Socket {socket_addr} not registered"
        )
        assert not self._socket_to_edge_keys[socket_addr], (
            f"CORRUPTION: Attempting to unregister socket {socket_addr} with remaining edge associations: {self._socket_to_edge_keys[socket_addr]}"
        )

        socket_item = self._socket_items[socket_addr]
        del self._socket_items[socket_addr]
        del self._socket_to_edge_keys[socket_addr]  # Remove the empty set entry

        return socket_item

    def node_item_for_id(self, node_id: str) -> "NodeItem":
        """Retrieves the node item for the given ID."""
        assert node_id in self._node_items, (
            f"CORRUPTION: Requested non-existent node {node_id}. Available: {list(self._node_items.keys())}"
        )
        return self._node_items[node_id]

    def edge_items_for_socket(self, socket_addr: "SocketAddress") -> set["EdgeItem"]:
        """Retrieves all edge items connected to the specified socket."""
        assert socket_addr in self._socket_items, (
            f"CORRUPTION: Requested edges for non-existent socket {socket_addr}"
        )

        edge_keys = self._socket_to_edge_keys[socket_addr]
        edge_items = set()

        for edge_key in edge_keys:
            # Every socket association must reference a valid edge
            assert edge_key in self._edge_items, (
                f"CORRUPTION: Socket {socket_addr} references non-existent edge {edge_key}"
            )
            edge_items.add(self._edge_items[edge_key])

        return edge_items

    def socket_item_for_address(self, socket_addr: "SocketAddress") -> "SocketItem":
        """Retrieves the socket item for the given address."""
        assert socket_addr in self._socket_items, (
            f"CORRUPTION: Requested non-existent socket {socket_addr}. Available: {list(self._socket_items.keys())}"
        )
        return self._socket_items[socket_addr]

    def _dump_debug_state(self) -> None:
        """Outputs complete registry state for post-mortem analysis."""
        logger.critical("=== REGISTRY STATE DUMP ===")
        logger.critical(f"Nodes: {len(self._node_items)} registered")
        logger.critical(f"Edges: {len(self._edge_items)} registered")
        logger.critical(f"Sockets: {len(self._socket_items)} registered")
        logger.critical(
            f"Socket-Edge associations: {len(self._socket_to_edge_keys)} sockets with edges"
        )
        logger.critical(
            f"Registration order: {self._registration_order[-10:]}"
        )  # Recent operations only

        # Identify specific corruption patterns
        orphaned_sockets = [
            addr for addr in self._socket_to_edge_keys if addr not in self._socket_items
        ]
        if orphaned_sockets:
            logger.critical(f"ORPHANED SOCKET ASSOCIATIONS: {orphaned_sockets}")

    def validate_against_entity_graph(self, entity_graph: "EntityGraph") -> None:
        """Cross-validates registry state against the logical entity graph."""

        # UI nodes must correspond to entity graph nodes
        for node_id in self._node_items:
            assert entity_graph.get_node(node_id) is not None, (
                f"CORRUPTION: UI node {node_id} exists but not in entity graph"
            )

        # UI edges must correspond to actual socket links
        for edge_key in self._edge_items:
            source_node = entity_graph.get_node(edge_key.source.node_id)
            target_node = entity_graph.get_node(edge_key.target.node_id)

            assert source_node is not None, (
                f"CORRUPTION: Edge {edge_key} references non-existent source node"
            )
            assert target_node is not None, (
                f"CORRUPTION: Edge {edge_key} references non-existent target node"
            )

            # Verify the logical socket connection exists
            source_socket = source_node.source_sockets.get(edge_key.source.name)
            target_socket = target_node.target_sockets.get(edge_key.target.name)

            assert source_socket is not None, (
                f"CORRUPTION: Edge {edge_key} references non-existent source socket"
            )
            assert target_socket is not None, (
                f"CORRUPTION: Edge {edge_key} references non-existent target socket"
            )
            assert target_socket in source_socket.links, (
                f"CORRUPTION: UI edge {edge_key} exists but entity sockets not linked"
            )
