"""orca_chat/graphs/default.py"""

from ..core.graph import build_graph
from ..core.registry import LLMRegistry


async def compile(registry: LLMRegistry):
    """Return default conversation graph."""
    pipeline = ["chat"]
    return await build_graph(registry, pipeline)
