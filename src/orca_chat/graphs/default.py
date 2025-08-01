"""orca_chat/graphs/default.py"""

from os import getenv

from langchain_openai import ChatOpenAI

from ..core import LLMStore, NodeStore, build_graph, register_skill
from ..core.session import DEFAULT_MAX_ROUNDS
from ..skills.chat import ChatSkill
from ..skills.summarize import SummarizeSkill

__all__ = ["build_graph_default", "llm_store", "node_store"]


node_store = NodeStore()
llm_store = LLMStore()
llm_store.register(
    ChatSkill.llm_alias,
    ChatOpenAI(
        base_url=getenv("OPENAI_URL", "http://localhost:1234/v1"),
        model=getenv("OPENAI_MODEL", "llama3"),
        streaming=True,
    ),
)


async def build_graph_default():
    chat_node = await register_skill(ChatSkill, node_store, llm_store)
    summarize_node = await register_skill(SummarizeSkill, node_store, llm_store)

    return await build_graph(
        [chat_node, summarize_node],
        [
            (
                chat_node,
                summarize_node,
                lambda state: len(state.history) >= DEFAULT_MAX_ROUNDS * 2,
            )
        ],
    )
