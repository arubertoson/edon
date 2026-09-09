"""Execution of complete graphs and individual dependency closures."""

from __future__ import annotations

import asyncio
import inspect
from threading import Event

from loguru import logger

from edon.graph import EntityGraph, EntitySubGraphNode
from edon.node import EntityNode
from edon.types import SocketRole, current_execution_engine_context, current_graph_context


class ExecutionCancelled(RuntimeError):
    """Raised when an execution is cancelled between nodes."""


class NodeExecutionFailed(RuntimeError):
    """Reports which node owns an execution error."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"Node execution failed: {node_id}")


class CancellationToken:
    """Thread-safe cooperative cancellation state."""

    def __init__(self) -> None:
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def raise_if_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise ExecutionCancelled("Execution cancelled")


class ExecutionEngine:
    """Executes graph nodes in dependency order."""

    def __init__(self, max_depth: int = 10) -> None:
        self.max_depth = max_depth
        self._current_depth = 0

    def _topological_sort(self, graph: EntityGraph) -> list[EntityNode]:
        """Return all graph nodes in dependency order."""
        return graph.topological_order(graph.nodes.keys())

    def execute_graph(self, graph: EntityGraph, context: str = "root") -> None:
        """Synchronously execute every node in a graph.

        This compatibility API also supports asynchronous node implementations when
        called outside an active asyncio event loop.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._execute_graph(graph, context))
            return
        raise RuntimeError("execute_graph() cannot run inside an active asyncio event loop")

    async def execute_node(
        self,
        graph: EntityGraph,
        node_id: str,
        cancellation: CancellationToken | None = None,
    ) -> None:
        """Execute a node and any stale upstream dependencies."""
        cancellation = cancellation or CancellationToken()
        node_ids = graph.upstream_node_ids(node_id)
        execution_order = graph.topological_order(node_ids)

        engine_token = current_execution_engine_context.set(self)
        graph_token = current_graph_context.set(graph)
        try:
            for node in execution_order:
                cancellation.raise_if_cancelled()
                if not self._requires_execution(node):
                    continue
                await self._execute_target_node(node, cancellation)
        finally:
            current_graph_context.reset(graph_token)
            current_execution_engine_context.reset(engine_token)

    def _requires_execution(self, node: EntityNode) -> bool:
        if node.execution_dirty:
            return True
        if isinstance(node, EntitySubGraphNode):
            return any(
                self._requires_execution(internal_node)
                for internal_node in node.internal_graph.nodes.values()
            )
        return False

    async def _execute_target_node(
        self, node: EntityNode, cancellation: CancellationToken
    ) -> None:
        node.execution_error = None
        try:
            await self._process_node(node, cancellation)
        except ExecutionCancelled:
            raise
        except Exception as error:
            node.execution_error = error
            node.execution_dirty = True
            raise NodeExecutionFailed(node.id) from error
        node.execution_dirty = False

    async def _execute_graph(
        self,
        graph: EntityGraph,
        context: str,
        cancellation: CancellationToken | None = None,
    ) -> None:
        if self._current_depth >= self.max_depth:
            raise RuntimeError(
                f"Maximum sub-graph nesting depth ({self.max_depth}) exceeded. "
                f"Current context: {context}"
            )
        if not graph.nodes:
            return

        cancellation = cancellation or CancellationToken()
        engine_token = current_execution_engine_context.set(self)
        graph_token = current_graph_context.set(graph)
        try:
            execution_order = self._topological_sort(graph)
            logger.info(f"Execution order at {context}: {[node.name for node in execution_order]}")
            for node in execution_order:
                cancellation.raise_if_cancelled()
                node.execution_error = None
                try:
                    await self._process_node(node, cancellation)
                except ExecutionCancelled:
                    raise
                except Exception as error:
                    node.execution_error = error
                    node.execution_dirty = True
                    raise
                node.execution_dirty = False
        finally:
            current_graph_context.reset(graph_token)
            current_execution_engine_context.reset(engine_token)

    async def _process_node(self, node: EntityNode, cancellation: CancellationToken) -> None:
        logger.debug(f"Processing node: {node.name} (ID: {node.id})")
        if isinstance(node, EntitySubGraphNode):
            await self._execute_subgraph_node(node, cancellation)
            return

        process_result = node.process()
        if inspect.isawaitable(process_result):
            await process_result

    async def _execute_subgraph_node(
        self, subgraph_node: EntitySubGraphNode, cancellation: CancellationToken
    ) -> None:
        self._current_depth += 1
        try:
            subgraph_node._propagate_sockets(SocketRole.TARGET)
            await self._execute_graph(
                subgraph_node.internal_graph,
                context=f"sub-graph: {subgraph_node.name}",
                cancellation=cancellation,
            )
            subgraph_node._propagate_sockets(SocketRole.SOURCE)
        finally:
            self._current_depth -= 1
