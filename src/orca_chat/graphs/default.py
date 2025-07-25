"""orca_chat/graphs/default.py"""

from ..core import ChatSession, SkillStore, build_graph
from ..loaders import load_config

# ...
_MAX_ROUNDS: int = load_config().llm.max_chat_rounds_to_llm


async def compile(skill_store: SkillStore):
    """Return default conversation graph."""
    pipeline = [
        "disambiguate",
        "route",
        "extract_topic",
        "make_query",
        "wikipedia",
        "rank",
        "chat",
        "summarize",
    ]

    def _goto_chat(state: ChatSession) -> bool:
        return state.payload.get("router_tags", "").strip().lower() == "chat"

    def _goto_wiki(state: ChatSession) -> bool:
        return state.payload.get("router_tags", "").strip().lower() == "wiki"

    def _goto_summary(state: ChatSession) -> bool:
        return len(state.history) // 2 >= _MAX_ROUNDS

    conditionals = [
        ("route", "chat", _goto_chat),
        ("route", "extract_topic", _goto_wiki),
        ("chat", "summarize", _goto_summary),
    ]

    return await build_graph(skill_store, pipeline, conditionals=conditionals)
