import pytest

from orca_chat.core.graph import build_graph
from orca_chat.core.session import LLMSession


class DummyRegistry:
    async def get_factory(self, name: str):
        def factory():
            async def node(state: LLMSession, **_: object):
                visited = [*state.payload.get("visited", []), name]
                return {"payload": {"visited": visited}}

            return node

        return factory


@pytest.mark.asyncio
async def test_conditional_branch():
    graph = await build_graph(
        DummyRegistry(),  # type: ignore
        ["a", "b"],
        conditionals=[("a", "b", lambda _s: True)],
    )
    result = await graph.ainvoke(LLMSession())
    assert result["payload"]["visited"] == ["a", "b"]


@pytest.mark.asyncio
async def test_conditional_mid_pipeline_branch():
    graph = await build_graph(
        DummyRegistry(),  # type: ignore
        ["a", "b", "c"],
        conditionals=[("b", "c", lambda _s: True)],
    )
    result = await graph.ainvoke(LLMSession(payload={}))
    visited = result["payload"]["visited"]
    assert visited == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_conditional_early_exit():
    graph = await build_graph(
        DummyRegistry(),  # type: ignore
        ["a", "b"],
        conditionals=[("a", "b", lambda _s: False)],
    )
    result = await graph.ainvoke(LLMSession())
    assert result["payload"]["visited"] == ["a"]


@pytest.mark.asyncio
async def test_conditional_mid_pipeline_early_exit():
    graph = await build_graph(
        DummyRegistry(),  # type: ignore
        ["a", "b", "c"],
        conditionals=[("b", "c", lambda _s: False)],
    )
    result = await graph.ainvoke(LLMSession(payload={}))
    visited = result["payload"]["visited"]
    assert visited == ["a", "b"]


@pytest.mark.asyncio
async def test_linear_pipeline():
    graph = await build_graph(
        DummyRegistry(),  # type: ignore
        ["a", "b", "c"],
    )
    result = await graph.ainvoke(LLMSession())
    assert result["payload"]["visited"] == ["a", "b", "c"]
