# tests/import_router.py

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from orca_chat.skills.route import route_node
from orca_chat.state import create_state

from ._helpers import run_node, tc


@pytest.mark.asyncio
async def test_route_to_chat(llm_stub):
    """When the model chooses chat, we should route there."""
    llm_stub(responses=[AIMessage("", tool_calls=[tc("route_to_chat")])])

    state = create_state()
    state["messages"].append(HumanMessage("Hello!"))
    out = await run_node(route_node(), state)

    assert out["payload"]["route"] == "chat"
    assert isinstance(out["payload"]["retrievers"], list)
    assert len(out["payload"]["retrievers"]) == 0


@pytest.mark.asyncio
async def test_route_to_retrievers(llm_stub):
    """When the model chooses retrievers, we should route to them."""
    tools = [tc("route_to_wikipedia"), tc("route_to_archive_retriever")]
    llm_stub(responses=[AIMessage("", tool_calls=tools)])

    state = create_state()
    state["messages"].append(HumanMessage("..."))
    out = await run_node(route_node(), state)

    assert out["payload"]["route"] == "tools"
    assert out["payload"]["retrievers"] == [
        "route_to_archive_retriever",
        "route_to_wikipedia",
    ]


@pytest.mark.asyncio
async def test_chat_mutually_exclusive(llm_stub):
    """When the model chooses chat, we should always route to it."""
    tools = [tc("route_to_wikipedia"), tc("route_to_chat")]
    llm_stub(responses=[AIMessage("", tool_calls=tools)])

    state = create_state()
    state["messages"].append(HumanMessage("..."))
    out = await run_node(route_node(), state)

    assert out["payload"]["route"] == "chat"
    assert isinstance(out["payload"]["retrievers"], list)
    assert len(out["payload"]["retrievers"]) == 0
