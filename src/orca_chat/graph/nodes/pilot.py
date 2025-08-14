# --- orca_chat/graph/nodes/pilot.py ------------------------------------------

from typing import Final

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import StateNode

from ..state import State

__all__: Final = [
    "pilot_node",
]


def pilot_node(llm: BaseChatModel, **llm_args) -> StateNode:
    """Call tool-enabled LLM; decide next step from emitted tool calls."""

    async def _run(state: State, config: RunnableConfig) -> State:
        reply = await llm.ainvoke(state["messages"], config=config, **llm_args)
        return {"messages": [reply]}  # type: ignore

    return _run
