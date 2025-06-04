from __future__ import annotations
from loguru import logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from edon.graph import EntityGraph
    from edon.subgraph.node import SubGraphNode
    from edon_ui.graph.registry import GraphUIDataRegistry
    from edon_ui.views.scene import GraphicsScene


class NavigationState:
    """
    A simple data class to hold the state for a single navigation level.
    """

    def __init__(
        self,
        graph: EntityGraph,
        scene: GraphicsScene,
        registry: GraphUIDataRegistry,
        originating_subgraph_node: SubGraphNode | None = None,
    ):
        self.graph = graph
        self.scene = scene
        self.registry = registry
        # The SubGraphNode instance that was entered to reach this level.
        # None for the root graph.
        self.originating_subgraph_node = originating_subgraph_node


class GraphContextStack:
    """
    Manages the state of navigation through a hierarchy of graphs (e.g., entering subgraphs).

    It maintains stacks for the logical EntityGraph, the corresponding UI GraphicsScene,
    and the GraphUIDataRegistry for that scene.
    """

    def __init__(self) -> None:
        self._navigation_stack: list[NavigationState] = []

    def initialize(
        self,
        root_graph: EntityGraph,
        root_scene: GraphicsScene,
        root_registry: GraphUIDataRegistry,
    ) -> None:
        """
        Initializes the navigation state with the root graph.
        """
        root_level_state = NavigationState(
            graph=root_graph,
            scene=root_scene,
            registry=root_registry,
            originating_subgraph_node=None,
        )
        # During a initialize we have to reset the whole stack, the assumption
        # is that you only do init from the root graph.
        self._navigation_stack = [root_level_state]

    def push_level(self, NavigationState) -> None:
        """
        Pushes a new navigation level (e.g., after entering a subgraph).
        """
        logger.error(f"CREATING NEW STACK {self.depth}")
        self._navigation_stack.append(NavigationState)

    def pop_level(self) -> NavigationState | None:
        """
        Pops the current navigation level, returning to the previous one.
        Returns the state of the level that was popped, or None if at root or uninitialized.
        """
        assert self._navigation_stack, "CORRUPTION: Cannot pop from an empty navigation stack"
        if self.is_at_root():
            return None

        return self._navigation_stack.pop()

    @property
    def current_level(self) -> NavigationState:
        """
        Gets the state of the current (topmost) navigation level.
        Returns None if the stack is empty (e.g., before initialization).
        """
        level = self._navigation_stack[-1]
        assert level is not None, (
            f"CORRUPTION: {self.__class__.__name__} level should never be None"
        )

        return level

    @property
    def current_graph(self) -> EntityGraph:
        """The logical graph of the current navigation level."""
        level = self.current_level
        return level.graph

    @property
    def current_scene(self) -> GraphicsScene:
        """The UI scene corresponding to the current navigation level."""
        level = self.current_level
        return level.scene

    @property
    def current_registry(self) -> GraphUIDataRegistry:
        """The UI data registry for the current scene."""
        level = self.current_level
        return level.registry

    @property
    def current_path_nodes(self) -> list[SubGraphNode]:
        """
        Returns the list of SubGraphNode instances that form the path from the root
        to the current level (excluding the root itself, which has no originating node).
        """
        return [
            level.originating_subgraph_node
            for level in self._navigation_stack[1:]  # Skip root's state object
            if level.originating_subgraph_node is not None
        ]

    def is_at_root(self) -> bool:
        """Checks if the current navigation level is the root."""
        return len(self._navigation_stack) == 1

    @property
    def depth(self) -> int:
        """Returns the current depth of the navigation stack (root is depth 1)."""
        return len(self._navigation_stack)
