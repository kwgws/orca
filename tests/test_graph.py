# tests/test_graph.py
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from orca_chat.graph import build_graph
from orca_chat.state import create_state

from ._helpers import tc


@tool
def say_hello(hello: str = "hi") -> str:
    """Deterministic tool for testing."""
    return f"TOOL:{hello}"


@pytest.mark.asyncio
async def test_tools_path_end_to_end(llm_stub):
    responses = [
        AIMessage("", tool_calls=[tc("say_hello", {"hello": "howdy"})]),
        AIMessage("done"),
    ]
    llm_stub(responses=responses)

    graph = build_graph(tools=[say_hello])

    state = create_state()
    state["payload"]["route"] = "tools"
    state["messages"].append(HumanMessage("..."))

    out = await graph.ainvoke(state)

    msgs = out["messages"]
    assert msgs[0].type == "human" and str(msgs[0].content) == "..."
    assert msgs[-1].type == "ai" and str(msgs[-1].content) == "done"
