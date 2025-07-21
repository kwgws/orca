"""orca_chat/graphs/default.py"""

from ..core import LLMRegistry, LLMSession, build_graph
from ..loaders import load_config

# ...
_MAX_ROUNDS: int = load_config().max_chat_rounds_to_llm


async def compile(registry: LLMRegistry):
    """Return default conversation graph."""
    pipeline = ["chat", "summarize"]

    def _needs_summary(state: LLMSession) -> bool:
        return len(state.history) // 2 >= _MAX_ROUNDS

    return await build_graph(
        registry,
        pipeline,
        conditionals=[("chat", "summarize", _needs_summary)],
    )
