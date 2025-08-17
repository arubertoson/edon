"""
Manages the context stack for navigating through nested graphs in the UI.

This module provides classes to track the current graph, scene, and registry
when entering and exiting subgraphs, ensuring the UI state remains synchronized
with the logical graph hierarchy.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from edon.graph import EntityGraph, EntitySubGraphNode
    from edon_ui.graph.registry import WorkspaceUIDataRegistry
    from edon_ui.views.scene import GraphicsScene


class ContextState:
    """
    A simple data class to hold the state for a single navigation level.
    """

    def __init__(
        self,
        graph: EntityGraph,
        scene: GraphicsScene,
        registry: WorkspaceUIDataRegistry,
        origin_subgraph_node: EntitySubGraphNode | None = None,
    ):
        self.graph = graph
        self.scene = scene
        self.registry = registry
        # The SubGraphNode instance that was entered to reach this level.
        # None for the root graph.
        self.origin_subgraph_node = origin_subgraph_node


class WorkspaceContextStack:
    """
    Manages the state of navigation through a hierarchy of graphs (e.g., entering subgraphs).

    It maintains stacks for the logical EntityGraph, the corresponding UI GraphicsScene,
    and the GraphUIDataRegistry for that scene.
    """

    def __init__(self) -> None:
        self._stacks: list[ContextState] = []

    def initialize(self, context_state: ContextState) -> None:
        """
        Initializes the navigation state with the root graph.
        """
        # During a initialize we have to reset the whole stack, the assumption
        # is that you only do init from the root graph.
        self._stacks = [context_state]

    @property
    def current(self) -> ContextState:
        """
        Gets the state of the current (topmost) navigation level.
        Returns None if the stack is empty (e.g., before initialization).
        """
        stack = self._stacks[-1]
        assert stack is not None, (
            f"CORRUPTION: {self.__class__.__name__} level should never be None"
        )

        return stack

    @property
    def parent(self) -> ContextState | None:
        if self.is_at_root():
            return None

        return self._stacks[-2]

    @property
    def depth(self) -> int:
        return len(self._stacks)

    def push(self, ContextState) -> None:
        """
        Pushes a new navigation level (e.g., after entering a subgraph).
        """
        self._stacks.append(ContextState)

    def pop(self) -> ContextState | None:
        """
        Pops the current navigation level, returning to the previous one.
        Returns the state of the level that was popped, or None if at root or uninitialized.
        """
        assert self._stacks, "CORRUPTION: Cannot pop from an empty navigation stack"
        if self.is_at_root():
            return None

        return self._stacks.pop()

    def context_state_for_scene(self, scene_instance: GraphicsScene) -> ContextState:
        """
        Retrieves the ContextState associated with a specific GraphicsScene instance.
        """
        context_state: ContextState | None = None
        for ctx in self._stacks:
            if ctx.scene is scene_instance:
                context_state = ctx

        assert context_state is not None, (
            "CORRUPTION: Scene {scene_instance} is not part of any stack."
        )
        return context_state

    def is_at_root(self) -> bool:
        """Checks if the current navigation level is the root."""
        return len(self._stacks) == 1
