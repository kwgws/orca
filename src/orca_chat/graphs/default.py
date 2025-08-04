# orca_chat/graphs/default.py

from ..core import LLMStore, NodeStore, build_graph, register_skills
from ..core.session import DEFAULT_MAX_ROUNDS
from ..skills.chat import ChatSkill
from ..skills.summarize import SummarizeSkill
from ..tools.word_count import word_count

__all__ = ["build_graph_default", "llm_store", "node_store"]

node_store = NodeStore()
llm_store = LLMStore()


async def build_graph_default():
    await llm_store.add_tools(word_count)

    (
        chat,
        summarize,
    ) = await register_skills(
        ChatSkill,
        SummarizeSkill,
        node_store=node_store,
        llm_store=llm_store,
    )

    return await build_graph(
        [chat, summarize],
        [
            (  # Chat -> Summarize
                chat,
                summarize,
                lambda state: len(state.history) >= DEFAULT_MAX_ROUNDS * 2,
            ),
        ],
    )
