import asyncio
from collections import defaultdict
from types import SimpleNamespace
from typing import ClassVar

import pytest
from langchain_core.prompts import ChatPromptTemplate

from orca_chat.core.registry import LLMRegistry, SkillConfig


class DummyLLM:
    calls: ClassVar[defaultdict[str, int]] = defaultdict(int)

    def __init__(self, model: str, base_url: str, **params: object) -> None:
        type(self).calls[model] += 1

    async def astream(self, prompt, config=None):  # pragma: no cover
        yield SimpleNamespace(content="")


@pytest.mark.asyncio
async def test_get_llm_concurrent(monkeypatch):
    load_calls: defaultdict[str, int] = defaultdict(int)

    def fake_load_skill(name: str, path):
        load_calls[name] += 1
        return SkillConfig(
            model=name,
            base_url="",
            params={},
            prompt=ChatPromptTemplate.from_messages([("system", "test")]),
        )

    monkeypatch.setattr("orca_chat.core.registry.load_skill", fake_load_skill)
    monkeypatch.setattr("orca_chat.core.registry.ChatOllama", DummyLLM)

    registry = LLMRegistry()

    async def worker() -> object:
        return await registry.get_llm("chat")

    results = await asyncio.gather(*(worker() for _ in range(5)))

    assert len({id(r) for r in results}) == 1
    assert DummyLLM.calls["chat"] == 1
    assert load_calls["chat"] == 1


@pytest.mark.asyncio
async def test_get_graph_concurrent(monkeypatch):
    compiled = 0

    async def fake_compile(reg: LLMRegistry):
        nonlocal compiled
        compiled += 1
        return "graph"

    import orca_chat.graphs.default as default_module

    monkeypatch.setattr(default_module, "compile", fake_compile)

    registry = LLMRegistry()
    results = await asyncio.gather(*(registry.get_graph("default") for _ in range(5)))

    assert results == ["graph"] * 5
    assert compiled == 1
