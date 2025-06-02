"""Sub-graph functionality for Edon node editor.

This package provides the core components for creating hierarchical node graphs,
where nodes can encapsulate entire graphs as reusable components.
"""

from .parameters import ParameterMapping, SubGraphParameter
from .node import SubGraphNode

__all__ = ["ParameterMapping", "SubGraphParameter", "SubGraphNode"]
