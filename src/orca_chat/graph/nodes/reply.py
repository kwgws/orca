# --- orca_chat/graph/nodes/reply.py ------------------------------------------

"""..."""

from typing import Final

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import StateNode

from ..state import State

__all__: Final = [
    "reply_node",
]


def reply_node(llm: BaseChatModel, **llm_args) -> StateNode:
    """Compose final response."""

    async def _run(state: State, config: RunnableConfig) -> State:
        reply = await llm.ainvoke(state["messages"], config=config, **llm_args)
        return {"messages": [reply]}  # type: ignore

    return _run
