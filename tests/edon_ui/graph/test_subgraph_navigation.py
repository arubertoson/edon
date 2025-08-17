from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

from edon.graph import EntityGraph
from edon.subgraph.node import SubGraphNode

# Assuming IntegerNode is a simple concrete EntityNode for testing
# If 'examples' is not in PYTHONPATH for tests, this might need adjustment
# (e.g., define a minimal node here or use a test-specific utility).
from examples.custom_nodes import IntegerNode

from edon_ui.graph.controller import WorkspaceController
from edon_ui.views.viewer import EditorContext
from edon_ui.commands.actions.basic_actions import (
    action_enter_subgraph,
    action_exit_subgraph,
)

if TYPE_CHECKING:
    from edon.node import EntityNode
    from edon_ui.items.node import NodeItem


@pytest.fixture
def workspace_controller() -> WorkspaceController:
    """Provides a WorkspaceController instance."""
    # Controller initializes with an empty root graph and scene
    return WorkspaceController()


@pytest.fixture
def simple_internal_node() -> EntityNode:
    """A simple node for internal graphs."""
    return IntegerNode(name="InternalNode_1")


@pytest.fixture
def subgraph_node_entity(simple_internal_node: EntityNode) -> SubGraphNode:
    """Creates a SubGraphNode entity with a simple internal graph."""
    internal_graph = EntityGraph()
    internal_graph.add_node(simple_internal_node)

    subgraph_entity = SubGraphNode(name="MySubGraphNode")
    # Assign the pre-populated internal graph
    subgraph_entity.internal_graph = internal_graph
    return subgraph_entity


@pytest.fixture
def regular_node_entity() -> EntityNode:
    """A simple regular EntityNode entity."""
    return IntegerNode(name="MyRegularNode")


class TestSubgraphNavigation:
    def test_full_enter_and_exit_subgraph_workflow(
        self,
        workspace_controller: WorkspaceController,
        subgraph_node_entity: SubGraphNode,
    ):
        """Tests the complete workflow of entering and exiting a subgraph."""
        # Setup: Create a root graph and add the SubGraphNode to it
        root_graph = EntityGraph()
        root_graph.add_node(subgraph_node_entity)
        workspace_controller.load_graph(root_graph)

        # Initial state assertions
        assert workspace_controller.context_stack.is_at_root()
        assert workspace_controller.context_stack.depth == 1
        original_scene = workspace_controller.scene
        original_graph = workspace_controller.graph
        assert (
            original_graph is root_graph
        )  # After load_graph, controller's graph should be the new root graph instance
        assert len(original_scene.items()) > 0  # Nodes should be populated

        # Get the NodeItem for the SubGraphNode
        subgraph_node_item = workspace_controller.registry.node_item_for_id(
            subgraph_node_entity.id
        )
        assert subgraph_node_item is not None

        # --- Enter Subgraph ---
        enter_context = EditorContext(
            controller=workspace_controller,
            view=workspace_controller.view,
            selected_items=[subgraph_node_item],
            event=None,
        )
        enter_success = action_enter_subgraph(enter_context)

        assert enter_success is True
        assert not workspace_controller.context_stack.is_at_root()
        assert workspace_controller.context_stack.depth == 2

        current_nav_state = workspace_controller.context_stack.current
        assert current_nav_state.graph is subgraph_node_entity.internal_graph
        assert workspace_controller.graph is subgraph_node_entity.internal_graph
        assert workspace_controller.scene is not original_scene
        assert current_nav_state.origin_subgraph_node is subgraph_node_entity

        # Check if the new scene is populated with the internal graph's contents
        # (e.g., simple_internal_node should be there)
        internal_node_ui_item = workspace_controller.registry.node_item_for_id(
            subgraph_node_entity.internal_graph.nodes.values_list()[0].id
        )
        assert internal_node_ui_item is not None
        assert len(workspace_controller.scene.items()) >= 1  # At least the internal node

        # --- Exit Subgraph ---
        exit_context = EditorContext(
            controller=workspace_controller,
            view=workspace_controller.view,
            selected_items=[],  # Selection doesn't matter for exit
            event=None,
        )
        exit_success = action_exit_subgraph(exit_context)

        assert exit_success is True
        assert workspace_controller.context_stack.is_at_root()
        assert workspace_controller.context_stack.depth == 1
        assert (
            workspace_controller.graph is original_graph
        )  # Should be back to the root graph instance
        assert (
            workspace_controller.scene is original_scene
        )  # Should be back to the root scene instance

        # Verify root scene content is back
        root_subgraph_node_item_after_exit = workspace_controller.registry.node_item_for_id(
            subgraph_node_entity.id
        )
        assert root_subgraph_node_item_after_exit is not None

    @pytest.mark.parametrize(
        "selected_items_config",
        [
            "no_selection",
            "non_subgraph_selected",
            "multiple_selected",
        ],
    )
    def test_enter_subgraph_conditions(
        self,
        workspace_controller: WorkspaceController,
        subgraph_node_entity: SubGraphNode,
        regular_node_entity: EntityNode,
        selected_items_config: str,
    ):
        """Tests conditions under which entering a subgraph should fail."""
        root_graph = EntityGraph(id="root_test_graph_conditions")
        root_graph.add_node(subgraph_node_entity)
        root_graph.add_node(regular_node_entity)
        workspace_controller.load_graph(root_graph)

        initial_depth = workspace_controller.context_stack.depth
        selected_node_items: list[NodeItem] = []

        subgraph_node_item = workspace_controller.registry.node_item_for_id(
            subgraph_node_entity.id
        )
        regular_node_item = workspace_controller.registry.node_item_for_id(regular_node_entity.id)

        if selected_items_config == "no_selection":
            selected_node_items = []
        elif selected_items_config == "non_subgraph_selected":
            selected_node_items = [regular_node_item]
        elif selected_items_config == "multiple_selected":
            selected_node_items = [subgraph_node_item, regular_node_item]

        context = EditorContext(
            controller=workspace_controller,
            view=workspace_controller.view,
            selected_items=selected_node_items,
            event=None,
        )
        success = action_enter_subgraph(context)

        assert success is False, (
            f"Expected action_enter_subgraph to fail for config: {selected_items_config}"
        )
        assert workspace_controller.context_stack.depth == initial_depth
        assert workspace_controller.graph is root_graph  # Ensure graph context didn't change

    def test_exit_subgraph_at_root(self, workspace_controller: WorkspaceController):
        """Tests that exiting a subgraph fails if already at the root level."""
        # Controller starts at root by default
        assert workspace_controller.context_stack.is_at_root()
        initial_depth = workspace_controller.context_stack.depth

        context = EditorContext(
            controller=workspace_controller,
            view=workspace_controller.view,
            selected_items=[],
            event=None,
        )
        success = action_exit_subgraph(context)

        assert success is False
        assert workspace_controller.context_stack.is_at_root()
        assert workspace_controller.context_stack.depth == initial_depth
