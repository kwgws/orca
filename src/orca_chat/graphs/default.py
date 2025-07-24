"""orca_chat/graphs/default.py"""

from ..core import ChatSession, SkillRegistry, build_graph
from ..loaders import load_config

# ...
_MAX_ROUNDS: int = load_config().llm.max_chat_rounds_to_llm


async def compile(registry: SkillRegistry):
    """Return default conversation graph."""
    pipeline = ["chat", "summarize"]

    def _needs_summary(state: ChatSession) -> bool:
        return len(state.history) // 2 >= _MAX_ROUNDS

    return await build_graph(
        registry,
        pipeline,
        conditionals=[("chat", "summarize", _needs_summary)],
    )
