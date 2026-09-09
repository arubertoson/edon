"""Qt bridge for running core graph execution outside the UI thread."""

import asyncio

from PySide6.QtCore import QObject, QThread, Signal

from edon.executor import (
    CancellationToken,
    ExecutionCancelled,
    ExecutionEngine,
    NodeExecutionFailed,
)
from edon.graph import EntityGraph


class NodeExecutionThread(QThread):
    """Runs one node execution and reports only the affected node identity."""

    completed = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        engine: ExecutionEngine,
        graph: EntityGraph,
        node_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._graph = graph
        self._node_id = node_id
        self._cancellation = CancellationToken()

    def cancel(self) -> None:
        self._cancellation.cancel()

    def run(self) -> None:
        try:
            asyncio.run(
                self._engine.execute_node(
                    self._graph,
                    self._node_id,
                    cancellation=self._cancellation,
                )
            )
        except NodeExecutionFailed as error:
            self.failed.emit(error.node_id)
        except ExecutionCancelled:
            self.cancelled.emit()
        except Exception as error:
            node = self._graph.get_node(self._node_id)
            node.execution_error = error
            node.execution_dirty = True
            self.failed.emit(node.id)
        else:
            self.completed.emit(self._node_id)
