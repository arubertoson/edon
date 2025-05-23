

    def _register_new_node(self, entity_node: EntityNode, ui_node: NodeItem) -> None:
        """Registers a new node in both entity graph and internal UI maps.

        If the entity_node is not already in the entity_graph, it's added.
        The UI node is added to the graphics scene.
        Mappings are updated for node_map and socket_row_map.

        Args:
            entity_node: The core data representation of the node.
            ui_node: The graphical representation of the node.
        """
        node_id = entity_node.id
        if node_id not in self.entity_graph.nodes:
            self.entity_graph.add_node(entity_node)

        self.graphics_scene.add_node(ui_node)
        self.node_map[node_id] = ui_node

        for row in ui_node._target_sockets:
            key = SocketRowAddress(node_id=node_id, socket_name=row.socket_entity_name, is_target=True)
            self.socket_row_map[key] = row
        for row in ui_node._source_sockets:
            key = SocketRowAddress(node_id=node_id, socket_name=row.socket_entity_name, is_target=False)
            self.socket_row_map[key] = row

    def _register_new_edge(self, edge_key: EdgeKey, edge_item: EdgeItem):
        """Registers a new edge item in the graphics scene and internal edge_map.

        Args:
            edge_key: The unique key identifying the edge connection.
            edge_item: The graphical representation of the edge.
        """
        self.graphics_scene.add_edge(edge_item)
        self.edge_map[edge_key] = edge_item

    def _clear_scene_for_population(self):
        """Clears UI elements from the scene and internal maps before repopulation.

        This method iterates through scene items, removing NodeItem and EdgeItem
        instances. It also clears the controller's internal node_map and edge_map
        to ensure a fresh state before repopulating from the model and to prevent
        stale references.
        """
        # Assuming graphics_scene.clear() is the standard Qt method that removes all items.
        # If GraphicsScene has custom lists like self.node_items, self.edge_items,
        # it should have its own comprehensive clear method that also clears those lists.
        # For now, we rely on the fact that addItem in GraphicsScene seems to manage its own list.

        # XXX: This is also curious, it's the best failsafe there is but we should really
        # use the controller maps to delete things.

        # Let's iterate and remove items that are NodeItem or EdgeItem to be safe
        items_to_remove: list[NodeItem | EdgeItem] = []
        for item in self.graphics_scene.items():
            if isinstance(item, (NodeItem, EdgeItem)):
                items_to_remove.append(item)

        for item in items_to_remove:
            self.graphics_scene.removeItem(item)  # Use scene's removeItem

        self.node_map.clear()
        self.edge_map.clear()

    def _populate_nodes(self):
        """Populates NodeItems in the graphics scene based on the entity_graph.

        Nodes are laid out in a simple grid for now. More sophisticated layout algorithms
        might be integrated in the future if needed.
        """
        logger.info(f"Populating UI with {len(self.entity_graph.nodes)} entity nodes.")
        default_x, default_y = 50.0, 50.0
        spacing_x = theme.NODE_MIN_WIDTH + 50.0
        spacing_y = theme.NODE_MIN_HEIGHT + 50.0
        nodes_per_row = 5

        for i, (node_id, entity_node) in enumerate(self.entity_graph.nodes.items()):
            pos_x = default_x + (i % nodes_per_row) * spacing_x
            pos_y = default_y + (i // nodes_per_row) * spacing_y
            logger.debug(f"  Creating NodeItem for '{entity_node.name}' (ID: {node_id}) at ({pos_x}, {pos_y})")

            ui_node = create_node_item(entity_node, pos_x, pos_y, controller=self)
            self._register_new_node(entity_node, ui_node)

        logger.debug("Node population complete.")

    def _populate_edges(self):
        """Populates EdgeItems in the graphics scene based on entity_graph connections.

        Iterates through all connections in the entity_graph and creates corresponding
        EdgeItem instances in the UI, linking the appropriate socket UI elements.
        """
        logger.debug("Populating UI edges...")
        processed_connections: set[EdgeKey] = set()

        for _, source_entity_node in self.entity_graph.nodes.items():
            for _, source_entity_socket in source_entity_node.target_sockets.items():
                for target_entity_socket in source_entity_socket.links:
                    edge_key = EdgeKey(  # Changed to use EdgeKey constructor
                        SocketAddress(source_entity_node.id, source_entity_socket.name),
                        SocketAddress(target_entity_socket.node.id, target_entity_socket.name),
                    )
                    if edge_key in processed_connections:
                        continue
                    processed_connections.add(edge_key)

                    source_ui_socket_row = self.socket_row_map.get(
                        SocketRowAddress(
                            node_id=source_entity_node.id, socket_name=source_entity_socket.name, is_target=False
                        )
                    )
                    target_ui_socket_row = self.socket_row_map.get(
                        SocketRowAddress(
                            node_id=target_entity_socket.node.id,
                            socket_name=target_entity_socket.name,
                            is_target=True,
                        )
                    )

                    logger.debug(
                        f"  Creating EdgeItem: {source_entity_node.id}::{source_entity_socket.name} -> "
                        f"{target_entity_socket.node.id}::{target_entity_socket.name}"
                    )
                    ui_edge = create_edge_item(source_ui_socket_row.circle, target_ui_socket_row.circle)
                    self._register_new_edge(edge_key, ui_edge)

        logger.debug("Edge population complete.")

    def sync_scene_from_graph(self):
        """
        Clears the current UI scene and repopulates it with NodeItems and EdgeItems
        based on the current state of the self.entity_graph.
        This ensures the UI accurately reflects the underlying graph model.
        """
        self._clear_scene_for_population()
        self._populate_nodes()
        self._populate_edges()
        logger.info("Scene population complete (nodes and edges).")

