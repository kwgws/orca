"""orca_chat/graphs/default.py"""

from ..config.constants import HISTORY_MAX_LEN
from ..core.graph import build_graph
from ..core.registry import LLMRegistry
from ..core.session import LLMSession


async def compile(registry: LLMRegistry):
    """Return default conversation graph."""
    pipeline = ["chat", "summarize"]

    def _needs_summary(state: LLMSession) -> bool:
        return len(state.history) // 2 >= HISTORY_MAX_LEN

    return await build_graph(
        registry,
        pipeline,
        conditionals=[("chat", "summarize", _needs_summary)],
    )
